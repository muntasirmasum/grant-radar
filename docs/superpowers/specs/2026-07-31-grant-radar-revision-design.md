# Grant Radar Revision: Editorial Digest + API Pipeline
**Date:** 2026-07-31 **Status:** Approved (brainstormed with Muntasir; layout and visual direction selected in visual companion session) **Supersedes:** the 2026-05-25 HTML dashboard design where they conflict. **Companion mockup:** `2026-07-31-grant-radar-revision-mockup.html` (same directory; open in a browser, toggle ☾ for dark mode)
## 1. Background and problems
The May 2026 dashboard shipped, then decayed. Diagnosis from the 2026-07-31 session:

1. **Empty shells.** 119 of 120 notices display no TL;DR. The LLM enrichment step (`/refresh-tldrs`) is manual and was rarely run.
  
2. **Enrichment gets destroyed.** The weekly rule-only refresh overwrote 5 of the 6 hand-enriched notices. Manual work does not survive the cron.
  
3. **Dead pipeline.** `weekly-refresh` has failed every run since 2026-06-29 (`there is no package called 'devtools'` in CI). One run hung for ~3 hours. No data since 2026-06-22.
  
4. **Wrong objects.** Only `NOT-*` administrative notices are ingested. Actual funding opportunities (`RFA-*`, `PA-*`, `PAR-*`) with application deadlines are absent, so the feed is mostly meta-chatter.
  
5. **Generic look.** The Paper Warm palette has no connection to muntasirmasum.com.
  
## 2. Goals and non-goals
**Goals**

- The site is genuinely useful with zero LLM enrichment, and strictly better with it.
  
- Surface real funding opportunities with deadlines, not just administrative notices.
  
- Look and feel: a sibling product of muntasirmasum.com (its design tokens, typography, and card language).
  
- The weekly pipeline is boring, fast, and stays alive unattended.
  
- LLM enrichment stays manual, free (Claude Code subscription), and is never clobbered.
  

**Non-goals (recorded for later, out of scope now)**

- Non-NIH sources (NSF, AHRQ, CDC, DoD/CDMRP).
  
- Automated LLM enrichment via API key or scheduled claude-code action.
  
- Email digest delivery, accounts, server-side anything.
  
- Historical backfill before February 2026 for the feed (the calendar naturally includes older still-open FOAs).
  
## 3. Decisions made during brainstorming
| Question | Decision |
| --- | --- |
| Primary pain point | Look and feel first, but all four problems above are real |
| Audience | Muntasir first, public-facing polish (linkable from muntasirmasum.com) |
| Enrichment | Stays manual via `/refresh-tldrs`; zero cost; refresh must never overwrite it |
| Page backbone | Editorial digest (option A), absorbing the "closing soon" strip from option C |
| Pipeline language | Python rewrite; R package retired |
## 4. Site design
Static HTML/CSS/JS in `site/`, deployed to GitHub Pages exactly as today. No build step. No CDN dependencies except Observable Plot, loaded only on the Trends page.
### 4.1 Pages
- `index.html` **(This week).** Editorial digest, single centered column (max width ~790px).
  
  - Header: eyebrow `NIH GUIDE · WEEK OF <date>`, serif H1 "This week in NIH funding", lead line with counts and refresh timestamp.
    
  - **Closing soon strip:** purple-tinted panel listing the 5 soonest future due dates among "For you" items, each with a countdown badge (solid purple when ≤30 days out, outlined otherwise). Links to Calendar.
    
  - **Filter chips** (replace the old sidebar): `All · For you · Opportunities · NOSIs · Career K/F · Policy · ♡ Saved`, with live counts. Single-select; combines with navbar search.
    
  - **Feed:** items grouped under week dividers ("Week of July 27"), newest first. First 4 weeks render immediately; older weeks append via a scroll sentinel from the already-loaded JSON.
    
- `calendar.html`**.** Upcoming due dates grouped by month. Each row: countdown badge, serif title, IC, mechanism chips, due-date type (application receipt vs expiration). Includes every still-open FOA regardless of release date. Respects the profile filter chip (All / For you).
  
- `trends.html`**.** Three charts (Observable Plot): weekly item volume (last 12 weeks), most active ICs (last 90 days), top activity codes among active FOAs. Computed entirely from structured fields.
  
- `about.html`**.** What the radar is, data sources (NIH Guide API, Grants.gov), refresh cadence, enrichment provenance note ("TL;DR blocks are LLM-assisted, reviewed by me"), link to repo and RSS.
  
### 4.2 Card anatomy and the three content states
Cards degrade gracefully. No card ever shows "TL;DR pending" or any other apology.

1. **Enriched** (has `purpose_tldr`): eyebrow (doctype · orgs · id), serif title, purple-edged **TL;DR** block, "For you" reason line when applicable, pill row (due chip, activity codes, topics), actions (save ♡, Details ▾, NIH ↗). Expanded details: do/don't lists and key dates.
  
2. **API synopsis only** (FOA without enrichment): same, but a quieter grey **Synopsis** block (Grants.gov `synopsisDesc`, truncated ~400 chars at build time) instead of TL;DR; award ceiling chip when known.
  

3. **Bare** (notice without synopsis): compact card, eyebrow + title only.
  

Mechanism pills display `activity_codes` (pipeline-owned) when present, falling back to the legacy LLM `mechanisms` field for old items the APIs do not cover.

**Color semantics:** purple left edge = actionable funding (RFA, PA, PAR, NOSI). Gold left edge = policy/admin (forms, policy changes, rescissions, webinars). Gold cards never show deadline chips. Urgency: due ≤30 days = solid purple chip; otherwise gold-tint chip.
### 4.3 Visual system
Design tokens copied from muntasirmasum.com `site.css` (`:root` and `.quarto-dark` blocks), same names where practical:

- **Light:** bg `#f5f6f8`, surface `#ffffff`, ink `#1f2d3a`, body `#3b4651`, muted `#5a6571`/`#74808b`, border `#e7eaee`, hair `#eef0f3`, accent `#46166b`, accent-tint `#f1ecf7`, accent-underline `#dccfe8`, gold `#c2a23a`, gold-tint `#fbf3e0`, gold-text `#a07d12`.
  
- **Dark:** bg `#141118`, surface `#1f1b27`, ink `#f4f2f8`, body `#cdc9d6`, border `#332e3e`, accent `#7a4fb0`, accent-text `#cbb1e8`, accent-tint `#2a2138`, gold-text `#d8b84e`, gold-tint `#332b16`.
  
- **Type:** Newsreader (600, negative letter-spacing) for brand, H1, card titles, week dividers; IBM Plex Sans for everything else. Google Fonts, same loading approach as the academic site.
  
- **Card language:** 12px radius, 1px border, 3px left accent, hover lift (translateY(-2px) + soft shadow), eyebrow labels, 999px pills, exactly as the academic site's publication cards.
  
- **Navbar:** sticky, blurred translucent bg, brand "Grant Radar" in Newsreader with a small purple radar-ping dot, links (This week · Calendar · Trends · About), search input, theme toggle, `muntasirmasum.com ↗` link.
  
- **Dark mode:** defaults to `prefers-color-scheme`, toggle persists to localStorage. Focus-visible outlines and `prefers-reduced-motion` handling per the academic site's conventions.
  
- **Footer:** hairline top border; left "Grant Radar · by Muntasir Masum", right "Data: NIH Guide & Grants.gov · refreshed weekly · RSS · GitHub".
  
### 4.4 Personalization ("For you")
Client-side only, localStorage, no accounts.

- **Profile:** sets of ICs, activity codes, and keywords. Editable inline (chip editor behind an "edit" affordance near the filter chips).
  
- **Default seed** (Muntasir's profile, shipped as the initial value): ICs `NIA, NIAAA, NICHD, NIMHD`; activity codes `K01, K99, R03, R21, R01`; keywords `aging, alcohol, mortality, demography, life course, disparities, epidemiology`.
  
- **Match rule (deterministic, explainable):** each matching IC, activity code, and keyword (case-insensitive, matched against title + synopsis + topics) contributes one named reason. An item is "For you" when it has ≥2 reasons. Cards show the reasons in words ("For you · matches NIA · alcohol · R21"). No numeric scores anywhere.
  
- **Closing soon strip** = "For you" items with a future due date, soonest 5.
  
- **Saved items:** heart toggle per card, localStorage set, surfaced via the ♡ Saved chip.
  
## 5. Data pipeline
### 5.1 Sources (both verified working, 2026-07-31, no keys required)
- **NIH Guide API** `https://search.grants.nih.gov/guide/api/data` (Elasticsearch query API behind the official Guide search). Provides for every Guide item: `docnum`, `doctype` (RFA / PA / notices…), `title`, `organization.parent` + `organization.primary` (ICs), `reldate`, `expdate`, `opendate`, `appreceiptdate`, `lard` (last application receipt date), activity codes (`ac`), clinical-trials flag, filename.
  
- **Grants.gov API** `POST https://api.grants.gov/v1/api/search2` (lookup by `oppNum`) and `POST https://api.grants.gov/v1/api/fetchOpportunity` (by numeric id). Provides `synopsisDesc` (purpose paragraph), `awardCeiling`/`awardFloor`, `responseDate`, applicant types, close date.
  
### 5.2 Fetch modes
- **Feed mode (weekly):** Guide items with `reldate` in the last 14 days (overlap tolerates a missed week). All doctypes.
  
- **Calendar mode (weekly):** all Guide items with `type=active` (still-open FOAs), paginated. Ensures the calendar knows about older still-open opportunities.
  
- **Grants.gov detail:** fetched only for FOA items that are new or whose NIH-side record changed, then cached in the item JSON. Bounds weekly Grants.gov calls to roughly the new/changed set, not the ~2k active backlog.
  
- **Raw HTML cache:** fetched only for feed-mode items (that week's new items), stored under `data/raw/nih/YYYY/` as today, for `/refresh-tldrs` to read. Older items: `/refresh-tldrs` fetches live when needed.
  
### 5.3 Data model and field ownership
Per-item JSON files stay in `data/notices/<release-year>/<docnum>.json`. The existing 121 files remain and are augmented in place. Schema additions: `doctype`, `activity_codes`, `expiration_date`, `open_date`, `next_due_date`, `due_dates[]`, `synopsis`, `synopsis_truncated`, `award_ceiling`, `award_floor`, `grants_gov_id`, `parent_ic`, `updated_at`.

**Field ownership (the anti-clobber contract):**

- **Pipeline-owned** (refresh may create/update, only when source data changed): identifiers, title, dates, orgs, activity codes, synopsis, award figures, raw hash.
  
- **LLM-owned** (refresh must never write, not even to null): `purpose_tldr`, `eligibility_tldr`, `dos`, `donts`, `career_stages`, `strategic_priorities`, `budget`, `mechanisms`, `llm_model`, `enriched_at`.
  
- **Hybrid:** `topics`. The pipeline seeds rule-based tags (taxonomy keyword match) only when the field is absent; once any writer has set it, the pipeline leaves it alone.
  
- Merge is per-field on top of the existing file; unknown/extra fields in existing files are preserved verbatim.
  
### 5.4 Implementation shape
- `pipeline/refresh.py`, Python ≥3.11, sole dependency `requests`. Roughly: fetch → normalize → merge → validate → write items → emit site artifacts. Target ~250–300 lines plus tests.
  
- **Emitted artifacts:** `site/notices.json` (all feed items since Feb 2026 + all active FOAs, synopsis truncated to 400 chars; single file, acceptable while gzipped size stays under ~1 MB on Pages) and `site/feed.xml` (RSS 2.0, latest 50 feed items, TL;DR or synopsis excerpt as description).
  
- **Validation:** hand-rolled checks per item (required keys, ISO dates, known doctype); a failing item aborts the run.
  
- `data/taxonomy.yml` keyword→topic mapping is applied by the pipeline (rule-based topic tags from title+synopsis) so topic chips exist without LLM. LLM enrichment may refine `topics` later and then owns the field (pipeline writes rule-based topics only when the field is absent).
  
### 5.5 CI
- `weekly-refresh.yml`: cron Sundays 23:00 UTC + `workflow_dispatch`. Steps: checkout → setup-python → `pip install requests` → `python pipeline/refresh.py` → commit data + site artifacts → done. Expected wall time ≈1 minute.
  
- `pages-deploy.yml`: unchanged (deploys `site/` on push to main).
  
- `ci.yml`: replace R test job with `pytest` over the pipeline tests.
  
## 6. Enrichment flow (`/refresh-tldrs`, revised)
- Queue = items missing `purpose_tldr`, ordered: (1) "For you" matches per the default profile, (2) FOAs by nearest `next_due_date`, (3) everything else, newest first.
  
- Input per item: cached raw HTML if present, else fetch live; for FOAs also the full Grants.gov synopsis.
  
- Writes LLM-owned fields only, plus `enriched_at` and `llm_model`. Never edits pipeline-owned fields.
  
- After enrichment, run the pipeline's emit step (or the pipeline re-run) to rebuild `site/notices.json`; commit both.
  
- The command file gets updated for the new schema and queue ordering as part of this work.
  
## 7. Failure behavior
- Any API failure or validation failure aborts the whole refresh before any file is written; the workflow fails loudly (GitHub failure email) and the site keeps last week's data. No partial commits.
  
- The homepage lead line shows the refresh timestamp from `notices.json` metadata, so staleness is visible on the site itself.
  
- If `notices.json` fails to load client-side, the page renders a styled error card (not a blank page).
  
## 8. Testing
`pipeline/tests/` with pytest, fixture JSON responses, no live API calls:

- Anti-clobber: refresh over an enriched item preserves every LLM-owned field.
  
- Change detection: changed source data updates pipeline-owned fields; identical data is a byte-stable no-op.
  
- Normalization: date parsing (including `lard`/receipt dates), IC extraction, activity codes, doctype mapping, topic tagging from taxonomy.
  
- Emission: notices.json shape, synopsis truncation, RSS validity, deterministic ordering.
  
- One end-to-end test: fixtures in → expected site artifacts out.
  
## 9. Cleanup and migration
In the implementation branch, in this order:

1. Restore the locally deleted `R/` files from git, then properly `git rm` the R package: `R/`, `DESCRIPTION`, `NAMESPACE`, `tests/` (R), `inst/`, plus Quarto leftovers `site/browse.qmd`, `site/calendar.qmd`, `site/ojs/`, `site/notice/`, `site/_quarto.yml`, `site/.quarto/`, and `data/notices.parquet`. Also delete the stale Quarto-built site sitting untracked in `docs/` root (`docs/*.html`, `docs/notices.json`, `docs/site_libs/`, `docs/sitemap.xml`, `docs/robots.txt`); `docs/superpowers/` stays (now un-ignored). History preserves everything.
  
2. Rewrite `NEXT.md` to reflect this revision (supersedes the uncommitted May working-tree edit).
  
3. New `pipeline/` + rewritten `site/` land together; README rewritten (architecture diagram, local dev = `python pipeline/refresh.py && python -m http.server -d site`).
  
4. Existing per-item JSONs are kept untouched until the first new refresh augments them.
  
## 10. Later (explicitly deferred)
- NSF / AHRQ / CDC / CDMRP sources behind the same item schema.
  
- Optional automated enrichment (API key or scheduled claude-code action) if manual cadence proves annoying.
  
- Email digest; OG images for social sharing; per-item permalink pages.
