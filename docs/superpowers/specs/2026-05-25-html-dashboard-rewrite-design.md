# Grant Radar: HTML Dashboard Rewrite

**Date:** 2026-05-25
**Status:** Approved

## Goal

Replace the Quarto-based dashboard (`format: dashboard` + Observable JS) with a hand-built HTML/CSS/JS dashboard. Motivated by the "unreasonable effectiveness of HTML" philosophy: full visual control, zero build tools, self-contained static files.

## Visual Direction

**Paper Warm palette**, inspired by https://thariqs.github.io/html-effectiveness/

| Token | Value | Usage |
|-------|-------|-------|
| `--bg` | `#f5f0e8` | Page background |
| `--bg-card` | `#faf8f5` | Card / input backgrounds |
| `--bg-sidebar` | `#ebe5da` | Sidebar background |
| `--border` | `#ddd5c8` | Card borders, dividers |
| `--text` | `#2c2416` | Headings, primary text |
| `--text-secondary` | `#5a5040` | Body text, descriptions |
| `--text-muted` | `#8b7e6f` | Metadata, labels |
| `--navbar` | `#2c2416` | Navbar background (dark brown) |
| `--navbar-text` | `#f5f0e8` | Navbar text |
| `--chip-bg` | `#ebe5da` | Default chip background |
| `--chart-primary` | `#2c2416` | Topic bars, volume chart |
| `--chart-secondary` | `#5a5040` | IC bars |

Chip type colors (same semantic mapping as current):
- NOFO/RFA: green (`#d4edda` / `#155724`)
- Change: amber (`#fff3cd` / `#856404`)
- Rescission: red (`#fee2e2` / `#991b1b`)
- PA/PAR: indigo (`#e0e7ff` / `#3730a3`)
- Reissue: cyan (`#cffafe` / `#155e75`)
- Match badge: `#2c2416` bg, `#f5f0e8` text

Font: Inter (same as current).

## Scope

### Kept from current dashboard
- Ranked notice feed with chips, TL;DRs, profile-based ranking
- Three charts: top topics (bar), most active ICs (bar), weekly release volume (line/area)

### Removed
- KPI value boxes (5 stat cards)
- Upcoming deadlines panel

### New features
- Sidebar with persistent filters (IC, mechanism, topic, date range)
- Profile configuration integrated into sidebar (collapsible section)
- Dark mode toggle (navbar, persisted to localStorage)
- Card actions: expand (shows dos/donts/key dates) and save for later (localStorage)
- Full-text search bar in navbar (across title, notice_id, TL;DR, topics)

## Architecture

**Approach:** Multi-file vanilla HTML/CSS/JS. No build step, no framework.

### File structure

```
site/
  index.html      Page skeleton: navbar, sidebar, content zones
  style.css       Paper Warm palette, layout, cards, chips, dark mode
  app.js          State management, filtering, rendering, search
  charts.js       Observable Plot chart definitions
  notices.json    Data file (copied from data/ by CI)
```

### External dependencies (CDN)

- Observable Plot (for charts)
- D3 (Plot dependency, for scales/time formatting)

No other runtime dependencies.

### Data flow

1. `index.html` loads, links `style.css`, `app.js`, `charts.js`, and CDN scripts
2. `app.js` fetches `notices.json`, parses it, builds a search index
3. Profile loaded from `localStorage` key `grant-radar.profile.v1`
4. Central state object:
   ```js
   state = {
     notices: [],          // full dataset
     filters: {
       ics: [],            // selected IC names
       mechanisms: [],     // selected mechanisms
       topics: [],         // selected topics
       dateRange: "30d"    // "7d" | "30d" | "90d" | "all"
     },
     search: "",           // search query string
     profile: { ics: [], mechs: [], topics: [], career: "any" },
     saved: []             // notice IDs bookmarked by user
   }
   ```
5. Any state change calls `render()` which: filters notices by sidebar + search + date range, scores against profile, sorts (matched first, then by date), updates the feed heading to reflect the active date range (e.g. "Last 30 days" or "All notices"), updates feed DOM, re-renders charts via `charts.js`
6. Sidebar dropdowns, search bar, profile edits, and save/expand actions all mutate state and trigger `render()`

### Deployment

Same as current: CI copies `data/notices.json` to `site/notices.json`, then deploys `site/` to GitHub Pages. Quarto removed from the build pipeline. The `pages-deploy` workflow changes from "render Quarto + deploy docs/" to "copy data + deploy site/".

## Component Details

### Navbar
- Dark brown (`#2c2416`) bar, fixed at top
- Left: "Grant Radar" wordmark (Inter 700)
- Right: search input (debounced 200ms, substring match on title/notice_id/TL;DR/topics), dark mode toggle button

### Sidebar (left, 230px on desktop)
- Always visible on desktop (≥768px), collapses behind hamburger on mobile
- **My Profile** (collapsible): displays saved ICs, mechanisms, career stage as chips; click to edit via inline multi-select checklists; saves to localStorage
- **Filters**: four multi-select dropdown checklists (IC, Mechanism, Topic, Date Range). Each shows active count as badge. AND across categories, OR within.
- **Saved notices**: toggle to show only bookmarked notices
- **Clear all filters** button at bottom

### Notice cards
- White card (`#faf8f5`) on parchment background, 1px border, 10px radius
- **Chip row**: notice ID (monospace), type chip (color-coded), IC chips (max 2 + "+N" overflow), match score badge (if profile matches)
- **Title**: links to NIH URL (`target="_blank"`)
- **TL;DR**: one-line summary, or italic "TL;DR pending" if not yet enriched
- **Footer left**: release date, mechanisms (comma-separated), topics
- **Footer right**: expand button, save (heart) button
- **Expand**: toggles a detail section below the card showing dos/donts lists and key dates (from LLM enrichment fields). Only renders if data exists.
- **Save**: toggles heart icon, persists array of saved notice IDs to localStorage key `grant-radar.saved.v1`

### Charts row
Below the notice feed, under a "Trends" heading. Three equal-width cards:

1. **Top Topics (bar)**: horizontal bars, `#2c2416` fill, filtered to current date range, top 8
2. **Most Active ICs (bar)**: horizontal bars, `#5a5040` fill, filtered, top 8
3. **Weekly Volume (line/area)**: time series, warm brown area fill with line, last 12 weeks of filtered data

All three rendered by Observable Plot into `<div>` containers. `charts.js` exports a `renderCharts(filteredNotices, containers)` function called by `app.js` on each `render()`.

### Dark mode
- Toggle in navbar, persisted to localStorage key `grant-radar.theme`
- Sets `data-theme="dark"` on `<html>`
- All colors defined as CSS custom properties on `:root` and overridden under `[data-theme="dark"]`
- Dark palette: charcoal body (#1a1510), slightly lighter cards (#252015), warm grey text, same accent colors adjusted for legibility

### Search
- Substring match (case-insensitive) across `title`, `notice_id`, `purpose_tldr`, and `topics` array (joined)
- Debounced at 200ms
- Filters feed and charts in real time
- Stacks with sidebar filters (search AND filters both apply)

## Migration notes

- `site/index.qmd` and `site/theme.scss` are replaced by `index.html` and `style.css`
- `site/profile.html` can be removed (profile now lives in sidebar)
- The `_quarto.yml` project config is no longer needed for the dashboard
- CI workflow `pages-deploy` simplifies: no Quarto render step, just copy data and deploy `site/`
- Existing `data/` pipeline, R package, tests, and cron workflow are unchanged
- The `/refresh-tldrs` slash command continues to work as before (it writes to `data/notices/`)
