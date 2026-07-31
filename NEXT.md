# Where we left off — 2026-05-26

## State

- Site: <https://muntasirmasum.github.io/grant-radar/>
- Repo: <https://github.com/muntasirmasum/grant-radar>
- Last commit on `main`: HTML dashboard rewrite (7 commits pushed)
- 98 notices in `data/notices/2026/` covering Feb 6 – May 22, 2026
- 6 of them have full LLM enrichment; the other 92 show "TL;DR pending"
- CI: `pages-deploy` now deploys `site/` directly (no Quarto render)
- Cron: `weekly-refresh` still scheduled for Sundays 23:00 UTC

## What changed this session

- **Replaced Quarto dashboard with vanilla HTML/CSS/JS** (Paper Warm palette)
- New files: `site/index.html`, `site/style.css`, `site/app.js`, `site/charts.js`, `site/about.html`
- Deleted: `site/index.qmd`, `site/profile.qmd`, `site/theme.scss`, `site/about.qmd`
- CI updated: no Quarto setup/render, deploys `site/` as static files
- Design spec: `docs/superpowers/specs/2026-05-25-html-dashboard-rewrite-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-25-html-dashboard-rewrite.md`

## New features in the HTML dashboard

- **Sidebar filters**: IC, mechanism, topic, date range (multi-select checklists, AND across categories, OR within)
- **Profile in sidebar**: collapsible section, saves to localStorage, ranks notices by match score
- **Dark mode**: toggle in navbar, persisted to localStorage
- **Card actions**: expand (shows dos/donts/key dates), save for later (heart icon, localStorage)
- **Full-text search**: debounced 200ms, filters feed and charts in real time
- **Charts**: Observable Plot (CDN), three charts respond to all filters

## Visual design

- **Palette**: Paper Warm (parchment #f5f0e8 background, dark brown #2c2416 navbar, warm tan #ebe5da sidebar, off-white #faf8f5 cards)
- **Dark mode**: charcoal body #1a1510, lighter cards #252015
- **Font**: Inter (same as before)
- **Responsive**: sidebar collapses behind hamburger on mobile (<768px)

## To resume the project

```sh
cd ~/projects/grant-radar
git pull
cp data/notices.json site/notices.json
cd site && python3 -m http.server 8080
# open http://localhost:8080
```

In Claude Code: run `/refresh-tldrs` to fill in TL;DRs on the remaining 92 notices.

## Open items, ranked

1. **Run `/refresh-tldrs` on the backlog** — biggest remaining value-add. ~92 notices need LLM enrichment.
2. **Test the deployed site** — verify GitHub Pages deploy worked after the CI change.
3. **Convert remaining Quarto pages** — `browse.qmd` and `calendar.qmd` still exist as Quarto files but are not rendered by CI. Convert to static HTML or remove.
4. **Visual polish** — KPI sparklines, treemap/sunburst, card hover animations.
5. **Extend backfill** to all of 2025: `backfill_range("2025-01-03", "2026-02-06")`.
6. **Additional sources** — NSF, AHRQ, CDC, DoD/CDMRP.
