#' NIH Guide for Grants and Contracts source.
#'
#' Reads the public weekly index and individual notice pages. No auth needed.

NIHSource <- S7::new_class(
  "grantradar::NIHSource",
  parent = Source,
  properties = list(
    weekly_index_url = S7::class_character,
    notice_base_url  = S7::class_character,
    user_agent       = S7::class_character
  ),
  constructor = function() {
    S7::new_object(
      S7::S7_object(),
      name             = "nih",
      weekly_index_url = "https://grants.nih.gov/grants/guide/WeeklyIndexMobile.cfm",
      notice_base_url  = "https://grants.nih.gov/grants/guide/notice-files/",
      user_agent       = "grant-radar (https://github.com/muntasirmasum/grant-radar)"
    )
  }
)

#' Build an NIHSource instance.
#' @export
nih_source <- function() NIHSource()

#' Format a Date as the URL parameter the NIH index expects.
#' @keywords internal
.nih_format_week <- function(week_ending) {
  if (!inherits(week_ending, "Date")) week_ending <- as.Date(week_ending)
  format(week_ending, "%Y-%m-%d")
}

#' Parse a weekly-index HTML string into a tibble of notice entries.
#'
#' Exported separately from the network call so tests can run against a
#' cached fixture.
#' @param html A character scalar of HTML.
#' @return A tibble with columns `notice_id`, `url`, `title`, `category`.
#' @export
parse_weekly_index <- function(html) {
  doc <- rvest::read_html(html)
  cats <- rvest::html_elements(doc, "h3.weeklyindex")

  if (length(cats) == 0L) {
    return(tibble::tibble(
      notice_id = character(),
      url = character(),
      title = character(),
      category = character()
    ))
  }

  entries <- purrr::map(cats, function(h) {
    category <- stringr::str_squish(rvest::html_text2(h))
    # Each h3.weeklyindex is followed by a single <ul> sibling listing notices.
    block <- rvest::html_elements(h, xpath = "following-sibling::ul[1]")
    if (length(block) == 0L) return(NULL)
    anchors <- rvest::html_elements(block, "a[href*='notice-files/']")
    if (length(anchors) == 0L) return(NULL)
    tibble::tibble(
      url      = rvest::html_attr(anchors, "href"),
      title    = stringr::str_squish(rvest::html_text2(anchors)),
      category = category
    )
  })

  out <- purrr::list_rbind(purrr::compact(entries))
  out$notice_id <- stringr::str_extract(out$url, "[A-Z]+-[A-Z]{2,4}-\\d{2}-\\d{3,4}")
  out <- dplyr::filter(out, !is.na(.data$notice_id))
  dplyr::distinct(out, .data$notice_id, .keep_all = TRUE)[, c("notice_id", "url", "title", "category")]
}

S7::method(list_week, NIHSource) <- function(source, week_ending) {
  req <- httr2::request(source@weekly_index_url) |>
    httr2::req_url_query(WeekEnding = .nih_format_week(week_ending)) |>
    httr2::req_user_agent(source@user_agent) |>
    httr2::req_retry(max_tries = 3)
  resp <- httr2::req_perform(req)
  parse_weekly_index(httr2::resp_body_string(resp))
}

S7::method(fetch_notice, NIHSource) <- function(source, url) {
  req <- httr2::request(url) |>
    httr2::req_user_agent(source@user_agent) |>
    httr2::req_retry(max_tries = 3)
  httr2::resp_body_string(httr2::req_perform(req))
}
