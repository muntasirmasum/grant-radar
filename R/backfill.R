#' Backfill multiple weeks in one call.
#'
#' Iterates Friday week-ending dates from `start` to `end` (inclusive),
#' calling `refresh_week()` for each. Politely paced (default 1 second
#' between weeks) to stay under any rate limits NIH might apply.
#'
#' @param start First week-ending date (Date or "YYYY-MM-DD"). Will be
#'   snapped to the nearest Friday on or before it.
#' @param end   Last week-ending date (defaults to today's Friday).
#' @param sources List of Source objects. Defaults to `list(nih_source())`.
#' @param sleep_seconds Delay between weeks. Defaults to 1.
#' @param ... Forwarded to `refresh_week()` (e.g. `run_llm = FALSE`,
#'   `force = TRUE`).
#' @return Tibble of per-notice results across all weeks.
#' @export
backfill_range <- function(start, end = Sys.Date(),
                           sources = list(nih_source()),
                           sleep_seconds = 1,
                           ...) {
  start <- .snap_to_friday(as.Date(start))
  end   <- .snap_to_friday(as.Date(end))
  weeks <- seq(start, end, by = "7 days")
  cli::cli_inform("Backfilling {length(weeks)} week{?s}: {as.character(start)} → {as.character(end)}")

  results <- purrr::map(weeks, function(w) {
    cli::cli_inform("--- week ending {as.character(w)} ---")
    out <- refresh_week(week_ending = w, sources = sources, ...)
    if (sleep_seconds > 0 && !identical(w, end)) Sys.sleep(sleep_seconds)
    dplyr::mutate(out, week_ending = w)
  })
  purrr::list_rbind(results)
}

#' Snap a date to the most recent Friday on or before it.
#' @keywords internal
.snap_to_friday <- function(d) {
  d - ((as.integer(format(d, "%u")) - 5L) %% 7L)
}
