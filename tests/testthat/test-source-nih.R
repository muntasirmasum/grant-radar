test_that("parse_weekly_index extracts notices from the May 22, 2026 index", {
  html  <- read_fixture("weekly-2026-05-22.html")
  index <- parse_weekly_index(html)

  expect_s3_class(index, "tbl_df")
  expect_named(index, c("notice_id", "url", "title", "category"))
  expect_gt(nrow(index), 0)

  # The week we sampled has at least these two notices we manually verified.
  expect_true("NOT-MH-26-035" %in% index$notice_id)
  expect_true("NOT-DA-26-011" %in% index$notice_id)

  # Every notice_id should match the NIH ID grammar.
  expect_true(all(grepl("^[A-Z]+-[A-Z]{2,4}-\\d{2}-\\d{3,4}$", index$notice_id)))

  # Categories should be populated from the h3 headings.
  expect_true(all(nzchar(index$category)))
})

test_that("parse_weekly_index returns an empty tibble for an unrelated HTML page", {
  out <- parse_weekly_index("<html><body><p>no index here</p></body></html>")
  expect_s3_class(out, "tbl_df")
  expect_equal(nrow(out), 0)
})

test_that("nih_source() builds an NIHSource with expected defaults", {
  src <- nih_source()
  expect_equal(src@name, "nih")
  expect_match(src@weekly_index_url, "WeeklyIndexMobile")
  expect_match(src@notice_base_url,  "notice-files")
})
