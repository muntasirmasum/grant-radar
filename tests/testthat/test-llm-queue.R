make_rule_only <- function(dir, notice_id = "NOT-MH-26-035", purpose_tldr = NULL) {
  fs::dir_create(fs::path(dir, "notices", "2026"))
  fs::dir_create(fs::path(dir, "raw", "nih", "2026"))
  rec <- list(
    notice_id = notice_id, source = "nih", notice_type = "rescission",
    title = "T", release_date = "2026-05-19",
    url = "https://x/", issuing_orgs = c("NIMH"),
    key_dates = list(list(label = "Release Date", date = "2026-05-19", type = "release")),
    related = character(),
    raw_html_hash = strrep("a", 64),
    extracted_at = "2026-05-22T19:00:00Z",
    extractor_version = "0.1.0"
  )
  if (!is.null(purpose_tldr)) rec$purpose_tldr <- purpose_tldr
  writeLines(jsonlite::toJSON(rec, auto_unbox = TRUE, null = "null", na = "null"),
             fs::path(dir, "notices", "2026", paste0(notice_id, ".json")))
  writeLines("<html><body><p>stub</p></body></html>",
             fs::path(dir, "raw", "nih", "2026", paste0(notice_id, ".html")))
}

test_that("notices_needing_llm finds rule-only records and skips enriched ones", {
  tmp <- withr::local_tempdir()
  make_rule_only(tmp, "NOT-MH-26-035")
  make_rule_only(tmp, "NOT-DA-26-011", purpose_tldr = "Already done.")

  q <- notices_needing_llm(data_dir = tmp)
  expect_equal(nrow(q), 1)
  expect_equal(q$notice_id, "NOT-MH-26-035")
  expect_true(grepl("NOT-MH-26-035\\.html$", q$html_path))
})

test_that("apply_llm_fields merges, validates, and rewrites the JSON", {
  tmp <- withr::local_tempdir()
  make_rule_only(tmp, "NOT-MH-26-035")
  json_path <- fs::path(tmp, "notices", "2026", "NOT-MH-26-035.json")

  llm <- list(
    purpose_tldr     = "Rescinds a prior K-award policy.",
    eligibility_tldr = "Applies to current K-award PIs.",
    budget = list(direct_cost_cap = NA_real_, total_cost_cap = NA_real_, project_period_max = NA_character_),
    mechanisms = c("K01"),
    career_stages = c("early_career"),
    topics = c("mental_health"),
    dos   = c("Read the rescinded notice"),
    donts = c("Do not rely on rescinded guidance"),
    strategic_priorities = character()
  )
  res <- apply_llm_fields(json_path, llm, model_label = "claude-via-cc")
  expect_equal(res$purpose_tldr, "Rescinds a prior K-award policy.")
  expect_equal(res$llm_model, "claude-via-cc")

  q <- notices_needing_llm(data_dir = tmp)
  expect_equal(nrow(q), 0)
})
