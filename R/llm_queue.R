#' List notice JSON files that lack LLM-extracted fields.
#'
#' A notice is considered "needs enrichment" if its `purpose_tldr` is null,
#' missing, or empty. Used by the local Claude Code workflow
#' (`/refresh-tldrs`) to know what still needs processing.
#'
#' @param data_dir Project data directory. Defaults to `"data"`.
#' @return Tibble with one row per unfilled notice: `notice_id`, `json_path`,
#'   `html_path`, `release_date`.
#' @export
notices_needing_llm <- function(data_dir = "data") {
  paths <- fs::dir_ls(fs::path(data_dir, "notices"), recurse = TRUE, glob = "*.json")
  if (length(paths) == 0L) {
    return(tibble::tibble(notice_id = character(), json_path = character(),
                          html_path = character(), release_date = as.Date(character())))
  }

  rows <- purrr::map(paths, function(p) {
    rec <- jsonlite::read_json(p)
    if (!.is_unfilled(rec$purpose_tldr)) return(NULL)
    year <- format(as.Date(rec$release_date %||% "1900-01-01"), "%Y")
    tibble::tibble(
      notice_id    = rec$notice_id,
      json_path    = as.character(p),
      html_path    = fs::path(data_dir, "raw", rec$source %||% "nih", year,
                              paste0(rec$notice_id, ".html")),
      release_date = as.Date(rec$release_date %||% NA)
    )
  })
  out <- purrr::list_rbind(purrr::compact(rows))
  if (nrow(out) == 0L) return(out)
  dplyr::arrange(out, dplyr::desc(.data$release_date))
}

.is_unfilled <- function(x) {
  is.null(x) || identical(x, NA) || identical(x, NA_character_) ||
    (is.character(x) && !nzchar(x))
}

#' Apply Claude-Code-supplied LLM fields to a notice and write it back.
#'
#' This is the bridge the `/refresh-tldrs` slash command calls after it
#' produces the structured extraction. It merges the supplied fields onto
#' the existing rule record, validates the result, and writes the JSON.
#'
#' @param json_path Path to the notice's JSON file under `data/notices/`.
#' @param llm_fields A named list with any of: `purpose_tldr`,
#'   `eligibility_tldr`, `budget`, `mechanisms`, `career_stages`, `topics`,
#'   `dos`, `donts`, `strategic_priorities`.
#' @param model_label String stored in `llm_model`. Defaults to
#'   `"claude-via-claude-code"`.
#' @return Invisibly returns the merged record.
#' @export
apply_llm_fields <- function(json_path, llm_fields,
                             model_label = "claude-via-claude-code") {
  rec <- jsonlite::read_json(json_path, simplifyVector = FALSE)
  llm_fields$llm_model    <- model_label
  llm_fields$extracted_at <- format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  full <- merge_extractions(rec, llm_fields)
  validate_notice(full)
  full_io <- full
  array_fields <- c("issuing_orgs", "mechanisms", "career_stages", "topics",
                    "related", "dos", "donts", "strategic_priorities", "key_dates")
  for (f in array_fields) {
    if (!is.null(full_io[[f]])) full_io[[f]] <- I(full_io[[f]])
  }
  json <- jsonlite::toJSON(full_io, auto_unbox = TRUE, null = "null",
                           na = "null", pretty = TRUE)
  writeLines(json, json_path)
  invisible(full)
}
