# HTML Dashboard Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Quarto dashboard with a hand-built HTML/CSS/JS dashboard using the Paper Warm palette, sidebar filters, dark mode, card actions, and full-text search.

**Architecture:** Multi-file vanilla HTML/CSS/JS (no build step, no framework). Central `state` object drives a single `render()` function. Observable Plot loaded via CDN for charts. Data from static `notices.json` via `fetch()`. Deployed as static files to GitHub Pages.

**Tech Stack:** HTML5, CSS custom properties, vanilla JS (ES modules), Observable Plot + D3 (CDN), GitHub Pages

**Spec:** `docs/superpowers/specs/2026-05-25-html-dashboard-rewrite-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `site/index.html` | Create | Page skeleton: navbar, sidebar, content zones, CDN script tags |
| `site/style.css` | Create | Paper Warm palette (CSS custom properties), layout, cards, chips, sidebar, dark mode overrides, responsive breakpoints |
| `site/app.js` | Create | State management, data loading, filtering, search (debounced), profile management, DOM rendering, event wiring |
| `site/charts.js` | Create | Observable Plot chart definitions, `renderCharts()` export |
| `.github/workflows/pages-deploy.yml` | Modify | Remove Quarto setup/render, deploy `site/` directly |
| `site/index.qmd` | Delete | Replaced by `index.html` |
| `site/theme.scss` | Delete | Replaced by `style.css` |
| `site/profile.qmd` | Delete | Profile now lives in sidebar |
| `site/_quarto.yml` | Modify | Remove dashboard-specific config; keep if browse/calendar/about pages remain as Quarto |

**Note on other Quarto pages:** `browse.qmd`, `calendar.qmd`, and `about.qmd` still exist. The spec does not cover rewriting them. The plan keeps `_quarto.yml` intact but updates the navbar to link to the new `index.html`. The CI workflow renders the remaining Quarto pages and also deploys `index.html` + `style.css` + `app.js` + `charts.js` alongside them.

---

### Task 1: Create `site/style.css` with Paper Warm palette and layout

**Files:**
- Create: `site/style.css`

- [ ] **Step 1: Create `style.css` with CSS custom properties for Paper Warm light theme**

```css
/* site/style.css */
:root {
  --bg: #f5f0e8;
  --bg-card: #faf8f5;
  --bg-sidebar: #ebe5da;
  --border: #ddd5c8;
  --text: #2c2416;
  --text-secondary: #5a5040;
  --text-muted: #8b7e6f;
  --navbar-bg: #2c2416;
  --navbar-text: #f5f0e8;
  --chip-bg: #ebe5da;
  --chart-primary: #2c2416;
  --chart-secondary: #5a5040;
  --radius: 10px;
  --radius-sm: 6px;
  --radius-pill: 99px;
  --font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}

[data-theme="dark"] {
  --bg: #1a1510;
  --bg-card: #252015;
  --bg-sidebar: #1f1b14;
  --border: #3d3428;
  --text: #e8e0d4;
  --text-secondary: #b8a98f;
  --text-muted: #8b7e6f;
  --navbar-bg: #0f0c08;
  --navbar-text: #e8e0d4;
  --chip-bg: #2c2416;
  --chart-primary: #b8a98f;
  --chart-secondary: #8b7e6f;
}
```

- [ ] **Step 2: Add Google Fonts import, reset, and body styles**

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text-secondary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  line-height: 1.5;
}
```

- [ ] **Step 3: Add navbar styles**

```css
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--navbar-bg);
  color: var(--navbar-text);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 1.2rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.navbar__brand {
  font-weight: 700;
  font-size: 1.15rem;
  letter-spacing: -0.02em;
  color: var(--navbar-text);
  text-decoration: none;
}
.navbar__right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.navbar__search {
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: var(--radius-sm);
  padding: 0.4rem 0.8rem;
  color: var(--navbar-text);
  font-size: 0.82rem;
  width: 260px;
  outline: none;
  font-family: var(--font);
}
.navbar__search::placeholder { color: rgba(245,240,232,0.5); }
.navbar__search:focus { background: rgba(255,255,255,0.18); border-color: rgba(255,255,255,0.3); }
.navbar__toggle {
  background: rgba(255,255,255,0.12);
  border: none;
  border-radius: var(--radius-sm);
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1rem;
}
.navbar__hamburger {
  display: none;
  background: none;
  border: none;
  color: var(--navbar-text);
  font-size: 1.4rem;
  cursor: pointer;
}
```

- [ ] **Step 4: Add layout styles (sidebar + main content)**

```css
.layout {
  display: flex;
  min-height: calc(100vh - 52px);
}

/* Sidebar */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  padding: 1rem;
  overflow-y: auto;
  font-size: 0.78rem;
  color: var(--text-muted);
}
.sidebar__section { margin-bottom: 1.2rem; }
.sidebar__heading {
  font-weight: 700;
  font-size: 0.82rem;
  color: var(--text);
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.sidebar__heading .arrow { transition: transform 0.15s; font-size: 0.65rem; }
.sidebar__heading .arrow--collapsed { transform: rotate(-90deg); }

/* Filter dropdowns */
.filter-group { margin-bottom: 0.6rem; }
.filter-group__label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  margin-bottom: 0.2rem;
}
.filter-group__trigger {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.35rem 0.5rem;
  font-size: 0.76rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-secondary);
  width: 100%;
}
.filter-group__trigger .badge {
  background: var(--text);
  color: var(--bg-card);
  border-radius: var(--radius-pill);
  padding: 0 0.4rem;
  font-size: 0.62rem;
  font-weight: 600;
  margin-left: 0.3rem;
}
.filter-group__list {
  display: none;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin-top: 0.25rem;
  max-height: 180px;
  overflow-y: auto;
  padding: 0.3rem;
}
.filter-group__list.open { display: block; }
.filter-group__item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.35rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.74rem;
  color: var(--text-secondary);
}
.filter-group__item:hover { background: var(--bg-sidebar); }
.filter-group__item input[type="checkbox"] { accent-color: var(--text); }

.sidebar__clear {
  background: transparent;
  border: 1px solid var(--text-muted);
  border-radius: var(--radius-sm);
  padding: 0.35rem;
  text-align: center;
  font-size: 0.74rem;
  color: var(--text-muted);
  cursor: pointer;
  width: 100%;
  font-family: var(--font);
}
.sidebar__clear:hover { border-color: var(--text); color: var(--text); }

/* Profile chips in sidebar */
.profile-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.3rem;
}
.profile-chip {
  background: var(--bg-card);
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  font-size: 0.65rem;
  color: var(--text-secondary);
}
```

- [ ] **Step 5: Add main content and notice card styles**

```css
/* Main content area */
.main {
  flex: 1;
  padding: 1.4rem;
  overflow-y: auto;
}
.main__heading {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text);
  margin-bottom: 0.8rem;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.main__heading-meta {
  font-size: 0.74rem;
  color: var(--text-muted);
  font-weight: 400;
}

/* Notice cards */
.notice {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
  margin-bottom: 0.8rem;
}
.notice__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-bottom: 0.35rem;
}
.chip {
  display: inline-block;
  padding: 0.08rem 0.45rem;
  border-radius: var(--radius-pill);
  font-size: 0.65rem;
  font-weight: 500;
  background: var(--chip-bg);
  color: var(--text-secondary);
  line-height: 1.5;
}
.chip--id { font-family: var(--font-mono); color: var(--text-muted); }
.chip--nofo, .chip--rfa { background: #d4edda; color: #155724; }
.chip--change { background: #fff3cd; color: #856404; }
.chip--rescission { background: #fee2e2; color: #991b1b; }
.chip--pa, .chip--par { background: #e0e7ff; color: #3730a3; }
.chip--reissue { background: #cffafe; color: #155e75; }
.chip--match { background: var(--text); color: var(--bg-card); font-weight: 600; }

[data-theme="dark"] .chip--nofo, [data-theme="dark"] .chip--rfa { background: #065f46; color: #d1fae5; }
[data-theme="dark"] .chip--change { background: #78350f; color: #fef3c7; }
[data-theme="dark"] .chip--rescission { background: #7f1d1d; color: #fee2e2; }
[data-theme="dark"] .chip--pa, [data-theme="dark"] .chip--par { background: #312e81; color: #e0e7ff; }
[data-theme="dark"] .chip--reissue { background: #164e63; color: #cffafe; }

.notice__title {
  font-weight: 600;
  font-size: 0.88rem;
  line-height: 1.35;
  margin-bottom: 0.25rem;
}
.notice__title a {
  color: var(--text);
  text-decoration: none;
  border-bottom: 1px solid transparent;
}
.notice__title a:hover { color: #2563eb; border-bottom-color: #2563eb; }
.notice__tldr {
  font-size: 0.82rem;
  line-height: 1.45;
  color: var(--text-secondary);
  margin-bottom: 0.3rem;
}
.notice__tldr--pending {
  font-style: italic;
  color: var(--text-muted);
  font-size: 0.78rem;
}
.notice__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.72rem;
  color: var(--text-muted);
}
.notice__actions {
  display: flex;
  gap: 0.4rem;
}
.notice__action {
  background: var(--chip-bg);
  border: none;
  border-radius: 4px;
  padding: 0.15rem 0.45rem;
  font-size: 0.68rem;
  color: var(--text-muted);
  cursor: pointer;
  font-family: var(--font);
}
.notice__action:hover { background: var(--border); color: var(--text); }
.notice__action--saved { color: #dc2626; }

/* Expand detail */
.notice__detail {
  display: none;
  margin-top: 0.6rem;
  padding-top: 0.6rem;
  border-top: 1px solid var(--border);
  font-size: 0.78rem;
  color: var(--text-secondary);
}
.notice__detail.open { display: block; }
.notice__detail h4 {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text);
  margin: 0.5rem 0 0.2rem;
}
.notice__detail h4:first-child { margin-top: 0; }
.notice__detail ul {
  padding-left: 1.2rem;
  margin: 0;
}
.notice__detail li { margin-bottom: 0.15rem; }
```

- [ ] **Step 6: Add charts row and responsive styles**

```css
/* Charts row */
.charts-heading {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text);
  margin: 1.5rem 0 0.8rem;
}
.charts-row {
  display: flex;
  gap: 0.8rem;
}
.chart-card {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.8rem;
}
.chart-card__title {
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}
.chart-card svg text { fill: var(--text-secondary) !important; }
.chart-card svg [aria-label="x-axis tick"] text,
.chart-card svg [aria-label="y-axis tick"] text { fill: var(--text-muted) !important; }

/* Responsive */
@media (max-width: 767px) {
  .navbar__hamburger { display: flex; }
  .navbar__search { width: 160px; }
  .sidebar {
    position: fixed;
    top: 52px;
    left: -260px;
    height: calc(100vh - 52px);
    z-index: 90;
    transition: left 0.2s;
    box-shadow: 2px 0 8px rgba(0,0,0,0.15);
  }
  .sidebar.open { left: 0; }
  .charts-row { flex-direction: column; }
}

/* Scrollbar styling */
.sidebar::-webkit-scrollbar,
.filter-group__list::-webkit-scrollbar { width: 5px; }
.sidebar::-webkit-scrollbar-thumb,
.filter-group__list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* Empty state */
.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--text-muted);
  font-size: 0.88rem;
}
```

- [ ] **Step 7: Open `site/style.css` in a browser with a test HTML file to visually verify**

Create a temporary `site/_test.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="style.css">
  <title>Style Test</title>
</head>
<body>
  <div class="navbar">
    <a class="navbar__brand" href="#">Grant Radar</a>
    <div class="navbar__right">
      <input class="navbar__search" placeholder="Search notices...">
      <button class="navbar__toggle">☀️</button>
    </div>
  </div>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar__section">
        <div class="sidebar__heading">My Profile <span class="arrow">▾</span></div>
        <div class="profile-chips">
          <span class="profile-chip">NCI</span>
          <span class="profile-chip">NIMHD</span>
          <span class="profile-chip">Early-stage</span>
        </div>
      </div>
      <div class="sidebar__heading">Filters</div>
      <div class="filter-group">
        <div class="filter-group__label">Institute / Center</div>
        <div class="filter-group__trigger">All ICs <span>▾</span></div>
      </div>
    </aside>
    <main class="main">
      <div class="main__heading">Last 30 days <span class="main__heading-meta">6 notices</span></div>
      <div class="notice">
        <div class="notice__chips">
          <span class="chip chip--id">NOT-CA-26-018</span>
          <span class="chip chip--nofo">NOFO</span>
          <span class="chip">NCI</span>
          <span class="chip chip--match">match 2</span>
        </div>
        <div class="notice__title"><a href="#">Example Notice Title Here</a></div>
        <div class="notice__tldr">Supports early-stage investigators studying social determinants.</div>
        <div class="notice__footer">
          <span>2026-05-20 · R21 · health equity</span>
          <div class="notice__actions">
            <button class="notice__action">⤢ expand</button>
            <button class="notice__action">♡ save</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</body>
</html>
```

Run: `open site/_test.html` (macOS) and verify the Paper Warm palette renders correctly.

- [ ] **Step 8: Delete the test file and commit**

```bash
rm site/_test.html
git add site/style.css
git commit -m "feat: add Paper Warm stylesheet for HTML dashboard"
```

---

### Task 2: Create `site/index.html` page skeleton

**Files:**
- Create: `site/index.html`

- [ ] **Step 1: Create `index.html` with full page structure**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grant Radar</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav class="navbar">
    <div style="display:flex;align-items:center;gap:0.75rem;">
      <button class="navbar__hamburger" id="hamburger" aria-label="Toggle sidebar">☰</button>
      <a class="navbar__brand" href="#">Grant Radar</a>
    </div>
    <div class="navbar__right">
      <input class="navbar__search" id="search" placeholder="Search notices..." autocomplete="off">
      <button class="navbar__toggle" id="theme-toggle" aria-label="Toggle dark mode">☀️</button>
    </div>
  </nav>

  <div class="layout">
    <aside class="sidebar" id="sidebar">
      <!-- Profile section -->
      <div class="sidebar__section" id="profile-section">
        <div class="sidebar__heading" id="profile-toggle">
          My Profile <span class="arrow">▾</span>
        </div>
        <div id="profile-body">
          <div class="profile-chips" id="profile-chips"></div>
          <div id="profile-editor" style="display:none;"></div>
        </div>
      </div>

      <!-- Filters -->
      <div class="sidebar__section">
        <div class="sidebar__heading">Filters</div>

        <div class="filter-group">
          <div class="filter-group__label">Institute / Center</div>
          <div class="filter-group__trigger" data-filter="ics">All ICs <span>▾</span></div>
          <div class="filter-group__list" id="filter-ics"></div>
        </div>

        <div class="filter-group">
          <div class="filter-group__label">Mechanism</div>
          <div class="filter-group__trigger" data-filter="mechanisms">All mechanisms <span>▾</span></div>
          <div class="filter-group__list" id="filter-mechanisms"></div>
        </div>

        <div class="filter-group">
          <div class="filter-group__label">Topic</div>
          <div class="filter-group__trigger" data-filter="topics">All topics <span>▾</span></div>
          <div class="filter-group__list" id="filter-topics"></div>
        </div>

        <div class="filter-group">
          <div class="filter-group__label">Date Range</div>
          <div class="filter-group__trigger" data-filter="dateRange">Last 30 days <span>▾</span></div>
          <div class="filter-group__list" id="filter-dateRange"></div>
        </div>
      </div>

      <!-- Saved filter + clear -->
      <div class="sidebar__section">
        <label class="filter-group__item" style="margin-bottom:0.5rem;">
          <input type="checkbox" id="saved-only"> Saved notices only
        </label>
        <button class="sidebar__clear" id="clear-filters">Clear all filters</button>
      </div>
    </aside>

    <main class="main">
      <div class="main__heading">
        <span id="feed-heading">Last 30 days</span>
        <span class="main__heading-meta" id="feed-meta"></span>
      </div>
      <div id="feed"></div>

      <div class="charts-heading">Trends</div>
      <div class="charts-row">
        <div class="chart-card">
          <div class="chart-card__title">Top Topics</div>
          <div id="chart-topics"></div>
        </div>
        <div class="chart-card">
          <div class="chart-card__title">Most Active ICs</div>
          <div id="chart-ics"></div>
        </div>
        <div class="chart-card">
          <div class="chart-card__title">Weekly Volume</div>
          <div id="chart-volume"></div>
        </div>
      </div>
    </main>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script src="https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6"></script>
  <script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Open in browser to verify skeleton renders with correct layout**

Run: `open site/index.html`

Expected: dark brown navbar, warm tan sidebar on left, parchment-colored main area on right, empty chart card placeholders at bottom.

- [ ] **Step 3: Commit**

```bash
git add site/index.html
git commit -m "feat: add HTML page skeleton for dashboard"
```

---

### Task 3: Create `site/charts.js` with Observable Plot chart definitions

**Files:**
- Create: `site/charts.js`

- [ ] **Step 1: Create `charts.js` with `renderCharts()` function**

```js
// site/charts.js

export function renderCharts(notices, containers) {
  renderTopics(notices, containers.topics);
  renderICs(notices, containers.ics);
  renderVolume(notices, containers.volume);
}

function renderTopics(notices, el) {
  const counts = new Map();
  for (const n of notices) {
    for (const t of (n.topics || [])) {
      counts.set(t, (counts.get(t) || 0) + 1);
    }
  }
  const data = Array.from(counts, ([topic, n]) => ({ topic, n }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 8);

  el.innerHTML = "";
  if (data.length === 0) {
    el.innerHTML = '<div class="empty-state">No topic data</div>';
    return;
  }

  const style = getComputedStyle(document.documentElement);
  const fill = style.getPropertyValue("--chart-primary").trim();

  el.appendChild(
    Plot.plot({
      marginLeft: 140,
      height: 260,
      y: { label: null },
      x: { label: "notices", grid: true, ticks: 4 },
      style: { fontSize: "11px", background: "transparent" },
      marks: [
        Plot.barX(data, {
          y: "topic", x: "n", fill,
          sort: { y: "x", reverse: true },
        }),
        Plot.text(data, {
          y: "topic", x: "n", text: "n",
          dx: 5, textAnchor: "start", fill: style.getPropertyValue("--text").trim(), fontWeight: 600,
        }),
        Plot.ruleX([0]),
      ],
    })
  );
}

function renderICs(notices, el) {
  const counts = new Map();
  for (const n of notices) {
    for (const ic of (n.issuing_orgs || [])) {
      counts.set(ic, (counts.get(ic) || 0) + 1);
    }
  }
  const data = Array.from(counts, ([ic, n]) => ({ ic, n }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 8);

  el.innerHTML = "";
  if (data.length === 0) {
    el.innerHTML = '<div class="empty-state">No IC data</div>';
    return;
  }

  const style = getComputedStyle(document.documentElement);
  const fill = style.getPropertyValue("--chart-secondary").trim();

  el.appendChild(
    Plot.plot({
      marginLeft: 200,
      height: 260,
      y: { label: null },
      x: { label: "notices", grid: true, ticks: 4 },
      style: { fontSize: "11px", background: "transparent" },
      marks: [
        Plot.barX(data, {
          y: (d) => d.ic.length > 38 ? d.ic.slice(0, 36) + "…" : d.ic,
          x: "n", fill,
          sort: { y: "x", reverse: true },
        }),
        Plot.text(data, {
          y: (d) => d.ic.length > 38 ? d.ic.slice(0, 36) + "…" : d.ic,
          x: "n", text: "n",
          dx: 5, textAnchor: "start", fill: style.getPropertyValue("--text").trim(), fontWeight: 600,
        }),
        Plot.ruleX([0]),
      ],
    })
  );
}

function renderVolume(notices, el) {
  const buckets = new Map();
  for (const n of notices) {
    if (!n.release_date) continue;
    const d = new Date(n.release_date);
    const mon = new Date(d);
    mon.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    const key = mon.toISOString().slice(0, 10);
    buckets.set(key, (buckets.get(key) || 0) + 1);
  }
  const data = Array.from(buckets, ([week, n]) => ({ week: new Date(week), n }))
    .sort((a, b) => a.week - b.week)
    .slice(-12);

  el.innerHTML = "";
  if (data.length === 0) {
    el.innerHTML = '<div class="empty-state">No volume data</div>';
    return;
  }

  const style = getComputedStyle(document.documentElement);
  const stroke = style.getPropertyValue("--chart-primary").trim();

  el.appendChild(
    Plot.plot({
      height: 260,
      y: { label: "notices / week", grid: true, ticks: 4 },
      x: { label: null, type: "time" },
      style: { fontSize: "11px", background: "transparent" },
      marks: [
        Plot.areaY(data, {
          x: "week", y: "n",
          fill: stroke, fillOpacity: 0.12, curve: "monotone-x",
        }),
        Plot.lineY(data, {
          x: "week", y: "n",
          stroke, strokeWidth: 2.5, curve: "monotone-x",
        }),
        Plot.dot(data, { x: "week", y: "n", fill: stroke, r: 3.5 }),
        Plot.ruleY([0]),
      ],
    })
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add site/charts.js
git commit -m "feat: add Observable Plot chart definitions"
```

---

### Task 4: Create `site/app.js` with state management and rendering

**Files:**
- Create: `site/app.js`

This is the largest file. It wires everything together: loads data, manages state, renders the feed, wires sidebar filters, search, profile, dark mode, and card actions.

- [ ] **Step 1: Create `app.js` with state initialization and data loading**

```js
// site/app.js
import { renderCharts } from "./charts.js";

// --- State ---
const state = {
  notices: [],
  filters: { ics: [], mechanisms: [], topics: [], dateRange: "30d" },
  search: "",
  profile: { ics: [], mechs: [], topics: [], career: "any" },
  saved: [],
  savedOnly: false,
};

// --- DOM refs ---
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
  feed: $("#feed"),
  feedHeading: $("#feed-heading"),
  feedMeta: $("#feed-meta"),
  search: $("#search"),
  themeToggle: $("#theme-toggle"),
  hamburger: $("#hamburger"),
  sidebar: $("#sidebar"),
  profileChips: $("#profile-chips"),
  profileEditor: $("#profile-editor"),
  profileToggle: $("#profile-toggle"),
  savedOnly: $("#saved-only"),
  clearFilters: $("#clear-filters"),
  chartTopics: $("#chart-topics"),
  chartICs: $("#chart-ics"),
  chartVolume: $("#chart-volume"),
};

// --- Init ---
async function init() {
  loadTheme();
  loadProfile();
  loadSaved();
  await loadNotices();
  buildFilterOptions();
  wireEvents();
  render();
}

async function loadNotices() {
  try {
    const resp = await fetch("notices.json");
    state.notices = await resp.json();
  } catch (e) {
    state.notices = [];
  }
}

function loadProfile() {
  try {
    const raw = localStorage.getItem("grant-radar.profile.v1");
    if (raw) state.profile = JSON.parse(raw);
  } catch (e) { /* use defaults */ }
}

function saveProfile() {
  localStorage.setItem("grant-radar.profile.v1", JSON.stringify(state.profile));
}

function loadSaved() {
  try {
    const raw = localStorage.getItem("grant-radar.saved.v1");
    if (raw) state.saved = JSON.parse(raw);
  } catch (e) { /* use defaults */ }
}

function saveSaved() {
  localStorage.setItem("grant-radar.saved.v1", JSON.stringify(state.saved));
}
```

- [ ] **Step 2: Add theme (dark mode) management**

Append to `app.js`:

```js
// --- Theme ---
function loadTheme() {
  const saved = localStorage.getItem("grant-radar.theme");
  if (saved === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
    dom.themeToggle.textContent = "🌙";
  }
}

function toggleTheme() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  if (isDark) {
    document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("grant-radar.theme", "light");
    dom.themeToggle.textContent = "☀️";
  } else {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("grant-radar.theme", "dark");
    dom.themeToggle.textContent = "🌙";
  }
  render();
}
```

- [ ] **Step 3: Add filter options builder and filter logic**

Append to `app.js`:

```js
// --- Filters ---
function collectUnique(key) {
  const set = new Set();
  for (const n of state.notices) {
    for (const v of (n[key] || [])) set.add(v);
  }
  return Array.from(set).sort();
}

function buildFilterOptions() {
  buildChecklist("filter-ics", collectUnique("issuing_orgs"), "ics");
  buildChecklist("filter-mechanisms", collectUnique("mechanisms"), "mechanisms");
  buildChecklist("filter-topics", collectUnique("topics"), "topics");
  buildDateRangeFilter();
}

function buildChecklist(containerId, options, stateKey) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  for (const opt of options) {
    const label = document.createElement("label");
    label.className = "filter-group__item";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = opt;
    cb.addEventListener("change", () => {
      if (cb.checked) {
        state.filters[stateKey].push(opt);
      } else {
        state.filters[stateKey] = state.filters[stateKey].filter((v) => v !== opt);
      }
      updateTriggerLabel(stateKey);
      render();
    });
    const text = document.createTextNode(" " + (opt.length > 35 ? opt.slice(0, 33) + "…" : opt));
    label.appendChild(cb);
    label.appendChild(text);
    container.appendChild(label);
  }
}

function buildDateRangeFilter() {
  const container = document.getElementById("filter-dateRange");
  container.innerHTML = "";
  const ranges = [
    { label: "Last 7 days", value: "7d" },
    { label: "Last 30 days", value: "30d" },
    { label: "Last 90 days", value: "90d" },
    { label: "All notices", value: "all" },
  ];
  for (const r of ranges) {
    const label = document.createElement("label");
    label.className = "filter-group__item";
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "dateRange";
    radio.value = r.value;
    radio.checked = r.value === state.filters.dateRange;
    radio.addEventListener("change", () => {
      state.filters.dateRange = r.value;
      updateTriggerLabel("dateRange");
      render();
    });
    const text = document.createTextNode(" " + r.label);
    label.appendChild(radio);
    label.appendChild(text);
    container.appendChild(label);
  }
}

function updateTriggerLabel(stateKey) {
  const trigger = document.querySelector(`[data-filter="${stateKey}"]`);
  if (!trigger) return;
  if (stateKey === "dateRange") {
    const labels = { "7d": "Last 7 days", "30d": "Last 30 days", "90d": "Last 90 days", all: "All notices" };
    trigger.innerHTML = `${labels[state.filters.dateRange]} <span>▾</span>`;
    return;
  }
  const count = state.filters[stateKey].length;
  const labels = { ics: "ICs", mechanisms: "mechanisms", topics: "topics" };
  if (count === 0) {
    trigger.innerHTML = `All ${labels[stateKey]} <span>▾</span>`;
  } else {
    trigger.innerHTML = `${labels[stateKey]} <span class="badge">${count}</span> <span>▾</span>`;
  }
}
```

- [ ] **Step 4: Add search with debounce**

Append to `app.js`:

```js
// --- Search ---
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

function matchesSearch(notice, query) {
  if (!query) return true;
  const q = query.toLowerCase();
  const haystack = [
    notice.title,
    notice.notice_id,
    notice.purpose_tldr,
    (notice.topics || []).join(" "),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}
```

- [ ] **Step 5: Add profile rendering and editing**

Append to `app.js`:

```js
// --- Profile ---
function renderProfileChips() {
  const parts = [];
  for (const ic of state.profile.ics) {
    parts.push(`<span class="profile-chip">${ic.replace(/^National (Institute|Center) of? /, "")}</span>`);
  }
  for (const m of state.profile.mechs) {
    parts.push(`<span class="profile-chip">${m}</span>`);
  }
  for (const t of state.profile.topics) {
    parts.push(`<span class="profile-chip">${t}</span>`);
  }
  if (state.profile.career && state.profile.career !== "any") {
    parts.push(`<span class="profile-chip">${state.profile.career}</span>`);
  }
  if (parts.length === 0) {
    dom.profileChips.innerHTML = '<span style="font-size:0.72rem;color:var(--text-muted);">No profile set. Click to configure.</span>';
  } else {
    dom.profileChips.innerHTML = parts.join("");
  }
}

function renderProfileEditor() {
  const allICs = collectUnique("issuing_orgs");
  const allMechs = collectUnique("mechanisms");
  const allTopics = collectUnique("topics");
  const careers = ["any", "early-stage", "mid-career", "established"];

  let html = '<div style="margin-top:0.5rem;font-size:0.72rem;">';
  html += buildProfileMultiSelect("ICs", allICs, state.profile.ics, "profile-ics");
  html += buildProfileMultiSelect("Mechanisms", allMechs, state.profile.mechs, "profile-mechs");
  html += buildProfileMultiSelect("Topics", allTopics, state.profile.topics, "profile-topics");
  html += `<div style="margin-top:0.4rem;"><strong>Career:</strong> <select id="profile-career" style="font-size:0.72rem;padding:0.2rem;border-radius:4px;border:1px solid var(--border);background:var(--bg-card);color:var(--text-secondary);">`;
  for (const c of careers) {
    html += `<option value="${c}" ${state.profile.career === c ? "selected" : ""}>${c}</option>`;
  }
  html += `</select></div>`;
  html += `<button id="profile-save" style="margin-top:0.5rem;padding:0.3rem 0.8rem;font-size:0.72rem;border-radius:4px;border:1px solid var(--text);background:var(--text);color:var(--bg-card);cursor:pointer;font-family:var(--font);">Save profile</button>`;
  html += "</div>";
  dom.profileEditor.innerHTML = html;

  document.getElementById("profile-save").addEventListener("click", () => {
    state.profile.ics = getCheckedValues("profile-ics");
    state.profile.mechs = getCheckedValues("profile-mechs");
    state.profile.topics = getCheckedValues("profile-topics");
    state.profile.career = document.getElementById("profile-career").value;
    saveProfile();
    dom.profileEditor.style.display = "none";
    renderProfileChips();
    render();
  });
}

function buildProfileMultiSelect(label, options, selected, id) {
  let html = `<div style="margin-top:0.4rem;"><strong>${label}:</strong><div id="${id}" style="max-height:100px;overflow-y:auto;margin-top:0.2rem;">`;
  for (const opt of options) {
    const checked = selected.includes(opt) ? "checked" : "";
    const short = opt.length > 30 ? opt.slice(0, 28) + "…" : opt;
    html += `<label style="display:block;cursor:pointer;"><input type="checkbox" value="${opt}" ${checked}> ${short}</label>`;
  }
  html += "</div></div>";
  return html;
}

function getCheckedValues(containerId) {
  const checks = document.getElementById(containerId).querySelectorAll("input:checked");
  return Array.from(checks).map((cb) => cb.value);
}
```

- [ ] **Step 6: Add the main `render()` function**

Append to `app.js`:

```js
// --- Render ---
function filterNotices() {
  const today = new Date();
  let cutoff = null;
  if (state.filters.dateRange === "7d") {
    cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - 7);
  } else if (state.filters.dateRange === "30d") {
    cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - 30);
  } else if (state.filters.dateRange === "90d") {
    cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - 90);
  }

  return state.notices.filter((n) => {
    if (cutoff && n.release_date && new Date(n.release_date) < cutoff) return false;
    if (state.filters.ics.length > 0) {
      if (!(n.issuing_orgs || []).some((ic) => state.filters.ics.includes(ic))) return false;
    }
    if (state.filters.mechanisms.length > 0) {
      if (!(n.mechanisms || []).some((m) => state.filters.mechanisms.includes(m))) return false;
    }
    if (state.filters.topics.length > 0) {
      if (!(n.topics || []).some((t) => state.filters.topics.includes(t))) return false;
    }
    if (!matchesSearch(n, state.search)) return false;
    if (state.savedOnly && !state.saved.includes(n.notice_id)) return false;
    return true;
  });
}

function matchScore(n) {
  const p = state.profile;
  let s = 0;
  for (const ic of (n.issuing_orgs || [])) if (p.ics.includes(ic)) s += 1;
  for (const m of (n.mechanisms || [])) if (p.mechs.includes(m)) s += 1;
  for (const t of (n.topics || [])) if (p.topics.includes(t)) s += 1;
  if (p.career && p.career !== "any" && (n.career_stages || []).includes(p.career)) s += 0.5;
  return s;
}

function profileEmpty() {
  const p = state.profile;
  return !p.ics.length && !p.mechs.length && !p.topics.length && (!p.career || p.career === "any");
}

function render() {
  const filtered = filterNotices();
  const scored = filtered.map((n) => ({ ...n, _score: matchScore(n) }));
  if (!profileEmpty()) {
    scored.sort((a, b) => b._score - a._score || (b.release_date || "").localeCompare(a.release_date || ""));
  } else {
    scored.sort((a, b) => (b.release_date || "").localeCompare(a.release_date || ""));
  }

  // Update heading
  const headingLabels = { "7d": "Last 7 days", "30d": "Last 30 days", "90d": "Last 90 days", all: "All notices" };
  dom.feedHeading.textContent = headingLabels[state.filters.dateRange];
  const rankText = profileEmpty() ? "" : " · ranked for you";
  dom.feedMeta.textContent = `${scored.length} notice${scored.length !== 1 ? "s" : ""}${rankText}`;

  // Render feed
  if (scored.length === 0) {
    dom.feed.innerHTML = '<div class="empty-state">No notices match your filters.</div>';
  } else {
    dom.feed.innerHTML = scored.map(renderNoticeCard).join("");
    wireCardActions();
  }

  // Render charts
  renderCharts(filtered, {
    topics: dom.chartTopics,
    ics: dom.chartICs,
    volume: dom.chartVolume,
  });

  renderProfileChips();
}
```

- [ ] **Step 7: Add notice card HTML renderer**

Append to `app.js`:

```js
function chipClass(type) {
  const map = {
    nofo: "chip--nofo", rfa: "chip--rfa", change: "chip--change",
    rescission: "chip--rescission", pa: "chip--pa", par: "chip--par",
    reissue: "chip--reissue",
  };
  return map[type] || "";
}

function renderNoticeCard(n) {
  const chips = [];
  chips.push(`<span class="chip chip--id">${esc(n.notice_id)}</span>`);
  chips.push(`<span class="chip ${chipClass(n.notice_type)}">${esc((n.notice_type || "notice").replace(/_/g, " "))}</span>`);
  for (const ic of (n.issuing_orgs || []).slice(0, 2)) {
    chips.push(`<span class="chip">${esc(ic.replace(/^National (Institute|Center) of? /, ""))}</span>`);
  }
  if ((n.issuing_orgs || []).length > 2) {
    chips.push(`<span class="chip">+${n.issuing_orgs.length - 2}</span>`);
  }
  if (n._score > 0) {
    chips.push(`<span class="chip chip--match">match ${n._score}</span>`);
  }

  const tldr = n.purpose_tldr
    ? `<div class="notice__tldr">${esc(n.purpose_tldr)}</div>`
    : `<div class="notice__tldr notice__tldr--pending">TL;DR pending /refresh-tldrs</div>`;

  const meta = [n.release_date, (n.mechanisms || []).join(", "), (n.topics || []).join(", ")]
    .filter(Boolean).join(" · ");

  const isSaved = state.saved.includes(n.notice_id);
  const saveLabel = isSaved ? "♥ saved" : "♡ save";
  const saveClass = isSaved ? "notice__action notice__action--saved" : "notice__action";

  let detail = "";
  const hasDos = n.dos && n.dos.length > 0;
  const hasDonts = n.donts && n.donts.length > 0;
  let keyDates = [];
  try { keyDates = JSON.parse(n.key_dates_json || "[]"); } catch (e) { /* ignore */ }
  const hasKeyDates = keyDates.filter((kd) => kd.type !== "release").length > 0;

  if (hasDos || hasDonts || hasKeyDates) {
    detail += `<div class="notice__detail" id="detail-${esc(n.notice_id)}">`;
    if (hasDos) {
      detail += `<h4>Do</h4><ul>${n.dos.map((d) => `<li>${esc(d)}</li>`).join("")}</ul>`;
    }
    if (hasDonts) {
      detail += `<h4>Don't</h4><ul>${n.donts.map((d) => `<li>${esc(d)}</li>`).join("")}</ul>`;
    }
    if (hasKeyDates) {
      detail += `<h4>Key Dates</h4><ul>${keyDates.filter((kd) => kd.type !== "release").map((kd) => `<li><strong>${esc(kd.date)}</strong> — ${esc(kd.label)}</li>`).join("")}</ul>`;
    }
    detail += "</div>";
  }

  const expandBtn = (hasDos || hasDonts || hasKeyDates)
    ? `<button class="notice__action" data-expand="${esc(n.notice_id)}">⤢ expand</button>`
    : "";

  return `<div class="notice">
    <div class="notice__chips">${chips.join("")}</div>
    <div class="notice__title"><a href="${esc(n.url)}" target="_blank" rel="noreferrer">${esc(n.title)}</a></div>
    ${tldr}
    <div class="notice__footer">
      <span>${esc(meta)}</span>
      <div class="notice__actions">
        ${expandBtn}
        <button class="${saveClass}" data-save="${esc(n.notice_id)}">${saveLabel}</button>
      </div>
    </div>
    ${detail}
  </div>`;
}

function esc(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
```

- [ ] **Step 8: Add event wiring**

Append to `app.js`:

```js
// --- Events ---
function wireEvents() {
  // Search
  dom.search.addEventListener(
    "input",
    debounce(() => {
      state.search = dom.search.value;
      render();
    }, 200)
  );

  // Theme
  dom.themeToggle.addEventListener("click", toggleTheme);

  // Hamburger
  dom.hamburger.addEventListener("click", () => {
    dom.sidebar.classList.toggle("open");
  });

  // Filter dropdown toggles
  for (const trigger of $$(".filter-group__trigger")) {
    trigger.addEventListener("click", () => {
      const list = trigger.nextElementSibling;
      list.classList.toggle("open");
    });
  }

  // Profile toggle
  dom.profileToggle.addEventListener("click", () => {
    const editor = dom.profileEditor;
    if (editor.style.display === "none") {
      editor.style.display = "block";
      renderProfileEditor();
    } else {
      editor.style.display = "none";
    }
  });

  // Saved only toggle
  dom.savedOnly.addEventListener("change", () => {
    state.savedOnly = dom.savedOnly.checked;
    render();
  });

  // Clear filters
  dom.clearFilters.addEventListener("click", () => {
    state.filters = { ics: [], mechanisms: [], topics: [], dateRange: "30d" };
    state.search = "";
    state.savedOnly = false;
    dom.search.value = "";
    dom.savedOnly.checked = false;
    buildFilterOptions();
    updateTriggerLabel("ics");
    updateTriggerLabel("mechanisms");
    updateTriggerLabel("topics");
    updateTriggerLabel("dateRange");
    render();
  });
}

function wireCardActions() {
  // Expand buttons
  for (const btn of $$("[data-expand]")) {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-expand");
      const detail = document.getElementById("detail-" + id);
      if (detail) {
        detail.classList.toggle("open");
        btn.textContent = detail.classList.contains("open") ? "⤡ collapse" : "⤢ expand";
      }
    });
  }

  // Save buttons
  for (const btn of $$("[data-save]")) {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-save");
      if (state.saved.includes(id)) {
        state.saved = state.saved.filter((s) => s !== id);
        btn.textContent = "♡ save";
        btn.classList.remove("notice__action--saved");
      } else {
        state.saved.push(id);
        btn.textContent = "♥ saved";
        btn.classList.add("notice__action--saved");
      }
      saveSaved();
    });
  }
}

// --- Boot ---
init();
```

- [ ] **Step 9: Test the full dashboard locally**

```bash
cp data/notices.json site/notices.json
open site/index.html
```

Verify:
1. Notices load and render as cards with chips and TL;DRs
2. Sidebar filters populate with ICs, mechanisms, topics from the data
3. Clicking a filter checkbox filters the feed and charts
4. Search bar filters notices by text
5. Dark mode toggle switches palette
6. Expand/save buttons on cards work
7. Profile editor in sidebar saves to localStorage
8. Charts render in the three containers

- [ ] **Step 10: Commit**

```bash
git add site/app.js
git commit -m "feat: add dashboard state management and rendering"
```

---

### Task 5: Update CI workflow and clean up Quarto files

**Files:**
- Modify: `.github/workflows/pages-deploy.yml`
- Modify: `site/_quarto.yml`
- Delete: `site/index.qmd`
- Delete: `site/theme.scss`
- Delete: `site/profile.qmd`

- [ ] **Step 1: Update `pages-deploy.yml` to deploy without Quarto rendering the dashboard**

The other Quarto pages (browse, calendar, about) still need Quarto. The workflow keeps the Quarto render but the new `index.html` will override the generated one since it's already a static file in `site/`.

Replace the full file content:

```yaml
name: pages-deploy

on:
  push:
    branches: [main]
    paths:
      - "site/**"
      - "data/notices.json"
      - ".github/workflows/pages-deploy.yml"
  workflow_dispatch:
  workflow_run:
    workflows: ["weekly-refresh"]
    types: [completed]

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - name: Stage data file
        run: |
          if [ -f data/notices.json ]; then
            cp data/notices.json site/notices.json
          else
            echo "[]" > site/notices.json
          fi
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site/
      - id: deployment
        uses: actions/deploy-pages@v4
```

This removes the Quarto setup and render steps entirely. The `site/` directory is deployed as-is with the static HTML files plus `notices.json`.

- [ ] **Step 2: Update `site/_quarto.yml` — remove dashboard-specific config**

Since we're deploying `site/` directly (not rendering Quarto), the `_quarto.yml` is no longer used by CI. However, keep it for local Quarto rendering of browse/calendar/about if desired. Remove the index and profile references from the navbar:

```yaml
project:
  type: website
  output-dir: ../docs

website:
  title: "Grant Radar"
  description: "A digestible weekly view of NIH funding notices."
  site-url: https://muntasirmasum.github.io/grant-radar/
  repo-url: https://github.com/muntasirmasum/grant-radar
  repo-actions: [issue]
  navbar:
    background: primary
    left:
      - href: browse.qmd
        text: Browse
      - href: calendar.qmd
        text: Calendar
    right:
      - href: about.qmd
        text: About

format:
  html:
    theme: cosmo
    toc: true
    grid:
      body-width: 1200px
```

- [ ] **Step 3: Delete replaced Quarto files**

```bash
git rm site/index.qmd
git rm site/profile.qmd
git rm site/theme.scss
```

- [ ] **Step 4: Verify the deploy workflow is valid YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pages-deploy.yml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 5: Test local preview still works**

```bash
cp data/notices.json site/notices.json
open site/index.html
```

Verify the full dashboard renders correctly from the `site/` directory.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/pages-deploy.yml site/_quarto.yml
git commit -m "chore: update CI to deploy site/ directly, remove Quarto dashboard files"
```

---

### Task 6: Update `about.qmd` and add navigation links

**Files:**
- Modify: `site/about.qmd`
- Modify: `site/index.html`

Since browse, calendar, and about pages are no longer rendered by Quarto in CI (we deploy `site/` as-is), we need to decide: either keep them as `.qmd` files for local rendering, or convert them to static HTML too. For now, the simplest path is to convert `about.qmd` to `about.html` (it's mostly prose) and add nav links to the dashboard.

- [ ] **Step 1: Add navigation links to `index.html` navbar**

In `site/index.html`, update the navbar left section to include links:

Find:
```html
<a class="navbar__brand" href="#">Grant Radar</a>
```

Replace with:
```html
<a class="navbar__brand" href="#">Grant Radar</a>
<div class="navbar__links">
  <a href="browse.html" class="navbar__link">Browse</a>
  <a href="about.html" class="navbar__link">About</a>
</div>
```

- [ ] **Step 2: Add navbar link styles to `style.css`**

Add after the `.navbar__hamburger` block:

```css
.navbar__links {
  display: flex;
  gap: 1rem;
  margin-left: 1.5rem;
}
.navbar__link {
  color: var(--navbar-text);
  text-decoration: none;
  font-size: 0.82rem;
  opacity: 0.75;
}
.navbar__link:hover { opacity: 1; }

@media (max-width: 767px) {
  .navbar__links { display: none; }
}
```

- [ ] **Step 3: Convert `about.qmd` to `about.html`**

Create `site/about.html` as a simple static page using the same Paper Warm palette:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>About — Grant Radar</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav class="navbar">
    <div style="display:flex;align-items:center;gap:0.75rem;">
      <a class="navbar__brand" href="index.html">Grant Radar</a>
      <div class="navbar__links">
        <a href="browse.html" class="navbar__link">Browse</a>
        <a href="about.html" class="navbar__link" style="opacity:1;">About</a>
      </div>
    </div>
    <div class="navbar__right">
      <button class="navbar__toggle" id="theme-toggle" aria-label="Toggle dark mode">☀️</button>
    </div>
  </nav>
  <div style="max-width:720px;margin:2rem auto;padding:0 1.5rem;">
    <h1 style="font-size:1.4rem;color:var(--text);margin-bottom:1rem;">About Grant Radar</h1>
    <div style="font-size:0.9rem;line-height:1.7;color:var(--text-secondary);">
      <h2 style="font-size:1.1rem;color:var(--text);margin:1.5rem 0 0.5rem;">What Grant Radar does</h2>
      <p>Grant Radar fetches the NIH Guide for Grants and Contracts weekly index every Sunday evening, downloads each notice, and runs a hybrid extractor that combines deterministic rule-based parsing of the consistent header fields (notice ID, release date, issuing IC, related announcements, key dates table) with a large language model (Anthropic Claude) that summarizes the free-text sections (purpose, eligibility, do's and don'ts, budget). Each notice is validated against a JSON schema and stored as a versioned record in the project's GitHub repository.</p>
      <p style="margin-top:0.8rem;">The dashboard is a static website hosted free on GitHub Pages. There is no server, no database, and no user account system. Personal filter profiles live entirely in your browser's localStorage.</p>
      <h2 style="font-size:1.1rem;color:var(--text);margin:1.5rem 0 0.5rem;">Sources</h2>
      <p>The MVP covers the NIH Guide for Grants and Contracts. NSF, AHRQ, CDC, and DoD/CDMRP are planned as pluggable source modules.</p>
      <h2 style="font-size:1.1rem;color:var(--text);margin:1.5rem 0 0.5rem;">Limitations</h2>
      <ul style="padding-left:1.5rem;margin-top:0.3rem;">
        <li>LLM extractions can be wrong. Always confirm against the linked original notice before drafting a proposal.</li>
        <li>Topic tagging is approximate.</li>
        <li>Backfill begins January 2025.</li>
        <li>Mobile rendering of complex notices may lose information; use the link to the original NIH page for the canonical text.</li>
      </ul>
    </div>
  </div>
  <script>
    const toggle = document.getElementById("theme-toggle");
    if (localStorage.getItem("grant-radar.theme") === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
      toggle.textContent = "🌙";
    }
    toggle.addEventListener("click", () => {
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      if (isDark) {
        document.documentElement.removeAttribute("data-theme");
        localStorage.setItem("grant-radar.theme", "light");
        toggle.textContent = "☀️";
      } else {
        document.documentElement.setAttribute("data-theme", "dark");
        localStorage.setItem("grant-radar.theme", "dark");
        toggle.textContent = "🌙";
      }
    });
  </script>
</body>
</html>
```

- [ ] **Step 4: Remove `site/about.qmd`**

```bash
git rm site/about.qmd
```

Note: `browse.qmd` and `calendar.qmd` are out of scope for this rewrite. They can be converted to HTML in a follow-up. For now, the navbar links to `browse.html` and it will 404 until converted. This is acceptable for the initial rewrite.

- [ ] **Step 5: Commit**

```bash
git add site/index.html site/style.css site/about.html
git commit -m "feat: add navbar links and convert about page to static HTML"
```

---

### Task 7: End-to-end verification

**Files:** none (testing only)

- [ ] **Step 1: Copy data and open in browser**

```bash
cp data/notices.json site/notices.json
open site/index.html
```

- [ ] **Step 2: Verify core functionality**

Walk through this checklist in the browser:

1. **Page loads** — warm parchment background, dark brown navbar, sidebar on left
2. **Notices render** — cards with chips, titles, TL;DRs (enriched and pending)
3. **Sidebar filters** — click IC dropdown, check an IC, feed and charts update
4. **Search** — type a notice ID or keyword, feed filters in real time
5. **Profile** — click "My Profile", configure ICs, save, notices re-rank with match badges
6. **Dark mode** — click toggle, palette inverts to warm charcoal, reload page and theme persists
7. **Expand** — click expand on an enriched notice, dos/donts appear
8. **Save** — click save on a notice, heart turns red, toggle "Saved notices only" in sidebar
9. **Charts** — three charts render below feed, update when filters change
10. **Mobile** — resize browser to < 768px, sidebar collapses, hamburger appears and toggles it
11. **About page** — click "About" in navbar, page loads with same palette

- [ ] **Step 3: Verify no console errors**

Open browser dev tools console. Expected: no errors (warnings about font loading on file:// protocol are acceptable).

- [ ] **Step 4: Commit any fixes found during testing**

```bash
git add -A
git commit -m "fix: address issues found during end-to-end testing"
```

(Skip this step if no fixes are needed.)

- [ ] **Step 5: Clean up Quarto cache**

```bash
rm -rf site/.quarto
```

```bash
git add -A
git commit -m "chore: remove Quarto cache directory"
```
