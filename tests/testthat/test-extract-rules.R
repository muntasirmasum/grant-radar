test_that("extract_rules_nih parses NOT-MH-26-035 (rescission notice)", {
  html <- read_fixture("NOT-MH-26-035.html")
  rec  <- extract_rules_nih(html, url = "https://grants.nih.gov/grants/guide/notice-files/NOT-MH-26-035.html")

  expect_equal(rec$notice_id, "NOT-MH-26-035")
  expect_equal(rec$source, "nih")
  expect_equal(rec$notice_type, "rescission")
  expect_match(rec$title, "Rescind NOT-MH-22-310")
  expect_equal(rec$release_date, "2026-05-19")
  expect_true("National Institute of Mental Health" %in% rec$issuing_orgs)
  expect_true("NOT-MH-22-310" %in% rec$related)
  expect_true(length(rec$key_dates) >= 1)
  expect_match(rec$raw_html_hash, "^[a-f0-9]{64}$")
})

test_that("extract_rules_nih parses NOT-DA-26-011", {
  html <- read_fixture("NOT-DA-26-011.html")
  rec  <- extract_rules_nih(html, url = "https://grants.nih.gov/grants/guide/notice-files/NOT-DA-26-011.html")

  expect_equal(rec$notice_id, "NOT-DA-26-011")
  expect_equal(rec$source, "nih")
  expect_true(rec$notice_type %in% c("guide_notice", "change", "reissue"))
  expect_true(nchar(rec$title) > 0)
  expect_true(grepl("^\\d{4}-\\d{2}-\\d{2}$", rec$release_date))
})

test_that("notice_type derivation handles common title patterns", {
  derive <- grantradar:::.derive_notice_type
  expect_equal(derive("NOT-MH-26-035", "Notice to Rescind XYZ"), "rescission")
  expect_equal(derive("NOT-MH-26-030", "Notice of Change to Key Dates for ABC"), "change")
  expect_equal(derive("RFA-DA-26-001", "Some RFA title"),            "rfa")
  expect_equal(derive("PAR-25-182",    "Some PAR title"),            "par")
  expect_equal(derive("PA-25-100",     "Some PA title"),             "pa")
  expect_equal(derive("NOT-MH-26-035", NULL),                        "guide_notice")
})

test_that("date parser handles NIH formats and rejects garbage", {
  parse <- grantradar:::.parse_nih_date
  expect_equal(parse("May 19, 2026"),     "2026-05-19")
  expect_equal(parse("  May  19, 2026 "), "2026-05-19")
  expect_equal(parse("Jan 3, 2026"),      "2026-01-03")
  expect_true(is.na(parse("not a date")))
})

test_that("rule-extracted records validate against the schema", {
  html <- read_fixture("NOT-MH-26-035.html")
  rec  <- extract_rules_nih(html, url = "https://grants.nih.gov/grants/guide/notice-files/NOT-MH-26-035.html")
  expect_true(validate_notice(rec))
})
