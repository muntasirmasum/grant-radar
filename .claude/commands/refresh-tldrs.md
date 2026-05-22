---
description: Fill in LLM-extracted fields (purpose, eligibility, budget, do's/don'ts, topics) for any notice that the rule-only weekly refresh left empty. Uses your Claude subscription, not the API.
---

You are completing the LLM-extraction step of the `grant-radar` pipeline.
The Sunday cron has already populated rule-extracted fields (notice_id,
title, release_date, ICs, key_dates, related). Your job is to fill in
the free-text fields the rules can't reach.

# Workflow

## 1. Find the queue

Run this in Bash:
```sh
Rscript -e 'devtools::load_all(quiet = TRUE); print(notices_needing_llm(), n = 100)'
```
This prints every notice JSON whose `purpose_tldr` is empty/null. The
table includes `notice_id`, `json_path`, `html_path`, sorted newest first.

If the table is empty, stop — nothing to do.

## 2. For each notice, in order

**a. Read the HTML.** Use the Read tool on the `html_path` column.

**b. Extract the structured fields.** Output them as a JSON object with
exactly these keys. Be faithful to the notice — do NOT invent budget
figures, eligibility constraints, or strategic priorities. Leave numeric
caps as `null` if the notice doesn't state them. Summaries are 2-3
sentences, plain English, no marketing language.

```json
{
  "purpose_tldr":     "2-3 sentence summary in plain English.",
  "eligibility_tldr": "2-3 sentences on who can apply (institutions, PI eligibility, citizenship, career stage).",
  "budget": {
    "direct_cost_cap":    null,
    "total_cost_cap":     null,
    "project_period_max": null
  },
  "mechanisms":    ["R01", "R21"],
  "career_stages": ["any"],
  "topics":        ["mental_health", "training_and_career"],
  "dos":           ["3-7 concrete things an applicant SHOULD do."],
  "donts":         ["3-7 concrete things an applicant should NOT do."],
  "strategic_priorities": []
}
```

**Constraints:**
- `career_stages` items come from: `trainee`, `early_career`, `midcareer`, `established`, `any`.
- `topics` items come from `data/taxonomy.yml` (topics:.name list). 0-4 tags.
- `mechanisms` are NIH activity codes mentioned in the notice (R01, R21, K01, F31, U01, etc.); empty array if none.
- For pure-administrative notices (rescissions, simple changes), `dos` and `donts` can be 1-2 items each.

**c. Apply it.** In Bash:
```sh
Rscript -e '
  devtools::load_all(quiet = TRUE)
  llm <- jsonlite::fromJSON("/tmp/llm-NOT-XX-XX-XXX.json", simplifyVector = FALSE)
  apply_llm_fields("data/notices/2026/NOT-XX-XX-XXX.json", llm)
'
```
(Write the JSON object you produced to `/tmp/llm-<notice_id>.json` first
via the Write tool, then run the snippet above with the correct notice_id
substituted.)

## 3. Every 10 notices, checkpoint

Run:
```sh
Rscript -e 'devtools::load_all(quiet = TRUE); rollup_notices()'
git add data/
git commit -m "data: LLM enrichment batch ($(date -u +%Y-%m-%d))"
```

## 4. When the queue is empty

Final rollup + commit + push:
```sh
Rscript -e 'devtools::load_all(quiet = TRUE); rollup_notices()'
git add data/
git commit -m "data: LLM enrichment complete ($(date -u +%Y-%m-%d))" || true
git push
```

# Notes

- Always validate after applying. `apply_llm_fields()` calls
  `validate_notice()` internally and will error if the schema doesn't
  match — that's your guardrail.
- If a notice is too long to read in one go, focus on the first few
  thousand characters: title, Key Dates, Purpose, Eligibility, and any
  budget statements are usually in the first half.
- Do NOT modify rule-extracted fields (`notice_id`, `title`,
  `release_date`, `issuing_orgs`, `key_dates`, `related`). The merge
  function preserves them.
