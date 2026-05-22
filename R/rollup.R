#' Roll all per-notice JSON records into a single parquet file.
#'
#' Reads every `data/notices/*/{notice_id}.json`, flattens it into one row,
#' and writes the result to `data/notices.parquet`. The OJS frontend loads
#' this single artifact via DuckDB-WASM.
#'
#' Nested fields (`key_dates`, `budget`) are JSON-encoded into string
#' columns so the parquet schema stays flat; the frontend parses them back
#' as needed.
#'
#' @param data_dir Project data directory. Defaults to `"data"`.
#' @param out_path Where to write the parquet roll-up. Defaults to
#'   `data/notices.parquet` under `data_dir`.
#' @return Invisibly returns the tibble that was written.
#' @export
rollup_notices <- function(data_dir = "data",
                           out_path = fs::path(data_dir, "notices.parquet")) {
  paths <- fs::dir_ls(fs::path(data_dir, "notices"), recurse = TRUE, glob = "*.json")
  if (length(paths) == 0L) {
    cli::cli_warn("No notice JSON files found under {.path {fs::path(data_dir, 'notices')}}.")
    empty <- tibble::tibble(
      notice_id = character(), source = character(), notice_type = character(),
      title = character(), release_date = as.Date(character()),
      url = character(), issuing_orgs = list(), mechanisms = list(),
      career_stages = list(), topics = list(),
      purpose_tldr = character(), eligibility_tldr = character(),
      budget_json = character(), key_dates_json = character(),
      related = list(), dos = list(), donts = list(),
      strategic_priorities = list(),
      raw_html_hash = character(), extracted_at = character(),
      extractor_version = character(), llm_model = character()
    )
    arrow::write_parquet(empty, out_path)
    return(invisible(empty))
  }
  rows <- purrr::map(paths, .flatten_notice)
  df <- purrr::list_rbind(rows)
  arrow::write_parquet(df, out_path)
  cli::cli_inform("Wrote {nrow(df)} notice{?s} to {.path {out_path}}.")
  invisible(df)
}

.flatten_notice <- function(path) {
  rec <- jsonlite::read_json(path)
  list_or_empty <- function(x) if (is.null(x)) list(character()) else list(unlist(x))
  scalar_or_na <- function(x) if (is.null(x)) NA_character_ else as.character(x)
  tibble::tibble(
    notice_id        = scalar_or_na(rec$notice_id),
    source           = scalar_or_na(rec$source),
    notice_type      = scalar_or_na(rec$notice_type),
    title            = scalar_or_na(rec$title),
    release_date     = as.Date(scalar_or_na(rec$release_date)),
    url              = scalar_or_na(rec$url),
    issuing_orgs     = list_or_empty(rec$issuing_orgs),
    mechanisms       = list_or_empty(rec$mechanisms),
    career_stages    = list_or_empty(rec$career_stages),
    topics           = list_or_empty(rec$topics),
    purpose_tldr     = scalar_or_na(rec$purpose_tldr),
    eligibility_tldr = scalar_or_na(rec$eligibility_tldr),
    budget_json      = jsonlite::toJSON(rec$budget %||% NULL, auto_unbox = TRUE, null = "null", na = "null"),
    key_dates_json   = jsonlite::toJSON(rec$key_dates %||% list(), auto_unbox = TRUE, null = "null", na = "null"),
    related          = list_or_empty(rec$related),
    dos              = list_or_empty(rec$dos),
    donts            = list_or_empty(rec$donts),
    strategic_priorities = list_or_empty(rec$strategic_priorities),
    raw_html_hash    = scalar_or_na(rec$raw_html_hash),
    extracted_at     = scalar_or_na(rec$extracted_at),
    extractor_version = scalar_or_na(rec$extractor_version),
    llm_model        = scalar_or_na(rec$llm_model)
  )
}
