#' Path to the canonical notice JSON schema.
#'
#' Resolves the bundled schema file in this package, falling back to the
#' in-source path during development.
#' @keywords internal
notice_schema_path <- function() {
  p <- system.file("schema", "notice.schema.json", package = "grantradar")
  if (nzchar(p)) return(p)
  fs::path("inst", "schema", "notice.schema.json")
}

#' Validate one extracted notice against the canonical schema.
#'
#' @param notice A list shaped like the schema (will be JSON-serialized).
#' @return Invisibly returns `TRUE` on success; throws on failure with the
#'   validator errors attached.
validate_notice <- function(notice) {
  # Mark schema-defined array fields with I() so single-element vectors
  # serialize as JSON arrays instead of scalars under auto_unbox.
  array_fields <- c("issuing_orgs", "mechanisms", "career_stages", "topics",
                    "related", "dos", "donts", "strategic_priorities", "key_dates")
  for (f in array_fields) {
    if (!is.null(notice[[f]])) notice[[f]] <- I(notice[[f]])
  }
  json <- jsonlite::toJSON(notice, auto_unbox = TRUE, null = "null", na = "null",
                           POSIXt = "ISO8601", Date = "ISO8601")
  ok <- jsonvalidate::json_validate(
    json   = json,
    schema = notice_schema_path(),
    engine = "ajv",
    verbose = TRUE,
    greedy  = TRUE
  )
  if (!isTRUE(ok)) {
    errors <- attr(ok, "errors")
    cli::cli_abort(c(
      "Notice failed schema validation.",
      "i" = "notice_id: {notice$notice_id %||% '<missing>'}",
      "x" = "{nrow(errors)} validation error{?s}"
    ), .envir = environment(), errors = errors)
  }
  invisible(TRUE)
}

#' Current extractor version string, used in every emitted record.
#' @keywords internal
extractor_version <- function() "0.1.0"
