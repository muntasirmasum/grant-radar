#' Read a fixture file's contents as a single character string.
read_fixture <- function(name) {
  path <- testthat::test_path("fixtures", "nih", name)
  paste(readLines(path, warn = FALSE), collapse = "\n")
}
