test_that("rollup_notices reads every JSON under data/notices and writes parquet", {
  tmp <- withr::local_tempdir()
  fs::dir_create(fs::path(tmp, "notices", "2026"))

  rec <- list(
    notice_id    = "NOT-MH-26-035",
    source       = "nih",
    notice_type  = "rescission",
    title        = "Test",
    release_date = "2026-05-19",
    url          = "https://example.com/x",
    issuing_orgs = c("National Institute of Mental Health"),
    mechanisms   = c("K01"),
    career_stages= c("early_career"),
    topics       = c("mental_health"),
    purpose_tldr = "Rescinds prior policy.",
    eligibility_tldr = "K-award PIs.",
    budget = list(direct_cost_cap = NA_real_, total_cost_cap = NA_real_, project_period_max = NA_character_),
    key_dates    = list(list(label = "Release Date", date = "2026-05-19", type = "release")),
    related      = c("NOT-MH-22-310"),
    dos          = c("a","b"),
    donts        = c("c"),
    strategic_priorities = list(),
    raw_html_hash      = strrep("a", 64),
    extracted_at       = "2026-05-22T19:00:00Z",
    extractor_version  = "0.1.0",
    llm_model          = "stub"
  )
  writeLines(jsonlite::toJSON(rec, auto_unbox = TRUE, null = "null", na = "null"),
             fs::path(tmp, "notices", "2026", "NOT-MH-26-035.json"))

  out <- rollup_notices(data_dir = tmp)
  expect_equal(nrow(out), 1)
  expect_equal(out$notice_id, "NOT-MH-26-035")
  expect_true(fs::file_exists(fs::path(tmp, "notices.parquet")))

  read_back <- arrow::read_parquet(fs::path(tmp, "notices.parquet"))
  expect_equal(read_back$notice_id, "NOT-MH-26-035")
  expect_equal(as.character(read_back$release_date), "2026-05-19")
})

test_that("rollup_notices handles an empty notices/ directory gracefully", {
  tmp <- withr::local_tempdir()
  fs::dir_create(fs::path(tmp, "notices"))
  out <- suppressWarnings(rollup_notices(data_dir = tmp))
  expect_s3_class(out, "tbl_df")
  expect_equal(nrow(out), 0)
  expect_true(fs::file_exists(fs::path(tmp, "notices.parquet")))
})
