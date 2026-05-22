# Where we left off — 2026-05-22

## State

- Site: <https://muntasirmasum.github.io/grant-radar/>
- Repo: <https://github.com/muntasirmasum/grant-radar>
- Last commit on `main`: dashboard visual overhaul (theme.scss + chips + value-box fix)
- 98 notices in `data/notices/2026/` covering Feb 6 – May 22, 2026
- 6 of them have full LLM enrichment (`/refresh-tldrs` walked manually); the other 92 are rule-only with `TL;DR pending` placeholders
- 61 tests passing (`devtools::test()`)
- CI: `ci` and `pages-deploy` workflows both green on `main`
- Cron: `weekly-refresh` scheduled for Sundays 23:00 UTC; rule-only, no API key needed

## To resume the project

```sh
cd ~/projects/grant-radar
git pull
Rscript -e 'devtools::load_all(); print(notices_needing_llm())'   # see what's queued
```

In Claude Code: open this repo and run `/refresh-tldrs` to fill in TL;DRs / topics / dos / donts on the remaining 92 notices.

## Open items, ranked

1. **Run `/refresh-tldrs` on the backlog** — biggest remaining value-add. ~92 notices, ~5-10 min of Claude Code time.
2. **Visual / UX polish** (deferred per your call):
   - Sidebar with persistent filters (IC / mechanism / topic / date range) driving every panel
   - KPI sparkline strip (last-8-week trend in each value box)
   - Treemap or sunburst of notices by IC
   - Dark-mode toggle
   - Card actions (hover, expand, "save for later" in localStorage)
3. **Extend backfill** to all of 2025: `backfill_range("2025-01-03", "2026-02-06")` — ~3k more notices, ~30 min runtime, paced 1 s/week.
4. **M6 — additional sources**:
   - NSF (different feed and schema)
   - AHRQ, CDC, DoD/CDMRP
   - Each is one new file under `R/source_<name>.R` implementing `list_week()` and `fetch_notice()` against the `Source` S7 interface.
5. **Schema / extractor improvements** as new edge cases surface (e.g., the empty `Release Date` on NOT-OD-26-076 is already handled; expect more like this).

## Things to remember

- The Sunday cron commits raw-only data; nothing happens to TL;DRs until you run `/refresh-tldrs` manually.
- API path is still in the code (`run_llm = TRUE` plus `ANTHROPIC_API_KEY`) if you ever decide the manual loop isn't worth it.
- All visual changes go through `site/theme.scss`; the index.qmd dashboard format is scoped to that one file so other pages keep their normal HTML format.
