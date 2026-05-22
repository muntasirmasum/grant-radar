#' Rule-based extraction of stable fields from an NIH notice page.
#'
#' Handles the fields that NIH renders in a predictable template: ID, title,
#' release date, issuing org(s), related announcements, and the "Key Dates"
#' table when present. Free-text fields (purpose, eligibility, do's/don'ts)
#' are out of scope here and handled by the LLM extractor.

.label_to_key_date_type <- function(label) {
  l <- tolower(label)
  dplyr::case_when(
    stringr::str_detect(l, "release")                                  ~ "release",
    stringr::str_detect(l, "letter of intent|loi")                     ~ "loi",
    stringr::str_detect(l, "application due|due date")                 ~ "application_due",
    stringr::str_detect(l, "scientific merit|peer review")             ~ "scientific_merit",
    stringr::str_detect(l, "advisory council|council")                 ~ "council",
    stringr::str_detect(l, "earliest start")                           ~ "earliest_start",
    stringr::str_detect(l, "expir")                                    ~ "expiration",
    TRUE                                                                ~ "other"
  )
}

#' Parse a free-form NIH date string ("May 19, 2026") to ISO-8601.
#' Returns NA on failure.
#' @keywords internal
.parse_nih_date <- function(s) {
  s <- stringr::str_squish(s)
  parsed <- suppressWarnings(as.Date(s, format = "%B %d, %Y"))
  if (!is.na(parsed)) return(format(parsed, "%Y-%m-%d"))
  # Try short month
  parsed <- suppressWarnings(as.Date(s, format = "%b %d, %Y"))
  if (!is.na(parsed)) return(format(parsed, "%Y-%m-%d"))
  NA_character_
}

#' Derive notice_type from the notice_id prefix and (optionally) title.
#' @keywords internal
.derive_notice_type <- function(notice_id, title = NULL) {
  prefix <- stringr::str_extract(notice_id, "^[A-Z]+")
  type <- switch(prefix,
    "NOT"   = "guide_notice",
    "RFA"   = "rfa",
    "PA"    = "pa",
    "PAR"   = "par",
    "NOFO"  = "nofo",
    "other"
  )
  if (!is.null(title) && type == "guide_notice") {
    t <- tolower(title)
    if (stringr::str_detect(t, "rescind"))                  type <- "rescission"
    else if (stringr::str_detect(t, "notice of change"))    type <- "change"
    else if (stringr::str_detect(t, "reissue"))             type <- "reissue"
  }
  type
}

#' Extract issuing organization(s) from the "Issued by" section.
#' Returns full institute names; abbreviations in parentheses are dropped.
#' @keywords internal
.extract_issuing_orgs <- function(doc) {
  h <- rvest::html_elements(doc, xpath = "//h2[normalize-space()='Issued by']")
  if (length(h) == 0L) return(character())
  # The h2 sits inside a wrapping div; the content lives in the next div sibling
  # of that wrapper.
  block <- rvest::html_elements(h[1], xpath = "ancestor::div[1]/following-sibling::div[1]")
  if (length(block) == 0L) return(character())
  txt <- rvest::html_text2(block)
  txt <- stringr::str_squish(txt)
  # Split on newline if multiple ICs are listed.
  parts <- unlist(stringr::str_split(txt, "\\s*\\n\\s*"))
  parts <- parts[nzchar(parts)]
  # Strip trailing "(XYZ)" abbreviation; keep full institute name.
  stringr::str_squish(stringr::str_replace(parts, "\\s*\\([^)]+\\)\\s*$", ""))
}

#' Extract related-announcement notice IDs from the "Related Announcements" section.
#' @keywords internal
.extract_related <- function(doc) {
  h <- rvest::html_elements(doc, xpath = "//h2[normalize-space()='Related Announcements']")
  if (length(h) == 0L) return(character())
  block <- rvest::html_elements(h[1], xpath = "ancestor::div[1]/following-sibling::div[1]")
  if (length(block) == 0L) return(character())
  hrefs <- rvest::html_attr(rvest::html_elements(block, "a"), "href")
  ids <- stringr::str_extract(hrefs, "[A-Z]+-[A-Z]{2,4}-\\d{2}-\\d{3,4}")
  unique(ids[!is.na(ids)])
}

#' Extract Key Dates rows. NIH uses two-column rows
#' (datalabel/datacolumn) inside a sibling block of <h2>Key Dates</h2>.
#' @keywords internal
.extract_key_dates <- function(doc) {
  rows <- rvest::html_elements(doc, xpath = "//div[contains(@class,'datalabel')]/parent::div[contains(@class,'row')]")
  if (length(rows) == 0L) return(list())
  labels  <- vapply(rows, function(r) stringr::str_squish(rvest::html_text2(rvest::html_element(r, ".datalabel"))), character(1))
  values  <- vapply(rows, function(r) stringr::str_squish(rvest::html_text2(rvest::html_element(r, ".datacolumn"))), character(1))
  labels  <- stringr::str_remove(labels, ":\\s*$")
  dates   <- vapply(values, .parse_nih_date, character(1))
  keep    <- !is.na(dates) & nzchar(labels)
  if (!any(keep)) return(list())
  purrr::map2(labels[keep], dates[keep], \(lab, d) list(
    label = lab,
    date  = d,
    type  = .label_to_key_date_type(lab)
  ))
}

#' Extract title and notice number.
#' @keywords internal
.extract_header <- function(doc) {
  title <- stringr::str_squish(rvest::html_text2(rvest::html_element(doc, "span.title")))
  num   <- stringr::str_squish(rvest::html_text2(rvest::html_element(doc, "span.noticenum")))
  list(title = title, notice_id = num)
}

#' Rule-extract the schema-stable fields from a single NIH notice HTML.
#'
#' @param html Character scalar HTML of one notice page.
#' @param url  The canonical URL the HTML was fetched from. Used as the
#'   record's `url` field.
#' @return A list with the rule-extractable subset of the schema:
#'   `notice_id`, `source`, `notice_type`, `title`, `release_date`, `url`,
#'   `issuing_orgs`, `key_dates`, `related`, `raw_html_hash`, `extracted_at`,
#'   `extractor_version`. Free-text fields are left for the LLM extractor.
#' @export
extract_rules_nih <- function(html, url) {
  doc <- rvest::read_html(html)
  hdr <- .extract_header(doc)
  key_dates <- .extract_key_dates(doc)

  release_date <- NA_character_
  for (kd in key_dates) {
    if (identical(kd$type, "release")) { release_date <- kd$date; break }
  }

  list(
    notice_id         = hdr$notice_id,
    source            = "nih",
    notice_type       = .derive_notice_type(hdr$notice_id, hdr$title),
    title             = hdr$title,
    release_date      = release_date,
    url               = url,
    issuing_orgs      = .extract_issuing_orgs(doc),
    key_dates         = key_dates,
    related           = .extract_related(doc),
    raw_html_hash     = digest::digest(html, algo = "sha256", serialize = FALSE),
    extracted_at      = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    extractor_version = extractor_version()
  )
}
