#' Pluggable funding-source interface.
#'
#' Each source (NIH, NSF, AHRQ, ...) implements two operations:
#'
#' - `list_week(source, week_ending)` returns a tibble of notices published
#'    in the week ending on `week_ending` (Date). Required columns:
#'    `notice_id`, `url`, `title`, `category`.
#' - `fetch_notice(source, url)` returns the raw HTML string for one notice.
#'
#' Implementations live in `R/sources/<name>.R` and are constructed by
#' top-level helpers (e.g. `nih_source()`).
Source <- S7::new_class(
  "grantradar::Source",
  properties = list(
    name = S7::class_character
  )
)

#' @export
list_week <- S7::new_generic("list_week", "source",
  function(source, week_ending) S7::S7_dispatch()
)

#' @export
fetch_notice <- S7::new_generic("fetch_notice", "source",
  function(source, url) S7::S7_dispatch()
)
