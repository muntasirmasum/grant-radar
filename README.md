# grant-radar

A public dashboard that ingests NIH funding notices weekly, extracts structured information with a hybrid rule + LLM pipeline, and presents them through faceted browse, a triage feed, decompressed TL;DR cards, and a forward-looking deadline calendar. Designed for pluggable sources (NSF, AHRQ, CDC, DoD/CDMRP coming after the NIH MVP is solid).

**Status:** M0 — scaffolding.

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

The pipeline runs every Sunday evening (19:00 ET) via GitHub Actions, so the rebuilt site is live by Sunday night / Monday morning.

## Local development

```r
renv::restore()
source("R/pipeline.R")
refresh_week(Sys.Date())
```

Then render the site:

```sh
quarto render site/
```

## License

MIT.
