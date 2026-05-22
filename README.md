# grant-radar

A public dashboard that ingests NIH funding notices weekly, extracts structured information with a hybrid rule + LLM pipeline, and presents them through faceted browse, a triage feed, decompressed TL;DR cards, and a forward-looking deadline calendar. Designed for pluggable sources (NSF, AHRQ, CDC, DoD/CDMRP coming after the NIH MVP is solid).

**Status:** M3 frontend wired. NIH source + hybrid extractor + roll-up + Quarto/OJS site are all in. Awaiting a first LLM-enabled refresh to populate `data/notices/`.

## Why

The NIH Guide for Grants and Contracts publishes dense, verbose HTML notices every week. Researchers either skim them and miss things, or read every word and lose hours. `grant-radar` does the reading and structuring once, then presents the result in a form researchers can scan in minutes.

## Architecture

See [`plan.md`](plan.md) for the full design. In brief:

```
NIH weekly index → fetcher → raw HTML cache
                                  ↓
                        rule extractor (headers, dates, IDs)
                                  ↓
                        LLM extractor (purpose, eligibility, do's/don'ts)
                                  ↓
                        schema-validated JSON per notice
                                  ↓
                        parquet roll-up
                                  ↓
                        Quarto + Observable JS site → GitHub Pages
```

The pipeline runs every Sunday evening (19:00 ET) via GitHub Actions and does the rule-only extraction (notice IDs, titles, dates, ICs, key dates, related announcements). The site is rebuilt and deployed automatically. Free-text fields (TL;DRs, do's and don'ts, topic tags) are filled in by running the `/refresh-tldrs` slash command in Claude Code, which uses your existing subscription rather than a paid API key.

## Local development

```r
# Install dependencies
install.packages(c("devtools","testthat","S7","rvest","httr2",
                   "jsonlite","jsonvalidate","digest","dplyr",
                   "stringr","tibble","purrr","cli","rlang",
                   "arrow","ellmer","yaml","fs","readr","xml2","withr"))

# Run tests
devtools::test()

# Refresh this week (rule extractor only; no API key needed)
devtools::load_all()
refresh_week(run_llm = FALSE)
rollup_notices()
```

Render the site (needs `quarto`):

```sh
cp data/notices.json site/notices.json
quarto render site/
```

For LLM enrichment after a refresh: open this directory in Claude Code and
run `/refresh-tldrs`. It walks every notice with a missing `purpose_tldr`,
extracts the free-text fields, and writes them back. No API key needed.

(The `R/extract_llm.R` path is still in the codebase for users who'd
rather pay the API; pass `run_llm = TRUE` to `refresh_week()` and set
`ANTHROPIC_API_KEY`.)

## License

MIT.
