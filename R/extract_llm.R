#' LLM-based extraction of free-text fields from an NIH notice.
#'
#' Handles fields the rule extractor cannot reliably parse: a 2-3 sentence
#' purpose summary, eligibility summary, budget caps (when stated),
#' do's/don'ts, topics (constrained to the taxonomy), career stage(s), and
#' mechanism codes mentioned in the notice.
#'
#' Uses Anthropic Claude via the ellmer package. Default model is Haiku 4.5;
#' on schema-validation failure the same prompt is retried with Sonnet 4.6.

#' Strip an NIH notice's HTML down to readable text for prompting.
#'
#' We keep section headers so the LLM can anchor on "Purpose", "Eligibility",
#' "Section IV. Application and Submission Information", etc.
#' @keywords internal
.html_to_prompt_text <- function(html) {
  doc <- rvest::read_html(html)
  # Drop scripts, styles, navigation chrome.
  for (sel in c("script", "style", "nav", "footer", "header.banner")) {
    rvest::html_elements(doc, sel) |>
      lapply(xml2::xml_remove) |>
      invisible()
  }
  body <- rvest::html_element(doc, "body")
  txt <- if (length(body)) rvest::html_text2(body) else rvest::html_text2(doc)
  # Collapse runs of blank lines.
  txt <- stringr::str_replace_all(txt, "\\n{3,}", "\n\n")
  stringr::str_trim(txt)
}

#' Build the ellmer structured-output schema for LLM-handled fields.
#' @keywords internal
.llm_output_type <- function(topic_vocab) {
  ellmer::type_object(
    purpose_tldr     = ellmer::type_string("2-3 sentences summarizing the notice's purpose in plain English."),
    eligibility_tldr = ellmer::type_string("2-3 sentences summarizing who can apply (institutions, PI eligibility, citizenship, career stage)."),
    budget = ellmer::type_object(
      .description = "Funding limits if explicitly stated. Use null fields when not stated.",
      direct_cost_cap    = ellmer::type_number("Per-year direct cost cap in USD, if stated."),
      total_cost_cap     = ellmer::type_number("Total cost cap in USD, if stated."),
      project_period_max = ellmer::type_string("Maximum project period (e.g., '5 years'), if stated.")
    ),
    mechanisms = ellmer::type_array(
      items = ellmer::type_string(),
      description = "NIH activity codes referenced in the notice (e.g., R01, R21, K01, F31, U01). Empty array if none."
    ),
    career_stages = ellmer::type_array(
      items = ellmer::type_enum(c("trainee", "early_career", "midcareer", "established", "any")),
      description = "Career stage(s) the notice targets."
    ),
    topics = ellmer::type_array(
      items = ellmer::type_enum(topic_vocab),
      description = "Topic tags from the provided taxonomy. 0-4 tags."
    ),
    dos = ellmer::type_array(
      items = ellmer::type_string(),
      description = "3-7 concrete things an applicant SHOULD do, drawn from the notice."
    ),
    donts = ellmer::type_array(
      items = ellmer::type_string(),
      description = "3-7 concrete things an applicant should NOT do, drawn from the notice."
    ),
    strategic_priorities = ellmer::type_array(
      items = ellmer::type_string(),
      description = "Strategic priorities or program goals the notice explicitly references. May be empty."
    )
  )
}

#' Default system prompt for notice extraction.
#' @keywords internal
.llm_system_prompt <- function() {
  paste0(
    "You extract structured information from NIH funding notices for a public ",
    "research dashboard. Your output must be faithful to the notice text. ",
    "If a field is not stated, return null or an empty array. Do not invent ",
    "budget figures, eligibility constraints, or strategic priorities. ",
    "Summaries must be 2-3 sentences, plain English, no marketing language. ",
    "Do's and Don'ts must be concrete, action-oriented, and traceable to ",
    "text in the notice."
  )
}

#' Load topic vocabulary names from data/taxonomy.yml.
#' @keywords internal
.topic_vocab <- function(taxonomy_path = NULL) {
  if (is.null(taxonomy_path)) {
    taxonomy_path <- system.file("taxonomy.yml", package = "grantradar")
    if (!nzchar(taxonomy_path)) taxonomy_path <- "data/taxonomy.yml"
  }
  tax <- yaml::read_yaml(taxonomy_path)
  vapply(tax$topics, `[[`, character(1), "name")
}

#' Build a chat client. Wrapped in a function so tests can stub it.
#' @keywords internal
.build_chat <- function(model, system_prompt) {
  ellmer::chat_anthropic(model = model, system_prompt = system_prompt, echo = "none")
}

#' LLM-extract free-text fields from one NIH notice.
#'
#' @param html Character scalar HTML of one notice.
#' @param taxonomy_path Path to `taxonomy.yml`. Defaults to the installed one.
#' @param primary_model Model used first (Haiku 4.5 by default).
#' @param fallback_model Model retried on validation failure (Sonnet 4.6).
#' @param chat_factory Function `(model, system_prompt) -> ellmer Chat`. Injected
#'   so tests can stub.
#' @return A list with the LLM-handled fields, plus `llm_model` recording which
#'   model produced the result.
#' @export
extract_llm_nih <- function(html,
                            taxonomy_path = NULL,
                            primary_model = "claude-haiku-4-5",
                            fallback_model = "claude-sonnet-4-6",
                            chat_factory = .build_chat) {
  prompt_text <- .html_to_prompt_text(html)
  schema_type <- .llm_output_type(.topic_vocab(taxonomy_path))
  user_msg <- paste0(
    "Extract the structured fields from the notice below. ",
    "Follow the schema strictly.\n\n---\n", prompt_text
  )

  try_model <- function(model) {
    chat <- chat_factory(model, .llm_system_prompt())
    out <- chat$chat_structured(user_msg, type = schema_type)
    out$llm_model <- model
    out
  }

  result <- tryCatch(try_model(primary_model), error = function(e) {
    cli::cli_warn(c("Primary LLM extraction failed; retrying with fallback.",
                    "i" = "primary: {primary_model}", "i" = "fallback: {fallback_model}",
                    "x" = "{conditionMessage(e)}"))
    try_model(fallback_model)
  })

  result
}

#' Merge rule-extracted and LLM-extracted records into one schema-valid notice.
#'
#' Rule fields win for everything they cover; LLM fields fill the rest.
#' @export
merge_extractions <- function(rule_rec, llm_rec) {
  out <- rule_rec
  for (k in names(llm_rec)) out[[k]] <- llm_rec[[k]]
  out
}
