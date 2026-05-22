#' Single-week refresh orchestrator.
#'
#' For each registered source, list the notices published in the week ending
#' on `week_ending`, fetch each one, cache the raw HTML to `data/raw/`,
#' run the hybrid extractor, validate, and write the schema-conformant JSON
#' to `data/notices/{YYYY}/{notice_id}.json`. Idempotent: notices whose
#' `raw_html_hash` has not changed are skipped unless `force = TRUE`.
#'
#' @param week_ending Date or string "YYYY-MM-DD". If empty or missing,
#'   defaults to the most recent Friday on or before today.
#' @param sources List of Source objects. Defaults to `list(nih_source())`.
#' @param data_dir Project data directory. Defaults to `"data"`.
#' @param force Re-extract even if a cached JSON already exists.
#' @param run_llm If TRUE, run the LLM extractor for free-text fields.
#'   Set FALSE for cheap dry runs or local development without an API key.
#' @return Invisibly returns a tibble of notice_id, status (one of
#'   `"new"`, `"updated"`, `"skipped"`, `"error"`).
#' @export
refresh_week <- function(week_ending = "",
                         sources = list(nih_source()),
                         data_dir = "data",
                         force = FALSE,
                         run_llm = TRUE) {
  week_ending <- .resolve_week_ending(week_ending)
  cli::cli_inform("Refreshing week ending {.val {week_ending}}")

  fs::dir_create(fs::path(data_dir, "raw"))
  fs::dir_create(fs::path(data_dir, "notices", format(week_ending, "%Y")))

  results <- purrr::map(sources, \(src) .refresh_one_source(
    src, week_ending, data_dir, force, run_llm
  ))
  purrr::list_rbind(results)
}

.resolve_week_ending <- function(week_ending) {
  if (is.null(week_ending) || identical(week_ending, "") || is.na(week_ending)) {
    today <- Sys.Date()
    # 5 = Friday; back up to the most recent Friday on or before today.
    return(today - ((as.integer(format(today, "%u")) - 5L) %% 7L))
  }
  as.Date(week_ending)
}

.refresh_one_source <- function(src, week_ending, data_dir, force, run_llm) {
  notices <- list_week(src, week_ending)
  if (nrow(notices) == 0L) {
    cli::cli_warn("No notices listed for {src@name} week {week_ending}.")
    return(tibble::tibble(notice_id = character(), status = character()))
  }
  cli::cli_inform("Found {nrow(notices)} {src@name} notice{?s}.")

  purrr::pmap(notices, function(notice_id, url, title, category) {
    tryCatch(
      .process_notice(src, notice_id, url, week_ending, data_dir, force, run_llm),
      error = function(e) {
        cli::cli_warn("Error processing {notice_id}: {conditionMessage(e)}")
        tibble::tibble(notice_id = notice_id, status = "error")
      }
    )
  }) |> purrr::list_rbind()
}

.process_notice <- function(src, notice_id, url, week_ending, data_dir, force, run_llm) {
  year <- format(week_ending, "%Y")
  out_path <- fs::path(data_dir, "notices", year, paste0(notice_id, ".json"))
  raw_path <- fs::path(data_dir, "raw", src@name, year, paste0(notice_id, ".html"))
  fs::dir_create(fs::path_dir(raw_path))

  html <- fetch_notice(src, url)
  writeLines(html, raw_path)

  rule_rec <- extract_rules_nih(html, url = url)

  if (!force && fs::file_exists(out_path)) {
    existing <- jsonlite::read_json(out_path)
    if (identical(existing$raw_html_hash, rule_rec$raw_html_hash)) {
      return(tibble::tibble(notice_id = notice_id, status = "skipped"))
    }
  }

  full <- if (run_llm) {
    llm_rec <- extract_llm_nih(html)
    merge_extractions(rule_rec, llm_rec)
  } else {
    rule_rec
  }

  validate_notice(full)
  json <- jsonlite::toJSON(.mark_arrays(full), auto_unbox = TRUE, null = "null",
                           na = "null", pretty = TRUE)
  writeLines(json, out_path)

  status <- if (fs::file_exists(out_path)) "updated" else "new"
  tibble::tibble(notice_id = notice_id, status = status)
}

.mark_arrays <- function(notice) {
  array_fields <- c("issuing_orgs", "mechanisms", "career_stages", "topics",
                    "related", "dos", "donts", "strategic_priorities", "key_dates")
  for (f in array_fields) {
    if (!is.null(notice[[f]])) notice[[f]] <- I(notice[[f]])
  }
  notice
}
