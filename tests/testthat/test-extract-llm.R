stub_chat <- function(canned, model_label = "stub") {
  list(
    chat_structured = function(user_msg, type) canned
  )
}

stub_chat_factory <- function(canned) {
  function(model, system_prompt) stub_chat(canned)
}

failing_then_succeeding_factory <- function(canned) {
  calls <- 0L
  function(model, system_prompt) {
    calls <<- calls + 1L
    list(chat_structured = function(user_msg, type) {
      if (calls == 1L) stop("simulated primary-model failure")
      canned
    })
  }
}

valid_canned <- function() {
  list(
    purpose_tldr     = "This notice rescinds a prior K-award policy.",
    eligibility_tldr = "Applies to existing K-award investigators at NIMH.",
    budget           = list(direct_cost_cap = NA_real_, total_cost_cap = NA_real_, project_period_max = NA_character_),
    mechanisms       = c("K01"),
    career_stages    = c("early_career"),
    topics           = c("mental_health", "training_and_career"),
    dos              = c("Read the rescinded notice", "Update internal records"),
    donts            = c("Do not rely on rescinded guidance"),
    strategic_priorities = character()
  )
}

test_that("extract_llm_nih returns LLM fields and records the model label", {
  html <- read_fixture("NOT-MH-26-035.html")
  out <- extract_llm_nih(
    html,
    taxonomy_path = testthat::test_path("..", "..", "data", "taxonomy.yml"),
    chat_factory  = stub_chat_factory(valid_canned())
  )
  expect_equal(out$llm_model, "claude-haiku-4-5")
  expect_match(out$purpose_tldr, "rescinds")
  expect_setequal(out$topics, c("mental_health", "training_and_career"))
})

test_that("extract_llm_nih falls back to Sonnet on primary failure", {
  html <- read_fixture("NOT-MH-26-035.html")
  out <- suppressWarnings(extract_llm_nih(
    html,
    taxonomy_path = testthat::test_path("..", "..", "data", "taxonomy.yml"),
    chat_factory  = failing_then_succeeding_factory(valid_canned())
  ))
  expect_equal(out$llm_model, "claude-sonnet-4-6")
})

test_that("merge_extractions overlays LLM fields onto a rule record and validates", {
  html <- read_fixture("NOT-MH-26-035.html")
  rule_rec <- extract_rules_nih(html, url = "https://grants.nih.gov/grants/guide/notice-files/NOT-MH-26-035.html")
  llm_rec  <- valid_canned()
  llm_rec$llm_model <- "claude-haiku-4-5"

  full <- merge_extractions(rule_rec, llm_rec)
  expect_equal(full$notice_id, "NOT-MH-26-035")
  expect_equal(full$llm_model, "claude-haiku-4-5")
  expect_true(validate_notice(full))
})

test_that(".html_to_prompt_text strips scripts and styles but keeps section headers", {
  txt <- grantradar:::.html_to_prompt_text(read_fixture("NOT-MH-26-035.html"))
  expect_true(grepl("Key Dates", txt))
  expect_true(grepl("Purpose", txt))
  expect_false(grepl("googletagmanager", txt))
})
