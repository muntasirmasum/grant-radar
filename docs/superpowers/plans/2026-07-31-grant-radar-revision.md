# Grant Radar Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dead R scraping pipeline with a small Python API pipeline (NIH Guide + Grants.gov), and rebuild the site as an editorial digest using the muntasirmasum.com design system.

**Architecture:** A weekly GitHub Actions cron runs `pipeline/refresh.py`, which pulls structured JSON from two public APIs, merges into per-item JSON files under an anti-clobber contract (LLM-enriched fields are never overwritten), and emits `data/notices.json` + `data/feed.xml`. The static site in `site/` (plain HTML/CSS/ES modules, no build step) renders a digest homepage, calendar, trends, and about page from the staged `notices.json`. LLM enrichment stays manual via the `/refresh-tldrs` command.

**Tech Stack:** Python ≥3.11 + `requests` (pipeline), pytest (pipeline tests), Node ≥20 built-in `node --test` (frontend logic tests), vanilla HTML/CSS/JS ES modules, Observable Plot via CDN (trends page only), GitHub Actions + Pages.

**Spec:** `docs/superpowers/specs/2026-07-31-grant-radar-revision-design.md`. Read it before starting. The interactive design mockup is `docs/superpowers/specs/2026-07-31-grant-radar-revision-mockup.html` (open in a browser; ☾ toggles dark mode).

## Global Constraints

- Pipeline: Python ≥3.11, sole runtime dependency `requests`. No pyyaml (taxonomy is converted to JSON in Task 1), no pandas, no arrow.
- Site: no build step, no framework, no CDN dependency except `@observablehq/plot` on `trends.html` only.
- Anti-clobber contract (spec §5.3): refresh never writes `purpose_tldr`, `eligibility_tldr`, `dos`, `donts`, `career_stages`, `strategic_priorities`, `budget`, `mechanisms`, `llm_model`, `enriched_at`. `topics` is hybrid: pipeline seeds it only when absent. Unknown fields in existing items are preserved verbatim.
- Design tokens are copied exactly from the spec §4.3 (light and dark). Fonts: Newsreader (headings) + IBM Plex Sans (body) via Google Fonts.
- localStorage keys: `grant-radar.theme` and `grant-radar.saved.v1` keep their current names (existing values survive); the profile uses the new key `grant-radar.profile.v2`.
- Feed history floor: items with `release_date >= 2026-02-06`; the site payload also includes older still-open opportunities (for the calendar).
- All new/changed dates in item JSON are ISO `YYYY-MM-DD` strings; timestamps are ISO 8601 UTC with `Z`.
- Item JSON files are written as `json.dumps(item, indent=2, sort_keys=True, ensure_ascii=False) + "\n"`; an unchanged item must be a byte-identical no-op.
- Commit after every task (messages given per task). Never commit `site/notices.json` or `site/feed.xml` (gitignored; staged at deploy).
- Verified API facts (2026-07-31): NIH Guide API is `GET https://search.grants.nih.gov/guide/api/data`, params `searchText`, `from`, `size`, `sort=reldate:desc` (that exact syntax; `order=desc` is silently ignored), `type=active` filters to open FOAs; ES-style response `data.hits.hits[]._source`. Grants.gov is `POST https://api.grants.gov/v1/api/search2` (JSON body, `oppNum` lookup) and `POST https://api.grants.gov/v1/api/fetchOpportunity` (JSON body `{"opportunityId": <int>}`), no keys.

---

### Task 1: Retire the R stack, stale built site, and YAML taxonomy

**Files:**
- Delete (git rm): `R/`, `DESCRIPTION`, `NAMESPACE`, `tests/`, `inst/`, `site/browse.qmd`, `site/calendar.qmd`, `site/ojs/`, `site/notice/`, `site/_quarto.yml`, `data/notices.parquet`, `data/taxonomy.yml`
- Delete (untracked): `docs/index.html`, `docs/about.html`, `docs/browse.html`, `docs/calendar.html`, `docs/profile.html`, `docs/notices.json`, `docs/sitemap.xml`, `docs/robots.txt`, `docs/site_libs/`, `site/.quarto/`
- Create: `data/taxonomy.json`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: `data/taxonomy.json` with shape `{"institutes": {"NIA": "National Institute on Aging", ...}, "topics": {"<topic_name>": ["keyword", ...], ...}}`. Later tasks (2, 7, 10) read exactly this shape.

- [ ] **Step 1: Restore the accidentally deleted working-tree files, then remove the R stack properly**

The working tree currently shows `R/*` deleted but uncommitted (from a folder move). Restore first so the deletion is a clean, intentional commit:

```bash
cd ~/projects/grant-radar
git checkout -- R/ 2>/dev/null || true
git rm -r --quiet R DESCRIPTION NAMESPACE tests inst
git rm --quiet site/browse.qmd site/calendar.qmd site/_quarto.yml
git rm -r --quiet site/ojs site/notice
git rm --quiet data/notices.parquet
rm -rf site/.quarto
rm -rf docs/index.html docs/about.html docs/browse.html docs/calendar.html docs/profile.html docs/notices.json docs/sitemap.xml docs/robots.txt docs/site_libs
```

- [ ] **Step 2: Convert taxonomy.yml to taxonomy.json**

One-time conversion (pyyaml used here only, never by the pipeline):

```bash
pip install --quiet pyyaml
python3 - <<'EOF'
import yaml, json
y = yaml.safe_load(open("data/taxonomy.yml"))
out = {
    "institutes": {e["code"]: e["name"] for e in y.get("institutes_and_centers", [])},
    "topics": {},
}
for t in y.get("topics", []):
    # taxonomy.yml topics entries look like {name: "aging", keywords: [...]}
    if isinstance(t, dict):
        out["topics"][t.get("name")] = list(t.get("keywords", []) or [])
    else:
        out["topics"][str(t)] = []
json.dump(out, open("data/taxonomy.json", "w"), indent=2, ensure_ascii=False, sort_keys=True)
print("topics:", len(out["topics"]), "institutes:", len(out["institutes"]))
EOF
```

Open `data/taxonomy.json` and eyeball it: institutes must map code→full name; topics must map name→keyword list (empty lists are acceptable; keyword matching then falls back to the topic name itself). If `data/taxonomy.yml` nests topics differently, adjust the loop until the output shape matches the Interfaces block above. Then:

```bash
git rm --quiet data/taxonomy.yml
git add data/taxonomy.json
```

- [ ] **Step 3: Update .gitignore**

Remove the renv and Quarto blocks (dead tech) and add the feed staging entry. The file becomes exactly:

```gitignore
.DS_Store

# Stale Quarto-built site (pre-May 2026 Pages setup; scheduled for deletion)
docs/*
!docs/superpowers/

# Data copies that pages-deploy stages into site/
site/notices.json
site/feed.xml

# Secrets
.env
.superpowers/

# Python
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Verify the tree**

Run: `git status --short`
Expected: only deletions (`D`), the `.gitignore` modification, `data/taxonomy.json` addition, and the pre-existing `NEXT.md` modification (leave NEXT.md uncommitted; Task 16 rewrites it). Run `ls R 2>&1` → "No such file or directory".

- [ ] **Step 5: Commit**

```bash
git add -A
git reset -- NEXT.md
git commit -m "chore: retire R pipeline, Quarto leftovers, stale built site; taxonomy to JSON"
```

---

### Task 2: Pipeline skeleton + NIH Guide normalizer (TDD)

**Files:**
- Create: `pipeline/__init__.py` (empty), `pipeline/nih_guide.py`, `pipeline/requirements.txt`, `pipeline/tests/__init__.py` (empty), `pipeline/tests/test_nih_guide.py`, `pipeline/tests/fixtures/guide_active_rfa.json`, `pipeline/tests/fixtures/guide_notice.json`

**Interfaces:**
- Consumes: `data/taxonomy.json` (Task 1).
- Produces: `nih_guide.normalize(source: dict, institutes: dict[str, str]) -> dict` returning the pipeline-owned item fields; `nih_guide.GUIDE_URL_SUBDIR: dict[str, str]`. Task 5's merge treats this dict as "incoming". Field names (exact): `notice_id`, `source`, `doctype`, `title`, `release_date`, `open_date`, `expiration_date`, `due_dates`, `next_due_date`, `activity_codes`, `primary_ic`, `parent_ic`, `issuing_orgs`, `url`, `clinical_trials`.

- [ ] **Step 1: Write fixtures from real API shapes**

`pipeline/tests/fixtures/guide_active_rfa.json` (a trimmed real `_source`):

```json
{
  "rowid": "37347",
  "type": "active",
  "title": "Commercial Fishing Occupational Safety Training Project Grants (T03)",
  "docnum": "RFA-OH-22-006",
  "organization": { "parent": "CDC", "primary": "NIOSH" },
  "parentIC": "CDC",
  "primaryIC": "NIOSH",
  "reldate": "2022-06-28T13:51:38.000Z",
  "expdate": "2028-01-31T00:00:00.000Z",
  "doctype": "RFA",
  "ac": ["T03"],
  "filename": "RFA-OH-22-006.html",
  "clinicaltrials": "Not_Allowed",
  "opendate": "2022-07-29T00:00:00.000Z",
  "appreceiptdate": null,
  "lard": "2028-01-30T00:00:00.000Z"
}
```

`pipeline/tests/fixtures/guide_notice.json`:

```json
{
  "rowid": "99001",
  "type": "notices",
  "title": "Notice of Special Interest (NOSI): Alcohol Use Among Older Adults",
  "docnum": "NOT-AA-26-012",
  "organization": { "parent": "NIH", "primary": "NIAAA" },
  "reldate": "2026-07-28T09:00:00.000Z",
  "expdate": "2026-11-17T00:00:00.000Z",
  "doctype": "NOT",
  "ac": "",
  "filename": "NOT-AA-26-012.html",
  "clinicaltrials": null,
  "opendate": null,
  "appreceiptdate": null,
  "lard": null
}
```

- [ ] **Step 2: Write the failing tests**

`pipeline/tests/test_nih_guide.py`:

```python
import json
from pathlib import Path

from pipeline.nih_guide import normalize

FIX = Path(__file__).parent / "fixtures"
INSTITUTES = {"NIAAA": "National Institute on Alcohol Abuse and Alcoholism"}


def load(name):
    return json.loads((FIX / name).read_text())


def test_normalize_active_rfa():
    item = normalize(load("guide_active_rfa.json"), INSTITUTES)
    assert item["notice_id"] == "RFA-OH-22-006"
    assert item["source"] == "nih"
    assert item["doctype"] == "RFA"
    assert item["release_date"] == "2022-06-28"
    assert item["open_date"] == "2022-07-29"
    assert item["expiration_date"] == "2028-01-31"
    assert item["due_dates"] == [{"label": "Last application receipt", "date": "2028-01-30"}]
    assert item["next_due_date"] == "2028-01-30"
    assert item["activity_codes"] == ["T03"]
    assert item["primary_ic"] == "NIOSH"
    assert item["parent_ic"] == "CDC"
    assert item["issuing_orgs"] == ["NIOSH"]  # not in institutes map -> code passthrough
    assert item["url"] == "https://grants.nih.gov/grants/guide/rfa-files/RFA-OH-22-006.html"
    assert item["clinical_trials"] == "Not_Allowed"


def test_normalize_notice_maps_org_name_and_handles_empty_ac():
    item = normalize(load("guide_notice.json"), INSTITUTES)
    assert item["notice_id"] == "NOT-AA-26-012"
    assert item["doctype"] == "NOT"
    assert item["activity_codes"] == []
    assert item["due_dates"] == []
    assert item["next_due_date"] is None
    assert item["expiration_date"] == "2026-11-17"
    assert item["issuing_orgs"] == ["National Institute on Alcohol Abuse and Alcoholism"]
    assert item["url"] == "https://grants.nih.gov/grants/guide/notice-files/NOT-AA-26-012.html"


def test_normalize_par_uses_pa_files_subdir():
    src = load("guide_active_rfa.json")
    src["docnum"] = "PAR-26-118"
    src["doctype"] = "PAR"
    src["filename"] = "PAR-26-118.html"
    item = normalize(src, INSTITUTES)
    assert item["url"] == "https://grants.nih.gov/grants/guide/pa-files/PAR-26-118.html"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd ~/projects/grant-radar && python3 -m pytest pipeline/tests/test_nih_guide.py -v
```
Expected: FAIL / collection error, `ModuleNotFoundError: No module named 'pipeline.nih_guide'` (install pytest first if missing: `pip install pytest requests`).

- [ ] **Step 4: Implement `pipeline/nih_guide.py` (normalizer half)**

```python
"""Fetch and normalize items from the NIH Guide search API."""
from __future__ import annotations

GUIDE_API = "https://search.grants.nih.gov/guide/api/data"
GUIDE_URL_SUBDIR = {"NOT": "notice-files", "RFA": "rfa-files", "PA": "pa-files", "PAR": "pa-files", "PAS": "pa-files"}
PAGE_SIZE = 100


def _iso_date(value):
    """'2026-07-28T09:00:00.000Z' -> '2026-07-28'; passes through None/''. """
    if not value or not isinstance(value, str) or len(value) < 10:
        return None
    return value[:10]


def _codes(ac):
    if isinstance(ac, list):
        return [c for c in ac if c]
    if isinstance(ac, str) and ac.strip():
        return [c.strip() for c in ac.split(",") if c.strip()]
    return []


def normalize(source: dict, institutes: dict[str, str]) -> dict:
    docnum = source["docnum"]
    doctype = source.get("doctype") or ("NOT" if docnum.startswith("NOT") else docnum.split("-")[0])
    org = source.get("organization") or {}
    primary = org.get("primary") or source.get("primaryIC")
    parent = org.get("parent") or source.get("parentIC")

    due_dates = []
    lard = _iso_date(source.get("lard"))
    receipt = _iso_date(source.get("appreceiptdate"))
    if receipt:
        due_dates.append({"label": "Application receipt", "date": receipt})
    if lard and lard != receipt:
        due_dates.append({"label": "Last application receipt", "date": lard})
    due_dates.sort(key=lambda d: d["date"])

    subdir = GUIDE_URL_SUBDIR.get(doctype, "notice-files")
    filename = source.get("filename") or f"{docnum}.html"

    return {
        "notice_id": docnum,
        "source": "nih",
        "doctype": doctype,
        "title": (source.get("title") or "").strip(),
        "release_date": _iso_date(source.get("reldate")),
        "open_date": _iso_date(source.get("opendate")),
        "expiration_date": _iso_date(source.get("expdate")),
        "due_dates": due_dates,
        "next_due_date": due_dates[0]["date"] if due_dates else None,
        "activity_codes": _codes(source.get("ac")),
        "primary_ic": primary,
        "parent_ic": parent,
        "issuing_orgs": [institutes.get(primary, primary)] if primary else [],
        "url": f"https://grants.nih.gov/grants/guide/{subdir}/{filename}",
        "clinical_trials": source.get("clinicaltrials"),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest pipeline/tests/test_nih_guide.py -v
```
Expected: 3 PASS.

- [ ] **Step 6: Create `pipeline/requirements.txt`**

```
requests>=2.31
```

- [ ] **Step 7: Commit**

```bash
git add pipeline
git commit -m "feat(pipeline): NIH Guide item normalizer with fixtures"
```

---

### Task 3: NIH Guide fetchers (paginated, injectable session)

**Files:**
- Modify: `pipeline/nih_guide.py`
- Test: `pipeline/tests/test_nih_guide_fetch.py`

**Interfaces:**
- Consumes: `GUIDE_API`, `PAGE_SIZE` from Task 2.
- Produces: `fetch_recent(session, days=14, today=None) -> list[dict]` (raw `_source` dicts released within the window, newest first) and `fetch_active(session) -> list[dict]` (all still-open FOAs). `session` is anything with `.get(url, params=..., timeout=...)` returning an object with `.raise_for_status()` and `.json()`. Task 7 passes a real `requests.Session`.

- [ ] **Step 1: Write the failing tests**

`pipeline/tests/test_nih_guide_fetch.py`:

```python
import datetime as dt

from pipeline.nih_guide import fetch_recent, fetch_active


class FakeResponse:
    def __init__(self, hits, total):
        self._hits, self._total = hits, total

    def raise_for_status(self):
        pass

    def json(self):
        return {"statusCode": 200, "data": {"hits": {"total": self._total, "hits": self._hits}}}


class FakeSession:
    """Serves pages of _source dicts and records requested params."""

    def __init__(self, sources):
        self.sources = sources
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        frm, size = params["from"], params["size"]
        page = [{"_source": s} for s in self.sources[frm : frm + size]]
        return FakeResponse(page, len(self.sources))


def _src(docnum, reldate):
    return {"docnum": docnum, "reldate": reldate, "title": docnum, "doctype": "NOT",
            "organization": {"parent": "NIH", "primary": "NIA"}, "filename": docnum + ".html"}


def test_fetch_recent_stops_at_cutoff():
    today = dt.date(2026, 7, 31)
    sources = [
        _src("NOT-A", "2026-07-30T08:00:00.000Z"),
        _src("NOT-B", "2026-07-20T08:00:00.000Z"),
        _src("NOT-C", "2026-07-01T08:00:00.000Z"),  # outside 14-day window
    ]
    got = fetch_recent(FakeSession(sources), days=14, today=today)
    assert [s["docnum"] for s in got] == ["NOT-A", "NOT-B"]
    assert FakeSession(sources).calls == []  # sanity: fresh fake unused


def test_fetch_recent_requests_desc_sort():
    sess = FakeSession([_src("NOT-A", "2026-07-30T08:00:00.000Z")])
    fetch_recent(sess, days=14, today=dt.date(2026, 7, 31))
    assert sess.calls[0]["sort"] == "reldate:desc"


def test_fetch_active_paginates_to_total():
    sources = [_src(f"RFA-{i:03d}", "2026-01-01T00:00:00.000Z") for i in range(250)]
    for s in sources:
        s["type"] = "active"
    sess = FakeSession(sources)
    got = fetch_active(sess)
    assert len(got) == 250
    assert sess.calls[0]["type"] == "active"
    assert len(sess.calls) == 3  # 100 + 100 + 50
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest pipeline/tests/test_nih_guide_fetch.py -v
```
Expected: FAIL, `ImportError: cannot import name 'fetch_recent'`.

- [ ] **Step 3: Implement the fetchers (append to `pipeline/nih_guide.py`)**

```python
import datetime as _dt

TIMEOUT = 30
MAX_PAGES = 300  # hard stop; 300*100 = 30k items > entire Guide


def _pages(session, extra_params):
    fetched = 0
    for page in range(MAX_PAGES):
        params = {"searchText": "", "from": page * PAGE_SIZE, "size": PAGE_SIZE, "sort": "reldate:desc"}
        params.update(extra_params)
        resp = session.get(GUIDE_API, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        hits = resp.json()["data"]["hits"]
        batch = [h["_source"] for h in hits["hits"]]
        if not batch:
            return
        yield from batch
        fetched += len(batch)
        total = hits.get("total")
        total_n = total.get("value") if isinstance(total, dict) else total
        if total_n is not None and fetched >= int(total_n):
            return


def fetch_recent(session, days=14, today=None):
    today = today or _dt.date.today()
    cutoff = (today - _dt.timedelta(days=days)).isoformat()
    out = []
    for src in _pages(session, {}):
        rel = (src.get("reldate") or "")[:10]
        if rel and rel < cutoff:
            break
        out.append(src)
    return out


def fetch_active(session):
    return list(_pages(session, {"type": "active"}))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest pipeline/tests/ -v
```
Expected: all 6 PASS.

- [ ] **Step 5: One live smoke check (not a test)**

```bash
python3 -c "
import requests
from pipeline.nih_guide import fetch_recent
items = fetch_recent(requests.Session(), days=7)
print(len(items), 'items in last 7 days;', items[0]['docnum'] if items else '-')"
```
Expected: a plausible count (20–80) and a current docnum. If the API shape changed, fix `_pages` accordingly before continuing.

- [ ] **Step 6: Commit**

```bash
git add pipeline
git commit -m "feat(pipeline): paginated NIH Guide fetchers with cutoff"
```

---

### Task 4: Grants.gov detail module

**Files:**
- Create: `pipeline/grants_gov.py`
- Test: `pipeline/tests/test_grants_gov.py`

**Interfaces:**
- Consumes: nothing internal.
- Produces: `fetch_detail(session, opp_num) -> dict | None` returning `{"grants_gov_id": int, "synopsis": str|None, "award_ceiling": str|None, "award_floor": str|None, "close_date": "YYYY-MM-DD"|None}` or `None` when Grants.gov has no such opportunity. `session` needs `.post(url, json=..., timeout=...)`. Task 7 calls this only for opportunity doctypes (`RFA`, `PA`, `PAR`, `PAS`).

- [ ] **Step 1: Write the failing tests**

`pipeline/tests/test_grants_gov.py`:

```python
from pipeline.grants_gov import fetch_detail, _strip_html


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, search_payload, fetch_payload=None):
        self.search_payload, self.fetch_payload = search_payload, fetch_payload
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json))
        if url.endswith("search2"):
            return FakeResponse(self.search_payload)
        return FakeResponse(self.fetch_payload)


SEARCH_HIT = {"errorcode": 0, "data": {"oppHits": [{"id": "357021", "number": "PAR-25-221",
              "closeDate": "01/07/2027"}]}}
FETCH = {"data": {"id": 357021, "synopsis": {
    "synopsisDesc": "<p>This NOFO supports <b>population approaches</b>.</p>",
    "awardCeiling": "500000", "awardFloor": "none",
    "responseDate": "Jan 07, 2027 12:00:00 AM EST"}}}


def test_fetch_detail_happy_path():
    sess = FakeSession(SEARCH_HIT, FETCH)
    d = fetch_detail(sess, "PAR-25-221")
    assert d["grants_gov_id"] == 357021
    assert d["synopsis"] == "This NOFO supports population approaches."
    assert d["award_ceiling"] == "500000"
    assert d["award_floor"] is None  # "none" -> None
    assert d["close_date"] == "2027-01-07"


def test_fetch_detail_no_hit_returns_none():
    sess = FakeSession({"errorcode": 0, "data": {"oppHits": []}})
    assert fetch_detail(sess, "PAR-99-999") is None


def test_fetch_detail_ignores_wrong_number_hits():
    wrong = {"errorcode": 0, "data": {"oppHits": [{"id": "1", "number": "PAR-11-111"}]}}
    assert fetch_detail(FakeSession(wrong), "PAR-25-221") is None


def test_strip_html():
    assert _strip_html("<p>a &amp; b<br>c</p>") == "a & b c"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest pipeline/tests/test_grants_gov.py -v
```
Expected: FAIL, `ModuleNotFoundError: No module named 'pipeline.grants_gov'`.

- [ ] **Step 3: Implement `pipeline/grants_gov.py`**

```python
"""Look up FOA detail (synopsis, award figures, close date) on Grants.gov."""
from __future__ import annotations

import datetime as _dt
import html as _html
import re as _re

SEARCH_URL = "https://api.grants.gov/v1/api/search2"
FETCH_URL = "https://api.grants.gov/v1/api/fetchOpportunity"
TIMEOUT = 30

_TAG = _re.compile(r"<[^>]+>")
_WS = _re.compile(r"\s+")


def _strip_html(text):
    if not text:
        return None
    text = _TAG.sub(" ", text)
    text = _html.unescape(text)
    return _WS.sub(" ", text).strip() or None


def _clean_amount(value):
    if value is None:
        return None
    v = str(value).strip()
    return None if v.lower() in ("", "none", "0") else v


def _close_date(us_date):
    """'01/07/2027' -> '2027-01-07'."""
    if not us_date:
        return None
    try:
        return _dt.datetime.strptime(us_date.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def fetch_detail(session, opp_num):
    resp = session.post(SEARCH_URL, json={"oppNum": opp_num, "rows": 5}, timeout=TIMEOUT)
    resp.raise_for_status()
    hits = (resp.json().get("data") or {}).get("oppHits") or []
    hit = next((h for h in hits if h.get("number") == opp_num), None)
    if hit is None:
        return None

    resp = session.post(FETCH_URL, json={"opportunityId": int(hit["id"])}, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json().get("data") or {}
    syn = data.get("synopsis") or {}
    return {
        "grants_gov_id": int(data.get("id") or hit["id"]),
        "synopsis": _strip_html(syn.get("synopsisDesc")),
        "award_ceiling": _clean_amount(syn.get("awardCeiling")),
        "award_floor": _clean_amount(syn.get("awardFloor")),
        "close_date": _close_date(hit.get("closeDate")),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest pipeline/tests/test_grants_gov.py -v
```
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add pipeline
git commit -m "feat(pipeline): Grants.gov synopsis/award detail lookup"
```

---

### Task 5: Merge module — the anti-clobber contract (TDD, the heart of the fix)

**Files:**
- Create: `pipeline/merge.py`
- Test: `pipeline/tests/test_merge.py`

**Interfaces:**
- Consumes: incoming dicts shaped like `nih_guide.normalize` output (Task 2), optionally extended with Grants.gov fields (Task 4) and `topics` seeds.
- Produces:
  - `LLM_OWNED: frozenset[str]`
  - `merge_item(existing: dict | None, incoming: dict, now_iso: str) -> tuple[dict, bool]` — merged item and whether anything pipeline-owned changed.
  - `validate_item(item: dict) -> None` (raises `ValueError` with the notice id and problem).
  - `dumps_item(item: dict) -> str` — the canonical serialization.

- [ ] **Step 1: Write the failing tests**

`pipeline/tests/test_merge.py`:

```python
import pytest

from pipeline.merge import LLM_OWNED, merge_item, validate_item, dumps_item

NOW = "2026-07-31T12:00:00Z"


def incoming(**over):
    base = {
        "notice_id": "NOT-AA-26-012", "source": "nih", "doctype": "NOT",
        "title": "Notice of Special Interest (NOSI): Alcohol Use Among Older Adults",
        "release_date": "2026-07-28", "open_date": None, "expiration_date": "2026-11-17",
        "due_dates": [], "next_due_date": None, "activity_codes": [],
        "primary_ic": "NIAAA", "parent_ic": "NIH",
        "issuing_orgs": ["National Institute on Alcohol Abuse and Alcoholism"],
        "url": "https://grants.nih.gov/grants/guide/notice-files/NOT-AA-26-012.html",
        "clinical_trials": None,
    }
    base.update(over)
    return base


def test_new_item_gets_created_with_updated_at():
    merged, changed = merge_item(None, incoming(), NOW)
    assert changed is True
    assert merged["updated_at"] == NOW
    assert merged["title"].startswith("Notice of Special Interest")


def test_llm_fields_survive_refresh():
    enriched = {**incoming(), "purpose_tldr": "Summary.", "dos": ["do x"],
                "mechanisms": ["R21"], "llm_model": "claude", "updated_at": "2026-05-01T00:00:00Z"}
    fresh = incoming(title="Notice of Special Interest (NOSI): Alcohol Use Among Older Adults v2")
    merged, changed = merge_item(enriched, fresh, NOW)
    assert changed is True
    assert merged["title"].endswith("v2")
    assert merged["purpose_tldr"] == "Summary."
    assert merged["dos"] == ["do x"]
    assert merged["mechanisms"] == ["R21"]


def test_incoming_llm_keys_are_ignored_even_if_present():
    bad = {**incoming(), "purpose_tldr": "PIPELINE MUST NOT WRITE THIS"}
    merged, _ = merge_item(None, bad, NOW)
    assert "purpose_tldr" not in merged


def test_unchanged_data_is_a_noop_and_byte_stable():
    merged1, _ = merge_item(None, incoming(), NOW)
    merged2, changed = merge_item(merged1, incoming(), "2026-08-07T12:00:00Z")
    assert changed is False
    assert merged2["updated_at"] == NOW  # not bumped
    assert dumps_item(merged2) == dumps_item(merged1)


def test_unknown_existing_fields_are_preserved():
    existing, _ = merge_item(None, incoming(), NOW)
    existing["key_dates"] = [{"label": "Release Date", "date": "2026-07-28", "type": "release"}]
    existing["raw_html_hash"] = "abc123"
    merged, _ = merge_item(existing, incoming(), NOW)
    assert merged["key_dates"][0]["date"] == "2026-07-28"
    assert merged["raw_html_hash"] == "abc123"


def test_topics_hybrid_seed_only_when_absent():
    merged, _ = merge_item(None, {**incoming(), "topics": ["alcohol"]}, NOW)
    assert merged["topics"] == ["alcohol"]
    refreshed, _ = merge_item(merged, {**incoming(), "topics": ["alcohol", "aging"]}, NOW)
    assert refreshed["topics"] == ["alcohol"]  # already set -> untouched


def test_none_incoming_values_do_not_erase_existing():
    existing, _ = merge_item(None, incoming(expiration_date="2026-11-17"), NOW)
    merged, changed = merge_item(existing, incoming(expiration_date=None), "2026-08-07T00:00:00Z")
    assert merged["expiration_date"] == "2026-11-17"
    assert changed is False


def test_validate_rejects_bad_items():
    ok, _ = merge_item(None, incoming(), NOW)
    validate_item(ok)  # no raise
    with pytest.raises(ValueError, match="NOT-AA-26-012"):
        validate_item({**ok, "release_date": "07/28/2026"})
    with pytest.raises(ValueError, match="title"):
        validate_item({**ok, "title": ""})
    with pytest.raises(ValueError, match="notice_id"):
        validate_item({k: v for k, v in ok.items() if k != "notice_id"})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest pipeline/tests/test_merge.py -v
```
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `pipeline/merge.py`**

```python
"""Anti-clobber merge: the refresh may never destroy LLM enrichment."""
from __future__ import annotations

import json
import re

LLM_OWNED = frozenset({
    "purpose_tldr", "eligibility_tldr", "dos", "donts", "career_stages",
    "strategic_priorities", "budget", "mechanisms", "llm_model", "enriched_at",
})
HYBRID = frozenset({"topics"})
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def merge_item(existing, incoming, now_iso):
    incoming = {k: v for k, v in incoming.items() if k not in LLM_OWNED}
    merged = dict(existing) if existing else {}
    changed = False

    for key, value in incoming.items():
        if key in HYBRID:
            if key not in merged and value:
                merged[key] = value
                changed = True
            continue
        if value is None and key in merged:
            continue  # never erase with None
        if merged.get(key) != value:
            merged[key] = value
            changed = True

    if existing is None:
        changed = True
    if changed:
        merged["updated_at"] = now_iso
    return merged, changed


def validate_item(item):
    nid = item.get("notice_id") or "<missing notice_id>"

    def fail(problem):
        raise ValueError(f"{nid}: {problem}")

    if not item.get("notice_id"):
        fail("notice_id is required")
    if not (item.get("title") or "").strip():
        fail("title is empty")
    if not item.get("url", "").startswith("https://"):
        fail("url must be https")
    for key in ("release_date", "open_date", "expiration_date", "next_due_date"):
        v = item.get(key)
        if v is not None and not _ISO_DATE.match(str(v)):
            fail(f"{key} is not ISO YYYY-MM-DD: {v!r}")
    for d in item.get("due_dates") or []:
        if not _ISO_DATE.match(str(d.get("date", ""))):
            fail(f"due_dates entry has bad date: {d!r}")
    if not isinstance(item.get("activity_codes", []), list):
        fail("activity_codes must be a list")


def dumps_item(item):
    return json.dumps(item, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest pipeline/tests/test_merge.py -v
```
Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add pipeline
git commit -m "feat(pipeline): anti-clobber merge, validation, canonical serialization"
```

---

### Task 6: Emit module — site payload and RSS

**Files:**
- Create: `pipeline/emit.py`
- Test: `pipeline/tests/test_emit.py`

**Interfaces:**
- Consumes: merged item dicts (Task 5 shape, possibly enriched).
- Produces:
  - `FEED_START = "2026-02-06"`
  - `is_opportunity(item) -> bool` (doctype in RFA/PA/PAR/PAS, or title starts with "Notice of Special Interest")
  - `build_site_payload(items, generated_at, today) -> dict` → `{"generated_at": ..., "items": [...]}` with `synopsis` replaced by `synopsis_truncated` (400 chars, word-safe, "…"), sorted by (`release_date` desc, `notice_id`), including items where `release_date >= FEED_START` OR (opportunity AND still open on `today`).
  - `build_rss(items, generated_at) -> str` — RSS 2.0, 50 newest feed-window items.
  - Task 10's `logic.js` consumes the payload: every item has `synopsis_truncated` (str|None) and never a full `synopsis`.

- [ ] **Step 1: Write the failing tests**

`pipeline/tests/test_emit.py`:

```python
# Plain ElementTree is fine here: it parses RSS this test just generated from
# fixtures (trusted input), so the XXE/defusedxml concern does not apply.
import xml.etree.ElementTree as ET

from pipeline.emit import FEED_START, build_rss, build_site_payload, is_opportunity

GEN = "2026-07-31T12:00:00Z"
TODAY = "2026-07-31"


def item(nid, doctype="NOT", release="2026-07-28", exp=None, title=None, **over):
    base = {"notice_id": nid, "doctype": doctype, "release_date": release,
            "expiration_date": exp, "next_due_date": None, "due_dates": [],
            "title": title or f"Title {nid}", "url": f"https://x/{nid}.html",
            "issuing_orgs": ["NIA"], "activity_codes": [], "primary_ic": "NIA",
            "synopsis": None}
    base.update(over)
    return base


def test_is_opportunity():
    assert is_opportunity(item("PAR-26-001", doctype="PAR"))
    assert is_opportunity(item("NOT-AA-26-012", title="Notice of Special Interest (NOSI): X"))
    assert not is_opportunity(item("NOT-OD-26-001", title="Policy Update"))


def test_payload_includes_feed_window_and_open_older_opps():
    items = [
        item("NOT-NEW"),                                            # in window
        item("NOT-OLD", release="2025-12-01"),                      # admin, pre-window -> out
        item("PAR-OLD", doctype="PAR", release="2024-11-06", exp="2027-01-07"),  # open opp -> in
        item("PAR-DEAD", doctype="PAR", release="2024-11-06", exp="2025-01-01"), # closed opp -> out
    ]
    payload = build_site_payload(items, GEN, TODAY)
    ids = [i["notice_id"] for i in payload["items"]]
    assert ids == ["NOT-NEW", "PAR-OLD"]
    assert payload["generated_at"] == GEN


def test_payload_truncates_synopsis_and_drops_full_text():
    long = "word " * 200
    payload = build_site_payload([item("PAR-1", doctype="PAR", exp="2027-01-01", synopsis=long)], GEN, TODAY)
    it = payload["items"][0]
    assert "synopsis" not in it
    assert it["synopsis_truncated"].endswith("…")
    assert len(it["synopsis_truncated"]) <= 401


def test_payload_sorted_release_desc_then_id():
    items = [item("B", release="2026-07-01"), item("A", release="2026-07-28"),
             item("C", release="2026-07-28")]
    payload = build_site_payload(items, GEN, TODAY)
    assert [i["notice_id"] for i in payload["items"]] == ["A", "C", "B"]


def test_rss_is_valid_xml_with_escaped_entities():
    rss = build_rss([item("NOT-1", title="Aging & Alcohol <2026>")], GEN)
    root = ET.fromstring(rss)  # raises if malformed
    assert root.tag == "rss"
    itm = root.find("./channel/item")
    assert itm.find("title").text == "Aging & Alcohol <2026>"
    assert itm.find("guid").text == "NOT-1"


def test_rss_caps_at_50_and_skips_prewindow():
    items = [item(f"NOT-{i:03d}") for i in range(60)] + [item("NOT-OLD", release="2025-01-01")]
    rss = build_rss(items, GEN)
    root = ET.fromstring(rss)
    assert len(root.findall("./channel/item")) == 50
    assert FEED_START == "2026-02-06"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest pipeline/tests/test_emit.py -v
```
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `pipeline/emit.py`**

```python
"""Build the site data payload and RSS feed."""
from __future__ import annotations

from xml.sax.saxutils import escape

FEED_START = "2026-02-06"
OPP_DOCTYPES = {"RFA", "PA", "PAR", "PAS"}
SITE_URL = "https://muntasirmasum.github.io/grant-radar"
TRUNCATE = 400


def is_opportunity(item):
    if item.get("doctype") in OPP_DOCTYPES:
        return True
    return (item.get("title") or "").startswith("Notice of Special Interest")


def _still_open(item, today):
    for key in ("expiration_date", "next_due_date"):
        v = item.get(key)
        if v and v >= today:
            return True
    return False


def _truncate(text):
    if not text:
        return None
    if len(text) <= TRUNCATE:
        return text
    cut = text[:TRUNCATE]
    cut = cut[: cut.rfind(" ")] if " " in cut else cut
    return cut.rstrip(",.;: ") + "…"


def _in_feed_window(item):
    return (item.get("release_date") or "") >= FEED_START


def build_site_payload(items, generated_at, today):
    keep = []
    for item in items:
        if _in_feed_window(item) or (is_opportunity(item) and _still_open(item, today)):
            out = {k: v for k, v in item.items() if k != "synopsis"}
            out["synopsis_truncated"] = out.get("synopsis_truncated") or _truncate(item.get("synopsis"))
            keep.append(out)
    keep.sort(key=lambda i: (i.get("release_date") or "", ""), reverse=True)
    keep.sort(key=lambda i: i["notice_id"])
    keep.sort(key=lambda i: i.get("release_date") or "", reverse=True)
    return {"generated_at": generated_at, "items": keep}


def build_rss(items, generated_at):
    feed_items = sorted(
        (i for i in items if _in_feed_window(i)),
        key=lambda i: (i.get("release_date") or "", i["notice_id"]),
        reverse=True,
    )[:50]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        "<title>Grant Radar</title>",
        f"<link>{SITE_URL}/</link>",
        "<description>NIH funding notices and opportunities, structured weekly.</description>",
        f"<lastBuildDate>{escape(generated_at)}</lastBuildDate>",
    ]
    for i in feed_items:
        desc = i.get("purpose_tldr") or i.get("synopsis_truncated") or ""
        lines += [
            "<item>",
            f"<title>{escape(i.get('title') or i['notice_id'])}</title>",
            f"<link>{escape(i.get('url') or SITE_URL)}</link>",
            f"<guid isPermaLink=\"false\">{escape(i['notice_id'])}</guid>",
            f"<pubDate>{escape(i.get('release_date') or '')}</pubDate>",
            f"<description>{escape(desc)}</description>",
            "</item>",
        ]
    lines += ["</channel>", "</rss>"]
    return "\n".join(lines) + "\n"
```

Note the triple sort in `build_site_payload` is deliberate and stable: final order is release_date desc, then notice_id asc within a date (Python sorts are stable, so sort by the tiebreaker first).

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest pipeline/tests/ -v
```
Expected: all PASS (Tasks 2–6 suites).

- [ ] **Step 5: Commit**

```bash
git add pipeline
git commit -m "feat(pipeline): site payload and RSS emission"
```

---

### Task 7: Refresh orchestrator

**Files:**
- Create: `pipeline/refresh.py`
- Test: `pipeline/tests/test_refresh.py`

**Interfaces:**
- Consumes: everything from Tasks 2–6.
- Produces: `python -m pipeline.refresh [--days N] [--emit-only]`. Reads/writes `data/notices/<year>/<id>.json`, caches HTML to `data/raw/nih/<year>/<id>.html`, writes `data/notices.json` and `data/feed.xml`. Also exposes `run(root, session, today, days, emit_only) -> dict` (stats) for tests. `/refresh-tldrs` (Task 15) calls `python3 -m pipeline.refresh --emit-only` after enriching.

- [ ] **Step 1: Write the failing test**

`pipeline/tests/test_refresh.py`:

```python
import datetime as dt
import json
from pathlib import Path

from pipeline import refresh


class FakeGuide:
    def __init__(self, recent, active):
        self.recent, self.active = recent, active


def guide_src(docnum, reldate, doctype="NOT", exp=None):
    return {"docnum": docnum, "reldate": reldate, "doctype": doctype,
            "title": f"Title {docnum}", "organization": {"parent": "NIH", "primary": "NIA"},
            "filename": f"{docnum}.html", "expdate": exp, "ac": ""}


def test_run_end_to_end(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2026").mkdir(parents=True)
    (root / "data").joinpath("taxonomy.json").write_text(json.dumps(
        {"institutes": {"NIA": "National Institute on Aging"},
         "topics": {"aging": ["aging", "older adult"]}}))

    # Pre-existing enriched item that the refresh must not clobber.
    enriched = {"notice_id": "NOT-AG-26-900", "source": "nih", "title": "Old Title",
                "release_date": "2026-07-20", "url": "https://grants.nih.gov/x.html",
                "purpose_tldr": "KEEP ME", "issuing_orgs": ["National Institute on Aging"]}
    (root / "data/notices/2026/NOT-AG-26-900.json").write_text(json.dumps(enriched))

    recent = [guide_src("NOT-AG-26-900", "2026-07-20T00:00:00.000Z"),
              guide_src("NOT-AA-26-012", "2026-07-28T00:00:00.000Z")]
    active = [guide_src("PAR-26-118", "2026-06-01T00:00:00.000Z", doctype="PAR",
                        exp="2027-05-08T00:00:00.000Z")]

    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: recent)
    monkeypatch.setattr(refresh, "fetch_active", lambda s: active)
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: {
        "grants_gov_id": 1, "synopsis": "A K01 in aging research for older adult cohorts.",
        "award_ceiling": "150000", "award_floor": None, "close_date": "2027-05-07"})
    monkeypatch.setattr(refresh, "fetch_html", lambda s, url: "<html>cached</html>")

    stats = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)

    kept = json.loads((root / "data/notices/2026/NOT-AG-26-900.json").read_text())
    assert kept["purpose_tldr"] == "KEEP ME"
    assert kept["title"] == "Title NOT-AG-26-900"      # pipeline field updated
    assert kept["primary_ic"] == "NIA"

    par = json.loads((root / "data/notices/2026/PAR-26-118.json").read_text())
    assert par["synopsis"].startswith("A K01")
    assert par["award_ceiling"] == "150000"
    assert par["topics"] == ["aging"]                  # rule-seeded from taxonomy keywords

    payload = json.loads((root / "data/notices.json").read_text())
    assert {i["notice_id"] for i in payload["items"]} >= {"NOT-AA-26-012", "PAR-26-118"}
    assert "synopsis" not in payload["items"][0]
    assert (root / "data/feed.xml").exists()
    assert (root / "data/raw/nih/2026/NOT-AA-26-012.html").read_text() == "<html>cached</html>"
    assert stats["written"] >= 2


def test_emit_only_rebuilds_without_fetching(tmp_path, monkeypatch):
    root = tmp_path
    d = root / "data/notices/2026"
    d.mkdir(parents=True)
    (root / "data/taxonomy.json").write_text(json.dumps({"institutes": {}, "topics": {}}))
    (d / "NOT-X.json").write_text(json.dumps({
        "notice_id": "NOT-X", "title": "T", "release_date": "2026-07-01",
        "url": "https://grants.nih.gov/x.html"}))

    def boom(*a, **k):
        raise AssertionError("must not fetch in --emit-only")

    monkeypatch.setattr(refresh, "fetch_recent", boom)
    monkeypatch.setattr(refresh, "fetch_active", boom)
    refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14, emit_only=True)
    assert (root / "data/notices.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest pipeline/tests/test_refresh.py -v
```
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `pipeline/refresh.py`**

```python
"""Weekly refresh: NIH Guide + Grants.gov -> per-item JSON -> site payload.

Two-phase for safety: everything is fetched, merged, and validated in
memory first; files are only written after the whole batch is clean, so a
failing API or bad item aborts the run without partial writes (spec §7).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import requests

from pipeline.emit import build_rss, build_site_payload, is_opportunity
from pipeline.grants_gov import fetch_detail
from pipeline.merge import dumps_item, merge_item, validate_item
from pipeline.nih_guide import fetch_active, fetch_recent, normalize

RAW_TIMEOUT = 30


def fetch_html(session, url):
    resp = session.get(url, timeout=RAW_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def _load_existing(root):
    items = {}
    for path in sorted((root / "data" / "notices").glob("*/*.json")):
        item = json.loads(path.read_text())
        items[item["notice_id"]] = (item, path)
    return items


def _item_path(root, item):
    year = (item.get("release_date") or "1900")[:4]
    return root / "data" / "notices" / year / f"{item['notice_id']}.json"


def _seed_topics(item, topics_map):
    if "topics" in item:
        return item
    hay = " ".join(filter(None, [item.get("title"), item.get("synopsis")])).lower()
    tags = [name for name, kws in sorted(topics_map.items())
            if any(kw.lower() in hay for kw in (kws or [name]))]
    if tags:
        item["topics"] = tags[:4]
    return item


def _backfill_primary_ic(item, institutes):
    if item.get("primary_ic") or not item.get("issuing_orgs"):
        return item
    name_to_code = {v: k for k, v in institutes.items()}
    code = name_to_code.get(item["issuing_orgs"][0])
    if code:
        item["primary_ic"] = code
    return item


def run(root, session, today, days=14, emit_only=False):
    root = Path(root)
    taxonomy = json.loads((root / "data" / "taxonomy.json").read_text())
    institutes, topics_map = taxonomy["institutes"], taxonomy["topics"]
    now_iso = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    existing = _load_existing(root)
    stats = {"fetched": 0, "written": 0, "unchanged": 0}

    merged_all: dict[str, dict] = {nid: item for nid, (item, _) in existing.items()}
    to_write: dict[str, dict] = {}
    html_cache: dict[str, str] = {}

    if not emit_only:
        sources = {s["docnum"]: s for s in fetch_active(session)}
        recent = fetch_recent(session, days=days, today=today)
        for s in recent:
            sources[s["docnum"]] = s
        recent_ids = {s["docnum"] for s in recent}
        stats["fetched"] = len(sources)

        for docnum, source in sources.items():
            incoming = normalize(source, institutes)
            old = existing.get(docnum, (None, None))[0]

            merged, changed = merge_item(old, incoming, now_iso)
            needs_detail = is_opportunity(merged) and (
                changed or not merged.get("grants_gov_id"))
            if needs_detail:
                detail = fetch_detail(session, docnum)
                if detail:
                    merged, changed2 = merge_item(merged, {**incoming, **detail}, now_iso)
                    changed = changed or changed2
            merged = _seed_topics(merged, topics_map)
            merged = _backfill_primary_ic(merged, institutes)

            if changed or old is None:
                to_write[docnum] = merged
            else:
                stats["unchanged"] += 1
            merged_all[docnum] = merged

            if docnum in recent_ids and old is None and not merged.get("purpose_tldr"):
                html_cache[docnum] = fetch_html(session, merged["url"])

        # legacy backfill pass for items the APIs no longer return
        for nid, item in merged_all.items():
            if nid not in to_write:
                fixed = _backfill_primary_ic(dict(item), institutes)
                if fixed != item:
                    to_write[nid] = fixed
                    merged_all[nid] = fixed

    # ---- validate everything BEFORE any write (all-or-nothing) ----
    for item in merged_all.values():
        validate_item(item)

    for nid, item in to_write.items():
        path = _item_path(root, item)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps_item(item))
        stats["written"] += 1

    for nid, html in html_cache.items():
        item = merged_all[nid]
        raw = root / "data" / "raw" / "nih" / (item.get("release_date") or "1900")[:4]
        raw.mkdir(parents=True, exist_ok=True)
        (raw / f"{nid}.html").write_text(html)

    payload = build_site_payload(list(merged_all.values()), now_iso, today.isoformat())
    (root / "data" / "notices.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    (root / "data" / "feed.xml").write_text(build_rss(list(merged_all.values()), now_iso))

    print(f"fetched={stats['fetched']} written={stats['written']} "
          f"unchanged={stats['unchanged']} site_items={len(payload['items'])}")
    return stats


def main(argv=None):
    parser = argparse.ArgumentParser(description="Grant Radar weekly refresh")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--emit-only", action="store_true",
                        help="rebuild notices.json/feed.xml from item files, no fetching")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    session = requests.Session()
    session.headers["User-Agent"] = "grant-radar (github.com/muntasirmasum/grant-radar)"
    run(root=root, session=session, today=dt.date.today(),
        days=args.days, emit_only=args.emit_only)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest pipeline/tests/ -v
```
Expected: all PASS. If `test_run_end_to_end` fails on `validate_item` for the legacy fixture item (it has no `doctype`), that is correct behavior to fix in the test data, not by weakening validation: legacy real files all carry `notice_id`/`title`/`url`/dates which is all validation requires.

- [ ] **Step 5: Commit**

```bash
git add pipeline
git commit -m "feat(pipeline): two-phase refresh orchestrator with emit-only mode"
```

---

### Task 8: CI — new weekly-refresh, pytest ci, feed staging in pages-deploy

**Files:**
- Modify: `.github/workflows/weekly-refresh.yml` (full replacement)
- Modify: `.github/workflows/ci.yml` (full replacement)
- Modify: `.github/workflows/pages-deploy.yml:32-38` (stage feed.xml too)

**Interfaces:**
- Consumes: `pipeline/refresh.py` CLI (Task 7), pytest suite, and (after Task 9) `node --test tests/js/`.
- Produces: green scheduled refresh; `ci` job later extended in Task 9 Step 6 already included here (node test step is added now but guarded so it passes with no test files yet).

- [ ] **Step 1: Replace `.github/workflows/weekly-refresh.yml` entirely**

```yaml
name: weekly-refresh

# API refresh: no keys needed. LLM fields (purpose_tldr, dos/donts, ...)
# are filled in manually via the /refresh-tldrs command in Claude Code
# and are never overwritten by this job (anti-clobber merge).

on:
  schedule:
    - cron: "0 23 * * 0" # Sunday 23:00 UTC
  workflow_dispatch:
    inputs:
      days:
        description: "Look-back window in days"
        required: false
        default: "14"

permissions:
  contents: write

jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r pipeline/requirements.txt
      - name: Refresh from NIH Guide + Grants.gov
        run: python -m pipeline.refresh --days "${{ github.event.inputs.days || 14 }}"
      - name: Commit refreshed data
        run: |
          git config user.name "grant-radar-bot"
          git config user.email "bot@grant-radar.local"
          git add data/
          if ! git diff --cached --quiet; then
            git commit -m "chore(data): api refresh $(date -u +%Y-%m-%d)"
            git push
          else
            echo "No data changes."
          fi
```

- [ ] **Step 2: Replace `.github/workflows/ci.yml` entirely**

```yaml
name: ci

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
    paths:
      - "pipeline/**"
      - "site/**"
      - "tests/**"
      - "data/taxonomy.json"
      - ".github/workflows/ci.yml"

jobs:
  pipeline-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r pipeline/requirements.txt pytest
      - run: python -m pytest pipeline/tests -v
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - name: Run frontend logic tests
        run: |
          if ls tests/js/*.test.mjs >/dev/null 2>&1; then
            node --test tests/js/
          else
            echo "No frontend tests yet."
          fi
```

- [ ] **Step 3: Update the staging step in `.github/workflows/pages-deploy.yml`**

Replace the `Stage data file` step (currently lines 32–38) with:

```yaml
      - name: Stage data files
        run: |
          if [ -f data/notices.json ]; then
            cp data/notices.json site/notices.json
          else
            echo '{"generated_at":null,"items":[]}' > site/notices.json
          fi
          if [ -f data/feed.xml ]; then
            cp data/feed.xml site/feed.xml
          fi
```

- [ ] **Step 4: Validate YAML locally**

```bash
python3 -c "
import yaml
for f in ('.github/workflows/weekly-refresh.yml','.github/workflows/ci.yml','.github/workflows/pages-deploy.yml'):
    yaml.safe_load(open(f)); print('ok', f)"
```
Expected: three `ok` lines (pyyaml was installed in Task 1).

- [ ] **Step 5: Commit**

```bash
git add .github/workflows
git commit -m "ci: python refresh workflow, pytest+node ci, stage feed.xml"
```

---

### Task 9: Site foundation — stylesheet, theme bootstrapping, shared UI

**Files:**
- Create: `site/style.css` (full replacement of the old file's content), `site/js/ui.js`
- Delete: `site/charts.js`, `site/app.js` (replaced by `site/js/*` over Tasks 9–13; delete now, the site is rebuilt wholesale this branch)

**Interfaces:**
- Consumes: design tokens from spec §4.3.
- Produces: CSS custom properties on `:root` / `:root.dark`; classes used by Tasks 11–14: `nav`, `nav-inner`, `brand`, `ping`, `nav-links`, `nav-tools`, `search`, `iconbtn`, `home-link`, `wrap`, `eyebrow`, `h1`, `lead`, `soon`, `soon-label`, `soon-row`, `days`, `days--mid`, `soon-title`, `soon-meta`, `chips`, `chip`, `chip--on`, `week`, `card`, `card--gold`, `card--compact`, `meta`, `meta-id`, `title`, `tldr`, `syn`, `pillrow`, `due`, `due--hot`, `pill`, `pill--gold`, `actions`, `foryou`, `detail`, `cal-month`, `cal-row`, `chart-card`, `footer`, `foot-inner`, `error-card`, `profile-editor`. JS: `ui.js` exports `initTheme()`, `esc(text)`, `fmtDate(iso)`.

- [ ] **Step 1: Delete the old JS**

```bash
git rm --quiet site/app.js site/charts.js
mkdir -p site/js
```

- [ ] **Step 2: Write `site/style.css`**

```css
/* ============================================================
   Grant Radar — design system shared with muntasirmasum.com.
   Tokens on :root (light) and :root.dark; namespace-free classes
   because this stylesheet owns the whole page.
   ============================================================ */
:root{
  --bg:#f5f6f8; --surface:#ffffff; --ink:#1f2d3a; --body:#3b4651;
  --muted:#5a6571; --muted2:#74808b; --border:#e7eaee; --hair:#eef0f3;
  --btnborder:#cfd6dd;
  --accent:#46166b; --accent-text:#46166b; --accent-hover:#341050;
  --accent-tint:#f1ecf7; --accent-underline:#dccfe8;
  --gold:#c2a23a; --gold-tint:#fbf3e0; --gold-text:#a07d12;
  --shadow:rgba(31,45,58,.09);
}
:root.dark{
  --bg:#141118; --surface:#1f1b27; --ink:#f4f2f8; --body:#cdc9d6;
  --muted:#aaa6b5; --muted2:#928da0; --border:#332e3e; --hair:#28232f;
  --btnborder:#4a4456;
  --accent:#7a4fb0; --accent-text:#cbb1e8; --accent-hover:#6b41a0;
  --accent-tint:#2a2138; --accent-underline:#4a3b60;
  --gold:#c2a23a; --gold-tint:#332b16; --gold-text:#d8b84e;
  --shadow:rgba(0,0,0,.4);
}
*{ box-sizing:border-box; }
html,body{ margin:0; padding:0; }
body{ background:var(--bg); color:var(--body);
  font-family:'IBM Plex Sans',system-ui,sans-serif; -webkit-font-smoothing:antialiased; }
::selection{ background:#e7d8f3; }
:root.dark ::selection{ background:#43355c; }
a{ color:var(--accent-text); }
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{ animation-duration:.001ms !important; transition-duration:.001ms !important; }
}
:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; }

/* ---------- NAV ---------- */
.nav{ position:sticky; top:0; z-index:50;
  background:color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter:saturate(180%) blur(10px); -webkit-backdrop-filter:saturate(180%) blur(10px);
  border-bottom:1px solid var(--border); }
.nav-inner{ max-width:1020px; margin:0 auto; padding:12px 24px; display:flex;
  align-items:center; justify-content:space-between; gap:14px; flex-wrap:wrap; }
.brand{ display:flex; align-items:center; gap:8px; font:600 20px 'Newsreader',Georgia,serif;
  color:var(--ink); letter-spacing:-.2px; text-decoration:none; }
.ping{ width:9px; height:9px; border-radius:50%; background:var(--accent); position:relative; flex:none; }
.ping::after{ content:''; position:absolute; inset:-4px; border-radius:50%;
  border:1.5px solid var(--accent); opacity:.45; }
.nav-links{ display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
.nav-links a{ font:500 14px 'IBM Plex Sans',system-ui,sans-serif; color:var(--muted); text-decoration:none; }
.nav-links a:hover{ color:var(--accent-text); }
.nav-links a.active{ font-weight:600; color:var(--accent-text); }
.nav-tools{ display:flex; align-items:center; gap:12px; margin-left:auto; }
.search{ border:1px solid var(--btnborder); border-radius:8px; padding:6px 11px; min-width:180px;
  font:400 13px 'IBM Plex Sans',system-ui,sans-serif; color:var(--ink); background:var(--surface); }
.search::placeholder{ color:var(--muted2); }
.iconbtn{ display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px;
  cursor:pointer; color:var(--body); background:var(--surface); border:1px solid var(--btnborder);
  border-radius:8px; font-size:15px; line-height:1; }
.iconbtn:hover{ color:var(--accent-text); border-color:var(--accent-text); }
.home-link{ font:600 13px 'IBM Plex Sans',system-ui,sans-serif; color:var(--accent-text);
  text-decoration:none; white-space:nowrap; }

/* ---------- PAGE SHELL ---------- */
.wrap{ max-width:790px; margin:0 auto; padding:40px 24px 24px; }
.eyebrow{ font:600 11.5px 'IBM Plex Sans',system-ui,sans-serif; letter-spacing:.12em;
  text-transform:uppercase; color:var(--accent-text); }
.h1{ font:600 38px 'Newsreader',Georgia,serif; color:var(--ink); margin:6px 0 0; letter-spacing:-.4px; }
.lead{ font:400 14.5px/1.6 'IBM Plex Sans',system-ui,sans-serif; color:var(--muted2); margin:8px 0 0; }

/* ---------- CLOSING SOON ---------- */
.soon{ margin-top:24px; background:var(--accent-tint); border:1px solid var(--border);
  border-radius:12px; padding:14px 16px; }
.soon-label{ display:flex; justify-content:space-between; align-items:center; gap:10px;
  font:600 11px 'IBM Plex Sans',system-ui,sans-serif; letter-spacing:.11em; text-transform:uppercase;
  color:var(--accent-text); margin-bottom:8px; }
.soon-label a{ font:600 12px 'IBM Plex Sans',system-ui,sans-serif; letter-spacing:0;
  text-transform:none; color:var(--accent-text); text-decoration:none; }
.soon-row{ display:flex; align-items:center; gap:12px; padding:8px 0;
  border-top:1px solid var(--accent-underline); }
.soon-row:first-of-type{ border-top:0; }
.days{ flex:none; min-width:54px; text-align:center; background:var(--accent); color:#fff;
  border-radius:7px; padding:4px 6px; font:700 12px/1.15 'IBM Plex Sans',system-ui,sans-serif; }
.days small{ display:block; font:600 8.5px 'IBM Plex Sans',system-ui,sans-serif;
  opacity:.8; letter-spacing:.05em; }
.days--mid{ background:var(--surface); color:var(--accent-text); border:1px solid var(--accent); }
.soon-title{ font:600 14.5px/1.3 'Newsreader',Georgia,serif; color:var(--ink); }
.soon-title a{ color:inherit; text-decoration:none; }
.soon-title a:hover{ color:var(--accent-text); }
.soon-meta{ font:400 11.5px 'IBM Plex Sans',system-ui,sans-serif; color:var(--muted2); margin-top:1px; }

/* ---------- CHIPS ---------- */
.chips{ display:flex; gap:7px; flex-wrap:wrap; margin:22px 0 2px; }
.chip{ border:1px solid var(--border); background:var(--surface); color:var(--muted);
  border-radius:999px; padding:6px 14px; font:600 12.5px 'IBM Plex Sans',system-ui,sans-serif;
  cursor:pointer; transition:all .15s ease; }
.chip:hover{ border-color:var(--accent); color:var(--accent-text); }
.chip--on{ background:var(--accent); border-color:var(--accent); color:#fff; }
.chip--on:hover{ color:#fff; }
.chip .n{ opacity:.65; font-weight:500; margin-left:3px; }

/* ---------- WEEK DIVIDERS + FEED ---------- */
.week{ display:flex; align-items:center; gap:12px; margin:26px 0 12px; }
.week span{ font:600 14px 'Newsreader',Georgia,serif; font-style:italic; color:var(--muted); }
.week::after{ content:''; flex:1; height:1px; background:var(--hair); }

/* ---------- CARDS ---------- */
.card{ background:var(--surface); border:1px solid var(--border); border-left:3px solid var(--accent);
  border-radius:12px; padding:18px 20px; margin-bottom:11px;
  transition:box-shadow .18s ease, transform .18s ease; }
.card:hover{ box-shadow:0 10px 28px var(--shadow); transform:translateY(-2px); }
.card--gold{ border-left-color:var(--gold); }
.card--compact{ padding:13px 20px; }
.meta{ display:flex; align-items:center; gap:8px; flex-wrap:wrap;
  font:600 10.5px 'IBM Plex Sans',system-ui,sans-serif; letter-spacing:.1em;
  text-transform:uppercase; color:var(--accent-text); }
.card--gold .meta{ color:var(--gold-text); }
.meta-id{ color:var(--muted2); letter-spacing:.04em; font-weight:500; }
.title{ font:600 19px/1.32 'Newsreader',Georgia,serif; color:var(--ink); margin:7px 0 0; }
.card--compact .title{ font-size:15.5px; margin-top:4px; }
.title a{ color:inherit; text-decoration:none; }
.title a:hover{ color:var(--accent-text); }
.tldr{ font:400 13.5px/1.6 'IBM Plex Sans',system-ui,sans-serif; color:var(--body);
  margin:9px 0 0; padding-left:10px; border-left:2px solid var(--accent-underline); }
.tldr b{ font-weight:600; color:var(--accent-text); font-size:10px; letter-spacing:.08em;
  text-transform:uppercase; margin-right:5px; }
.syn{ font:400 13.5px/1.6 'IBM Plex Sans',system-ui,sans-serif; color:var(--muted); margin:9px 0 0; }
.syn b{ font-weight:600; color:var(--muted2); font-size:10px; letter-spacing:.08em;
  text-transform:uppercase; margin-right:5px; }
.pillrow{ display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:11px; }
.due{ display:inline-flex; align-items:center; gap:5px; background:var(--gold-tint);
  color:var(--gold-text); border-radius:7px; padding:3px 9px;
  font:700 11px 'IBM Plex Sans',system-ui,sans-serif; }
.due--hot{ background:var(--accent); color:#fff; }
.pill{ background:var(--accent-tint); color:var(--accent-text); border-radius:999px;
  padding:3px 10px; font:600 11px 'IBM Plex Sans',system-ui,sans-serif; }
.pill--gold{ background:var(--gold-tint); color:var(--gold-text); }
.actions{ margin-left:auto; display:flex; gap:12px; align-items:center; }
.actions button, .actions a{ font:600 12px 'IBM Plex Sans',system-ui,sans-serif; color:var(--muted2);
  background:none; border:0; padding:0; cursor:pointer; text-decoration:none; }
.actions button:hover, .actions a:hover{ color:var(--accent-text); }
.actions .saved{ color:var(--accent-text); }
.foryou{ display:flex; align-items:center; gap:6px; margin-top:10px;
  font:600 11px 'IBM Plex Sans',system-ui,sans-serif; color:var(--accent-text); }
.foryou i{ width:6px; height:6px; border-radius:50%; background:var(--accent); flex:none; }
.foryou em{ font-style:normal; font-weight:400; color:var(--muted2); }
.detail{ margin-top:13px; border-top:1px solid var(--hair); padding-top:12px;
  display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.detail h6{ font:600 10px 'IBM Plex Sans',system-ui,sans-serif; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted2); margin:0 0 6px; }
.detail ul{ margin:0; padding-left:15px; font:400 12.5px/1.55 'IBM Plex Sans',system-ui,sans-serif;
  color:var(--body); }
.detail .do li::marker{ color:#3a8a5f; }
.detail .dont li::marker{ color:#b04a4a; }
.load-note{ text-align:center; font:400 13px 'IBM Plex Sans',system-ui,sans-serif;
  color:var(--muted2); margin:18px 0; }

/* ---------- PROFILE EDITOR ---------- */
.profile-editor{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
  padding:16px 18px; margin-top:12px; }
.profile-editor label{ display:block; font:600 11px 'IBM Plex Sans',system-ui,sans-serif;
  letter-spacing:.08em; text-transform:uppercase; color:var(--muted2); margin:10px 0 4px; }
.profile-editor label:first-of-type{ margin-top:0; }
.profile-editor input{ width:100%; border:1px solid var(--btnborder); border-radius:8px;
  padding:7px 10px; font:400 13.5px 'IBM Plex Sans',system-ui,sans-serif;
  color:var(--ink); background:var(--bg); }
.profile-editor .row{ display:flex; gap:8px; margin-top:12px; }
.btn{ background:var(--accent); color:#fff; border:0; border-radius:8px; padding:8px 15px;
  font:600 13px 'IBM Plex Sans',system-ui,sans-serif; cursor:pointer; }
.btn:hover{ background:var(--accent-hover); }
.btn--ghost{ background:none; border:1px solid var(--btnborder); color:var(--body); }
.btn--ghost:hover{ border-color:var(--accent-text); color:var(--accent-text); }

/* ---------- CALENDAR ---------- */
.cal-month{ font:600 22px 'Newsreader',Georgia,serif; color:var(--ink); margin:28px 0 10px; }
.cal-row{ display:flex; align-items:center; gap:12px; background:var(--surface);
  border:1px solid var(--border); border-radius:10px; padding:10px 14px; margin-bottom:7px; }
.cal-row .soon-title{ font-size:15px; }

/* ---------- TRENDS ---------- */
.chart-card{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
  padding:18px 20px; margin-bottom:16px; }
.chart-card h3{ font:600 17px 'Newsreader',Georgia,serif; color:var(--ink); margin:0 0 10px; }

/* ---------- PROSE (about) ---------- */
.prose{ font:400 15.5px/1.65 'IBM Plex Sans',system-ui,sans-serif; color:var(--body); }
.prose h2{ font:600 24px 'Newsreader',Georgia,serif; color:var(--ink); margin:28px 0 8px; }
.prose a{ color:var(--accent-text); text-decoration:none; border-bottom:1px solid var(--accent-underline); }
.prose a:hover{ color:var(--accent); }

/* ---------- ERROR ---------- */
.error-card{ background:var(--surface); border:1px solid var(--border); border-left:3px solid #b04a4a;
  border-radius:12px; padding:18px 20px; margin-top:20px;
  font:400 14px/1.6 'IBM Plex Sans',system-ui,sans-serif; }

/* ---------- FOOTER ---------- */
.footer{ border-top:1px solid var(--border); background:var(--surface); margin-top:40px; }
.foot-inner{ max-width:1020px; margin:0 auto; padding:16px 24px; display:flex;
  justify-content:space-between; gap:10px; flex-wrap:wrap;
  font:400 12.5px 'IBM Plex Sans',system-ui,sans-serif; color:var(--muted2); }
.foot-inner b{ font:600 14px 'Newsreader',Georgia,serif; color:var(--ink); }
.foot-inner a{ color:var(--accent-text); text-decoration:none; }

/* ---------- RESPONSIVE ---------- */
@media (max-width:640px){
  .wrap{ padding:30px 16px 16px; }
  .h1{ font-size:29px; }
  .nav-inner{ padding:10px 16px; }
  .search{ min-width:0; flex:1; }
  .detail{ grid-template-columns:1fr; }
  .nav-links{ order:10; width:100%; gap:14px; }
}
```

- [ ] **Step 3: Write `site/js/ui.js`**

```javascript
// Shared page chrome: theme toggling and small render helpers.

const THEME_KEY = "grant-radar.theme";

export function initTheme() {
  const btn = document.getElementById("theme-toggle");
  const root = document.documentElement;
  const apply = (dark) => {
    root.classList.toggle("dark", dark);
    if (btn) btn.textContent = dark ? "☀" : "☾";
  };
  apply(root.classList.contains("dark"));
  btn?.addEventListener("click", () => {
    const dark = !root.classList.contains("dark");
    apply(dark);
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
  });
}

export function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

const MONTHS = ["January","February","March","April","May","June",
  "July","August","September","October","November","December"];

export function fmtDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1].slice(0, 3)} ${d}, ${y}`;
}

export function fmtDateLong(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}
```

Note the head-of-page FOUC guard (used verbatim in every page Task 11–14):

```html
<script>(function(){var t=localStorage.getItem("grant-radar.theme");
if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))
document.documentElement.classList.add("dark");})()</script>
```

- [ ] **Step 4: Visual sanity check**

No page uses these yet; just confirm the CSS parses: open a scratch HTML or run:

```bash
node -e "const css=require('fs').readFileSync('site/style.css','utf8');
const open=(css.match(/{/g)||[]).length, close=(css.match(/}/g)||[]).length;
if(open!==close) throw new Error('brace mismatch '+open+'/'+close); console.log('css ok', open, 'rules-ish')"
```
Expected: `css ok …`.

- [ ] **Step 5: Commit**

```bash
git add site .gitignore
git commit -m "feat(site): design-system stylesheet and shared UI helpers"
```

---

### Task 10: Frontend logic module (pure, node-tested)

**Files:**
- Create: `site/js/logic.js`
- Test: `tests/js/logic.test.mjs`

**Interfaces:**
- Consumes: site payload items (Task 6 shape).
- Produces (exact exports, used by Tasks 11–13):
  - `DEFAULT_PROFILE = {ics:[...], codes:[...], keywords:[...]}`
  - `isOpportunity(item)`, `isNosi(item)`, `isCareer(item)`, `codesOf(item) -> string[]`
  - `weekMonday(iso) -> "YYYY-MM-DD"`, `weekLabel(mondayIso) -> "Week of July 27"`
  - `daysUntil(iso, todayIso) -> number` (can be negative)
  - `dueInfo(item, todayIso) -> {date, days, label} | null` (earliest future among due_dates then expiration; label "Next due" for receipt dates, "Closes" for expiration)
  - `matchReasons(item, profile) -> string[]`
  - `chipCounts(items, profile, savedSet, todayIso) -> object`
  - `applyChip(items, chip, profile, savedSet) -> items`
  - `searchFilter(items, query) -> items`
  - `closingSoon(items, profile, todayIso, n=5) -> items sorted by days`

- [ ] **Step 1: Write the failing tests**

`tests/js/logic.test.mjs`:

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_PROFILE, isOpportunity, isNosi, isCareer, weekMonday, weekLabel,
  daysUntil, dueInfo, matchReasons, applyChip, searchFilter, closingSoon,
} from "../../site/js/logic.js";

const TODAY = "2026-07-31";

const nosi = {
  notice_id: "NOT-AA-26-012", doctype: "NOT",
  title: "Notice of Special Interest (NOSI): Alcohol Use Among Older Adults",
  release_date: "2026-07-28", expiration_date: "2026-11-17",
  due_dates: [], activity_codes: [], primary_ic: "NIAAA",
  synopsis_truncated: "Drinking patterns and mortality in adults 50+.",
};
const par = {
  notice_id: "PAR-26-118", doctype: "PAR", title: "K01 in Aging Research",
  release_date: "2026-06-01", expiration_date: "2027-05-08",
  due_dates: [{ label: "Application receipt", date: "2026-10-12" }],
  activity_codes: ["K01"], primary_ic: "NIA", synopsis_truncated: "Career development.",
};
const policy = {
  notice_id: "NOT-OD-26-104", doctype: "NOT", title: "FORMS-J Required",
  release_date: "2026-07-27", due_dates: [], activity_codes: [], primary_ic: "OD",
};

test("classification", () => {
  assert.equal(isOpportunity(nosi), true);   // NOSI counts
  assert.equal(isNosi(nosi), true);
  assert.equal(isOpportunity(par), true);
  assert.equal(isNosi(par), false);
  assert.equal(isOpportunity(policy), false);
  assert.equal(isCareer(par), true);         // K01
  assert.equal(isCareer(nosi), false);
});

test("week helpers", () => {
  assert.equal(weekMonday("2026-07-31"), "2026-07-27"); // Friday -> that week's Monday
  assert.equal(weekMonday("2026-07-27"), "2026-07-27"); // Monday stays
  assert.equal(weekLabel("2026-07-27"), "Week of July 27");
});

test("daysUntil and dueInfo", () => {
  assert.equal(daysUntil("2026-08-12", TODAY), 12);
  assert.equal(daysUntil("2026-07-30", TODAY), -1);
  const d = dueInfo(par, TODAY);
  assert.deepEqual(d, { date: "2026-10-12", days: 73, label: "Next due" });
  const e = dueInfo(nosi, TODAY);
  assert.equal(e.label, "Closes");
  assert.equal(e.date, "2026-11-17");
  assert.equal(dueInfo(policy, TODAY), null);
  const past = { ...par, due_dates: [{ label: "x", date: "2026-01-01" }] };
  assert.equal(dueInfo(past, TODAY).date, "2027-05-08"); // skips past receipt, uses expiration
});

test("matchReasons needs two dimensions of evidence", () => {
  const profile = { ics: ["NIA", "NIAAA"], codes: ["K01", "R21"], keywords: ["alcohol", "aging"] };
  assert.deepEqual(matchReasons(par, profile), ["NIA", "K01", "aging"]);
  assert.deepEqual(matchReasons(nosi, profile), ["NIAAA", "alcohol"]);
  assert.deepEqual(matchReasons(policy, profile), []);
  assert.ok(DEFAULT_PROFILE.ics.includes("NIA"));
});

test("applyChip and searchFilter", () => {
  const items = [nosi, par, policy];
  const profile = DEFAULT_PROFILE;
  assert.deepEqual(applyChip(items, "nosi", profile, new Set()).map(i => i.notice_id), ["NOT-AA-26-012"]);
  assert.deepEqual(applyChip(items, "policy", profile, new Set()).map(i => i.notice_id), ["NOT-OD-26-104"]);
  assert.deepEqual(applyChip(items, "career", profile, new Set()).map(i => i.notice_id), ["PAR-26-118"]);
  assert.deepEqual(applyChip(items, "saved", profile, new Set(["PAR-26-118"])).map(i => i.notice_id), ["PAR-26-118"]);
  assert.equal(applyChip(items, "foryou", profile, new Set()).length >= 1, true);
  assert.deepEqual(searchFilter(items, "forms-j").map(i => i.notice_id), ["NOT-OD-26-104"]);
  assert.equal(searchFilter(items, "").length, 3);
});

test("closingSoon picks for-you items with future dates, soonest first", () => {
  const soon = closingSoon([nosi, par, policy], DEFAULT_PROFILE, TODAY, 5);
  assert.deepEqual(soon.map(i => i.notice_id), ["PAR-26-118", "NOT-AA-26-012"]);
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
node --test tests/js/
```
Expected: FAIL, cannot find module `site/js/logic.js`.

- [ ] **Step 3: Implement `site/js/logic.js`**

```javascript
// Pure data logic. No DOM access: everything here is node-testable.

export const DEFAULT_PROFILE = {
  ics: ["NIA", "NIAAA", "NICHD", "NIMHD"],
  codes: ["K01", "K99", "R03", "R21", "R01"],
  keywords: ["aging", "alcohol", "mortality", "demography", "life course",
    "disparities", "epidemiology"],
};

const OPP_DOCTYPES = new Set(["RFA", "PA", "PAR", "PAS"]);

export function isNosi(item) {
  return (item.title || "").startsWith("Notice of Special Interest");
}

export function isOpportunity(item) {
  return OPP_DOCTYPES.has(item.doctype) || isNosi(item);
}

export function codesOf(item) {
  const codes = item.activity_codes?.length ? item.activity_codes : (item.mechanisms || []);
  return codes || [];
}

export function isCareer(item) {
  return codesOf(item).some((c) => /^[KF]/.test(c));
}

const DAY = 86400000;

export function weekMonday(iso) {
  const d = new Date(iso + "T00:00:00Z");
  const shift = (d.getUTCDay() + 6) % 7; // Mon=0 ... Sun=6
  return new Date(d.getTime() - shift * DAY).toISOString().slice(0, 10);
}

const MONTHS = ["January","February","March","April","May","June",
  "July","August","September","October","November","December"];

export function weekLabel(mondayIso) {
  const [, m, d] = mondayIso.split("-").map(Number);
  return `Week of ${MONTHS[m - 1]} ${d}`;
}

export function daysUntil(iso, todayIso) {
  return Math.round((Date.parse(iso + "T00:00:00Z") - Date.parse(todayIso + "T00:00:00Z")) / DAY);
}

export function dueInfo(item, todayIso) {
  for (const d of item.due_dates || []) {
    if (d.date >= todayIso) {
      return { date: d.date, days: daysUntil(d.date, todayIso), label: "Next due" };
    }
  }
  const exp = item.expiration_date;
  if (isOpportunity(item) && exp && exp >= todayIso) {
    return { date: exp, days: daysUntil(exp, todayIso), label: "Closes" };
  }
  return null;
}

function haystack(item) {
  return [item.title, item.synopsis_truncated, item.purpose_tldr,
    (item.topics || []).join(" ")].filter(Boolean).join(" ").toLowerCase();
}

export function matchReasons(item, profile) {
  const reasons = [];
  const ics = new Set([item.primary_ic, item.parent_ic].filter(Boolean));
  for (const ic of profile.ics) if (ics.has(ic)) reasons.push(ic);
  const codes = new Set(codesOf(item));
  for (const c of profile.codes) if (codes.has(c)) reasons.push(c);
  const hay = haystack(item);
  for (const kw of profile.keywords) if (hay.includes(kw.toLowerCase())) reasons.push(kw);
  return reasons.length >= 2 ? reasons : [];
}

export function applyChip(items, chip, profile, savedSet) {
  switch (chip) {
    case "foryou": return items.filter((i) => matchReasons(i, profile).length > 0);
    case "opps": return items.filter((i) => isOpportunity(i) && !isNosi(i));
    case "nosi": return items.filter(isNosi);
    case "career": return items.filter(isCareer);
    case "policy": return items.filter((i) => !isOpportunity(i));
    case "saved": return items.filter((i) => savedSet.has(i.notice_id));
    default: return items;
  }
}

export function chipCounts(items, profile, savedSet) {
  const chips = ["all", "foryou", "opps", "nosi", "career", "policy", "saved"];
  return Object.fromEntries(chips.map((c) => [c, applyChip(items, c, profile, savedSet).length]));
}

export function searchFilter(items, query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return items;
  return items.filter((i) => (i.notice_id.toLowerCase() + " " + haystack(i)).includes(q));
}

export function closingSoon(items, profile, todayIso, n = 5) {
  return items
    .filter((i) => matchReasons(i, profile).length > 0)
    .map((i) => ({ item: i, due: dueInfo(i, todayIso) }))
    .filter((x) => x.due)
    .sort((a, b) => a.due.days - b.due.days)
    .slice(0, n)
    .map((x) => x.item);
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
node --test tests/js/
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add site/js/logic.js tests/js
git commit -m "feat(site): pure frontend logic with node tests"
```

---

### Task 11: Homepage — index.html, cards, controller

**Files:**
- Create: `site/index.html` (full replacement), `site/js/cards.js`, `site/js/index.js`

**Interfaces:**
- Consumes: `logic.js` (Task 10), `ui.js` (Task 9), staged `site/notices.json`.
- Produces: `cards.js` exports `renderCard(item, ctx) -> string` and `renderSoonRow(item, due) -> string` where `ctx = {profile, savedSet, todayIso, expanded:Set}`; Tasks 12 reuses `renderSoonRow`.

- [ ] **Step 1: Write `site/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grant Radar — this week in NIH funding</title>
  <meta name="description" content="NIH funding notices and opportunities, structured and summarized weekly.">
  <script>(function(){var t=localStorage.getItem("grant-radar.theme");
  if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))
  document.documentElement.classList.add("dark");})()</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
  <link rel="alternate" type="application/rss+xml" title="Grant Radar" href="feed.xml">
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a class="brand" href="index.html"><span class="ping"></span>Grant Radar</a>
      <div class="nav-links">
        <a href="index.html" class="active">This week</a>
        <a href="calendar.html">Calendar</a>
        <a href="trends.html">Trends</a>
        <a href="about.html">About</a>
      </div>
      <div class="nav-tools">
        <input class="search" id="search" placeholder="Search notices…" autocomplete="off">
        <button class="iconbtn" id="theme-toggle" aria-label="Toggle dark mode">☾</button>
        <a class="home-link" href="https://muntasirmasum.com">muntasirmasum.com ↗</a>
      </div>
    </div>
  </nav>

  <main class="wrap">
    <div class="eyebrow" id="page-eyebrow">NIH Guide</div>
    <h1 class="h1">This week in NIH funding</h1>
    <p class="lead" id="page-lead">Loading…</p>

    <section class="soon" id="soon" hidden>
      <div class="soon-label"><span>⏳ Closing soon · matches your profile</span>
        <a href="calendar.html">Full calendar →</a></div>
      <div id="soon-rows"></div>
    </section>

    <div class="chips" id="chips"></div>
    <div id="profile-editor-slot"></div>

    <div id="feed"></div>
    <p class="load-note" id="load-note" hidden>…scroll for earlier weeks…</p>
  </main>

  <footer class="footer">
    <div class="foot-inner">
      <span><b>Grant Radar</b> · by <a href="https://muntasirmasum.com">Muntasir Masum</a></span>
      <span>Data: <a href="https://grants.nih.gov/funding/searchguide/">NIH Guide</a> &amp;
        <a href="https://www.grants.gov">Grants.gov</a> · refreshed weekly ·
        <a href="feed.xml">RSS</a> ·
        <a href="https://github.com/muntasirmasum/grant-radar">GitHub</a></span>
    </div>
  </footer>

  <script type="module" src="js/index.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `site/js/cards.js`**

```javascript
import { esc, fmtDate } from "./ui.js";
import { codesOf, dueInfo, isOpportunity, matchReasons } from "./logic.js";

function duePill(item, todayIso) {
  const due = dueInfo(item, todayIso);
  if (!due) return "";
  const hot = due.days <= 30 ? " due--hot" : "";
  return `<span class="due${hot}">${due.label} ${esc(fmtDate(due.date))}</span>`;
}

function metaLine(item) {
  const kind = item.title?.startsWith("Notice of Special Interest") ? "NOSI"
    : (isOpportunity(item) ? item.doctype : "Policy");
  const org = item.primary_ic || (item.issuing_orgs || [])[0] || "NIH";
  return `${esc(kind)} · ${esc(org)} <span class="meta-id">${esc(item.notice_id)}</span>`;
}

function detailBlock(item) {
  if (!item.dos?.length && !item.donts?.length && !item.key_dates?.length) return "";
  const list = (title, cls, entries) => entries?.length
    ? `<div class="${cls}"><h6>${title}</h6><ul>${entries.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>`
    : "";
  const dates = item.key_dates?.length
    ? `<div><h6>Key dates</h6><ul>${item.key_dates.map((k) =>
        `<li>${esc(k.label)}: ${esc(fmtDate(k.date))}</li>`).join("")}</ul></div>`
    : "";
  return `<div class="detail">${list("Do", "do", item.dos)}${list("Don't", "dont", item.donts)}${dates}</div>`;
}

export function renderCard(item, ctx) {
  const { profile, savedSet, todayIso, expanded } = ctx;
  const gold = isOpportunity(item) ? "" : " card--gold";
  const body = item.purpose_tldr
    ? `<p class="tldr"><b>TL;DR</b>${esc(item.purpose_tldr)}</p>`
    : (item.synopsis_truncated
      ? `<p class="syn"><b>Synopsis</b>${esc(item.synopsis_truncated)}</p>` : "");
  const compact = !body ? " card--compact" : "";
  const reasons = matchReasons(item, profile);
  const foryou = reasons.length
    ? `<div class="foryou"><i></i>For you <em>· matches ${esc(reasons.join(" · "))}</em></div>` : "";
  const pills = codesOf(item).map((c) => `<span class="pill">${esc(c)}</span>`).join("");
  const topics = (item.topics || []).map((t) => `<span class="pill pill--gold">${esc(t)}</span>`).join("");
  const cash = item.award_ceiling
    ? `<span class="pill pill--gold">≤ $${esc(Number(item.award_ceiling).toLocaleString("en-US"))}</span>` : "";
  const saved = savedSet.has(item.notice_id);
  const isOpen = expanded.has(item.notice_id);
  const hasDetail = Boolean(item.dos?.length || item.donts?.length || item.key_dates?.length);
  const actions = `<span class="actions">
      <button data-save="${esc(item.notice_id)}" class="${saved ? "saved" : ""}"
        aria-label="Save for later">${saved ? "♥ saved" : "♡"}</button>
      ${hasDetail ? `<button data-expand="${esc(item.notice_id)}">${isOpen ? "Collapse ▴" : "Details ▾"}</button>` : ""}
      <a href="${esc(item.url)}" target="_blank" rel="noopener">NIH ↗</a>
    </span>`;
  const pillrow = `<div class="pillrow">${duePill(item, todayIso)}${pills}${topics}${cash}${actions}</div>`;
  return `<article class="card${gold}${compact}" data-id="${esc(item.notice_id)}">
    <div class="meta">${metaLine(item)}</div>
    <h2 class="title"><a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.title)}</a></h2>
    ${body}${foryou}${isOpen ? detailBlock(item) : ""}${pillrow}
  </article>`;
}

export function renderSoonRow(item, due) {
  const mid = due.days > 30 ? " days--mid" : "";
  const org = item.primary_ic || (item.issuing_orgs || [])[0] || "NIH";
  return `<div class="soon-row">
    <div class="days${mid}">${due.days}<small>DAYS</small></div>
    <div><div class="soon-title"><a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.title)}</a></div>
    <div class="soon-meta">${esc(item.doctype)} · ${esc(org)} · ${esc(due.label.toLowerCase())} ${esc(fmtDate(due.date))}</div></div>
  </div>`;
}
```

- [ ] **Step 3: Write `site/js/index.js`**

```javascript
import { initTheme, fmtDateLong } from "./ui.js";
import {
  DEFAULT_PROFILE, applyChip, chipCounts, closingSoon, dueInfo,
  searchFilter, weekLabel, weekMonday,
} from "./logic.js";
import { renderCard, renderSoonRow } from "./cards.js";

const PROFILE_KEY = "grant-radar.profile.v2";
const SAVED_KEY = "grant-radar.saved.v1";
const WEEKS_PER_PAGE = 4;

const state = {
  items: [],
  chip: "all",
  query: "",
  weeksShown: WEEKS_PER_PAGE,
  expanded: new Set(),
  todayIso: new Date().toISOString().slice(0, 10),
  profile: loadJSON(PROFILE_KEY) || DEFAULT_PROFILE,
  savedSet: new Set(loadJSON(SAVED_KEY) || []),
};

function loadJSON(key) {
  try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
}

function save(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

const CHIP_LABELS = [["all", "All"], ["foryou", "For you"], ["opps", "Opportunities"],
  ["nosi", "NOSIs"], ["career", "Career K/F"], ["policy", "Policy"], ["saved", "♡ Saved"]];

function visibleItems() {
  return searchFilter(applyChip(state.items, state.chip, state.profile, state.savedSet), state.query);
}

function renderChips() {
  const counts = chipCounts(searchFilter(state.items, state.query), state.profile, state.savedSet);
  document.getElementById("chips").innerHTML = CHIP_LABELS.map(([id, label]) =>
    `<button class="chip${state.chip === id ? " chip--on" : ""}" data-chip="${id}">
      ${label} <span class="n">${counts[id]}</span></button>`).join("")
    + `<button class="chip" data-edit-profile>Edit profile</button>`;
}

function renderSoon() {
  const soon = closingSoon(state.items, state.profile, state.todayIso, 5);
  const box = document.getElementById("soon");
  box.hidden = soon.length === 0;
  document.getElementById("soon-rows").innerHTML = soon.map((i) =>
    renderSoonRow(i, dueInfo(i, state.todayIso))).join("");
}

function renderFeed() {
  const ctx = { profile: state.profile, savedSet: state.savedSet,
    todayIso: state.todayIso, expanded: state.expanded };
  const groups = new Map();
  for (const item of visibleItems()) {
    const wk = weekMonday(item.release_date || state.todayIso);
    if (!groups.has(wk)) groups.set(wk, []);
    groups.get(wk).push(item);
  }
  const weeks = [...groups.keys()].sort().reverse().slice(0, state.weeksShown);
  document.getElementById("feed").innerHTML = weeks.map((wk) =>
    `<div class="week"><span>${weekLabel(wk)}</span></div>` +
    groups.get(wk).map((i) => renderCard(i, ctx)).join("")).join("")
    || `<p class="load-note">Nothing matches — clear the search or switch chips.</p>`;
  document.getElementById("load-note").hidden = weeks.length >= groups.size;
}

function renderAll() {
  renderChips();
  renderSoon();
  renderFeed();
}

function renderProfileEditor() {
  const slot = document.getElementById("profile-editor-slot");
  const p = state.profile;
  slot.innerHTML = `<div class="profile-editor">
    <label for="pf-ics">Institutes (codes, comma-separated)</label>
    <input id="pf-ics" value="${p.ics.join(", ")}">
    <label for="pf-codes">Activity codes</label>
    <input id="pf-codes" value="${p.codes.join(", ")}">
    <label for="pf-kw">Keywords</label>
    <input id="pf-kw" value="${p.keywords.join(", ")}">
    <div class="row">
      <button class="btn" id="pf-save">Save profile</button>
      <button class="btn btn--ghost" id="pf-reset">Reset to default</button>
      <button class="btn btn--ghost" id="pf-close">Close</button>
    </div></div>`;
  const parse = (id) => document.getElementById(id).value
    .split(",").map((s) => s.trim()).filter(Boolean);
  document.getElementById("pf-save").onclick = () => {
    state.profile = { ics: parse("pf-ics"), codes: parse("pf-codes"), keywords: parse("pf-kw") };
    save(PROFILE_KEY, state.profile);
    slot.innerHTML = "";
    renderAll();
  };
  document.getElementById("pf-reset").onclick = () => {
    state.profile = DEFAULT_PROFILE;
    localStorage.removeItem(PROFILE_KEY);
    slot.innerHTML = "";
    renderAll();
  };
  document.getElementById("pf-close").onclick = () => { slot.innerHTML = ""; };
}

function wireEvents() {
  document.getElementById("chips").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-chip]");
    if (chip) { state.chip = chip.dataset.chip; state.weeksShown = WEEKS_PER_PAGE; renderAll(); }
    if (e.target.closest("[data-edit-profile]")) renderProfileEditor();
  });
  document.getElementById("feed").addEventListener("click", (e) => {
    const saveBtn = e.target.closest("[data-save]");
    if (saveBtn) {
      const id = saveBtn.dataset.save;
      state.savedSet.has(id) ? state.savedSet.delete(id) : state.savedSet.add(id);
      save(SAVED_KEY, [...state.savedSet]);
      renderAll();
    }
    const expandBtn = e.target.closest("[data-expand]");
    if (expandBtn) {
      const id = expandBtn.dataset.expand;
      state.expanded.has(id) ? state.expanded.delete(id) : state.expanded.add(id);
      renderFeed();
    }
  });
  let timer;
  document.getElementById("search").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.query = e.target.value;
      state.weeksShown = WEEKS_PER_PAGE;
      renderAll();
    }, 200);
  });
  new IntersectionObserver((entries) => {
    if (entries.some((en) => en.isIntersecting)) {
      state.weeksShown += WEEKS_PER_PAGE;
      renderFeed();
    }
  }).observe(document.getElementById("load-note"));
}

async function boot() {
  initTheme();
  try {
    const resp = await fetch("notices.json");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const payload = await resp.json();
    state.items = payload.items || [];
    const newest = state.items.filter((i) => weekMonday(i.release_date || "1900-01-01")
      === weekMonday(state.todayIso)).length;
    document.getElementById("page-eyebrow").textContent =
      `NIH Guide · Week of ${fmtDateLong(weekMonday(state.todayIso)).replace(/, \d+$/, "")}`;
    const stamp = payload.generated_at ? new Date(payload.generated_at).toLocaleString() : "unknown";
    const foryou = applyChip(state.items, "foryou", state.profile, state.savedSet).length;
    document.getElementById("page-lead").textContent =
      `${state.items.length} items tracked · ${newest} new this week · ${foryou} match your profile · refreshed ${stamp}`;
    wireEvents();
    renderAll();
  } catch (err) {
    document.getElementById("feed").innerHTML =
      `<div class="error-card"><strong>Couldn't load the data file.</strong><br>
       ${err.message}. Try reloading; if it persists the weekly refresh may have failed —
       <a href="https://github.com/muntasirmasum/grant-radar/actions">check the Actions log</a>.</div>`;
    document.getElementById("page-lead").textContent = "Data unavailable.";
  }
}

boot();
```

- [ ] **Step 4: Manual verification**

```bash
cd ~/projects/grant-radar
cp data/notices.json site/notices.json 2>/dev/null || echo '{"generated_at":null,"items":[]}' > site/notices.json
python3 -m http.server 8080 --directory site
```

Open `http://localhost:8080`. Verify: navbar renders with fonts, theme toggle flips and persists across reload, chips render with counts, cards show (the existing 120-item data has old-schema items — cards must render without errors even though most lack `doctype`; policy/gold styling applies via `isOpportunity` returning false), search filters, save heart toggles and survives reload. Note the full data only appears after Task 16's first real refresh. Fix anything broken before committing.

- [ ] **Step 5: Frontend logic tests still pass**

```bash
node --test tests/js/
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add site
git commit -m "feat(site): editorial digest homepage with closing-soon, chips, profile"
```

---

### Task 12: Calendar page

**Files:**
- Create: `site/calendar.html`, `site/js/calendar.js`

**Interfaces:**
- Consumes: `logic.js`, `ui.js`, `cards.js#renderSoonRow`.
- Produces: nothing consumed later.

- [ ] **Step 1: Write `site/calendar.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grant Radar — deadline calendar</title>
  <script>(function(){var t=localStorage.getItem("grant-radar.theme");
  if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))
  document.documentElement.classList.add("dark");})()</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a class="brand" href="index.html"><span class="ping"></span>Grant Radar</a>
      <div class="nav-links">
        <a href="index.html">This week</a>
        <a href="calendar.html" class="active">Calendar</a>
        <a href="trends.html">Trends</a>
        <a href="about.html">About</a>
      </div>
      <div class="nav-tools">
        <button class="iconbtn" id="theme-toggle" aria-label="Toggle dark mode">☾</button>
        <a class="home-link" href="https://muntasirmasum.com">muntasirmasum.com ↗</a>
      </div>
    </div>
  </nav>

  <main class="wrap">
    <div class="eyebrow">Upcoming due dates</div>
    <h1 class="h1">Deadline calendar</h1>
    <p class="lead">Every still-open opportunity with a future receipt or expiration date, whenever it was first announced.</p>
    <div class="chips" id="cal-chips">
      <button class="chip chip--on" data-scope="all">All deadlines</button>
      <button class="chip" data-scope="foryou">For you</button>
    </div>
    <div id="calendar"></div>
  </main>

  <footer class="footer">
    <div class="foot-inner">
      <span><b>Grant Radar</b> · by <a href="https://muntasirmasum.com">Muntasir Masum</a></span>
      <span>Data: NIH Guide &amp; Grants.gov · refreshed weekly · <a href="feed.xml">RSS</a></span>
    </div>
  </footer>

  <script type="module" src="js/calendar.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `site/js/calendar.js`**

```javascript
import { initTheme } from "./ui.js";
import { DEFAULT_PROFILE, dueInfo, matchReasons } from "./logic.js";
import { renderSoonRow } from "./cards.js";

const PROFILE_KEY = "grant-radar.profile.v2";
const MONTHS = ["January","February","March","April","May","June",
  "July","August","September","October","November","December"];

let items = [];
let scope = "all";
const todayIso = new Date().toISOString().slice(0, 10);
let profile = DEFAULT_PROFILE;
try { profile = JSON.parse(localStorage.getItem(PROFILE_KEY)) || DEFAULT_PROFILE; } catch {}

function render() {
  const withDue = items
    .map((i) => ({ item: i, due: dueInfo(i, todayIso) }))
    .filter((x) => x.due)
    .filter((x) => scope === "all" || matchReasons(x.item, profile).length > 0)
    .sort((a, b) => a.due.date.localeCompare(b.due.date));
  const byMonth = new Map();
  for (const x of withDue) {
    const key = x.due.date.slice(0, 7);
    if (!byMonth.has(key)) byMonth.set(key, []);
    byMonth.get(key).push(x);
  }
  document.getElementById("calendar").innerHTML = [...byMonth.entries()].map(([ym, rows]) => {
    const [y, m] = ym.split("-").map(Number);
    return `<h2 class="cal-month">${MONTHS[m - 1]} ${y}</h2>` +
      rows.map((x) => `<div class="cal-row">${renderSoonRow(x.item, x.due).replace(/^<div class="soon-row">|<\/div>$/g, "")}</div>`).join("");
  }).join("") || `<p class="load-note">No upcoming deadlines in this view.</p>`;
}

async function boot() {
  initTheme();
  document.getElementById("cal-chips").addEventListener("click", (e) => {
    const b = e.target.closest("[data-scope]");
    if (!b) return;
    scope = b.dataset.scope;
    for (const chip of e.currentTarget.querySelectorAll(".chip"))
      chip.classList.toggle("chip--on", chip === b);
    render();
  });
  try {
    const payload = await (await fetch("notices.json")).json();
    items = payload.items || [];
    render();
  } catch {
    document.getElementById("calendar").innerHTML =
      `<div class="error-card">Couldn't load the data file.</div>`;
  }
}

boot();
```

- [ ] **Step 3: Manual verification**

With the Task 11 server still running, open `http://localhost:8080/calendar.html`. With old-schema data most items lack due dates, so expect a sparse list (possibly only "No upcoming deadlines"); the layout, chips, and theme toggle must work. Full verification happens after Task 16's refresh.

- [ ] **Step 4: Commit**

```bash
git add site/calendar.html site/js/calendar.js
git commit -m "feat(site): deadline calendar page"
```

---

### Task 13: Trends page

**Files:**
- Create: `site/trends.html`, `site/js/trends.js`

**Interfaces:**
- Consumes: `logic.js` (`weekMonday`, `isOpportunity`, `codesOf`, `dueInfo`), Observable Plot CDN globals (`Plot`, `d3`).
- Produces: nothing consumed later.

- [ ] **Step 1: Write `site/trends.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grant Radar — trends</title>
  <script>(function(){var t=localStorage.getItem("grant-radar.theme");
  if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))
  document.documentElement.classList.add("dark");})()</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a class="brand" href="index.html"><span class="ping"></span>Grant Radar</a>
      <div class="nav-links">
        <a href="index.html">This week</a>
        <a href="calendar.html">Calendar</a>
        <a href="trends.html" class="active">Trends</a>
        <a href="about.html">About</a>
      </div>
      <div class="nav-tools">
        <button class="iconbtn" id="theme-toggle" aria-label="Toggle dark mode">☾</button>
        <a class="home-link" href="https://muntasirmasum.com">muntasirmasum.com ↗</a>
      </div>
    </div>
  </nav>

  <main class="wrap">
    <div class="eyebrow">Structure of the stream</div>
    <h1 class="h1">Trends</h1>
    <p class="lead">Computed from structured fields only; no LLM involved.</p>
    <div class="chart-card"><h3>Items per week (last 12 weeks)</h3><div id="chart-volume"></div></div>
    <div class="chart-card"><h3>Most active institutes (last 90 days)</h3><div id="chart-ics"></div></div>
    <div class="chart-card"><h3>Activity codes among open opportunities</h3><div id="chart-codes"></div></div>
  </main>

  <footer class="footer">
    <div class="foot-inner">
      <span><b>Grant Radar</b> · by <a href="https://muntasirmasum.com">Muntasir Masum</a></span>
      <span>Data: NIH Guide &amp; Grants.gov · refreshed weekly · <a href="feed.xml">RSS</a></span>
    </div>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"
    integrity="sha384-CjloA8y00+1SDAUkjs099PVfnY2KmDC2BZnws9kh8D/lX1s46w6EPhpXdqMfjK6i"
    crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.17/dist/plot.umd.min.js"
    integrity="sha384-JUpn2GgRr0gxU0xOBd8D8P634jhRCwobtG8G2MMEkX1RnGJ7/FJNnuukpfT+H2w1"
    crossorigin="anonymous"></script>
  <script type="module" src="js/trends.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `site/js/trends.js`**

```javascript
import { initTheme } from "./ui.js";
import { codesOf, dueInfo, isOpportunity, weekMonday } from "./logic.js";

/* global Plot */

const todayIso = new Date().toISOString().slice(0, 10);

function accent() {
  return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
}

function textColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
}

function draw(items) {
  const style = { background: "transparent", color: textColor(), fontFamily: "'IBM Plex Sans',sans-serif" };
  const cutoffWeek = new Date(Date.now() - 12 * 7 * 86400000).toISOString().slice(0, 10);
  const weekly = d3.rollups(
    items.filter((i) => (i.release_date || "") >= cutoffWeek),
    (v) => v.length, (i) => weekMonday(i.release_date)).map(([week, n]) => ({ week, n }));
  document.getElementById("chart-volume").replaceChildren(Plot.plot({
    style, height: 220, x: { label: null, tickFormat: (w) => w.slice(5) }, y: { label: "items", grid: true },
    marks: [Plot.barY(weekly, { x: "week", y: "n", fill: accent(), rx: 3 })],
  }));

  const cutoff90 = new Date(Date.now() - 90 * 86400000).toISOString().slice(0, 10);
  const ics = d3.rollups(
    items.filter((i) => (i.release_date || "") >= cutoff90 && i.primary_ic),
    (v) => v.length, (i) => i.primary_ic)
    .sort((a, b) => b[1] - a[1]).slice(0, 10).map(([ic, n]) => ({ ic, n }));
  document.getElementById("chart-ics").replaceChildren(Plot.plot({
    style, height: 260, marginLeft: 70, x: { label: "items", grid: true }, y: { label: null },
    marks: [Plot.barX(ics, { y: "ic", x: "n", fill: accent(), rx: 3, sort: { y: "-x" } })],
  }));

  const codes = d3.rollups(
    items.filter((i) => isOpportunity(i) && dueInfo(i, todayIso)).flatMap((i) => codesOf(i)),
    (v) => v.length, (c) => c)
    .sort((a, b) => b[1] - a[1]).slice(0, 10).map(([code, n]) => ({ code, n }));
  document.getElementById("chart-codes").replaceChildren(Plot.plot({
    style, height: 260, marginLeft: 60, x: { label: "open opportunities", grid: true }, y: { label: null },
    marks: [Plot.barX(codes, { y: "code", x: "n", fill: accent(), rx: 3, sort: { y: "-x" } })],
  }));
}

async function boot() {
  initTheme();
  try {
    const payload = await (await fetch("notices.json")).json();
    draw(payload.items || []);
    document.getElementById("theme-toggle").addEventListener("click", () =>
      draw(payload.items || []));
  } catch {
    document.getElementById("chart-volume").innerHTML =
      `<div class="error-card">Couldn't load the data file.</div>`;
  }
}

boot();
```

- [ ] **Step 3: Manual verification**

Open `http://localhost:8080/trends.html`. Three charts render from the staged data (weekly volume works with old-schema items; IC chart may be sparse until refresh backfills `primary_ic`). Toggle dark mode: charts redraw with readable colors.

- [ ] **Step 4: Commit**

```bash
git add site/trends.html site/js/trends.js
git commit -m "feat(site): trends page with Observable Plot charts"
```

---

### Task 14: About page

**Files:**
- Create: `site/about.html` (full replacement of the old file's content)

**Interfaces:** consumes `ui.js` only.

- [ ] **Step 1: Write `site/about.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grant Radar — about</title>
  <script>(function(){var t=localStorage.getItem("grant-radar.theme");
  if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))
  document.documentElement.classList.add("dark");})()</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a class="brand" href="index.html"><span class="ping"></span>Grant Radar</a>
      <div class="nav-links">
        <a href="index.html">This week</a>
        <a href="calendar.html">Calendar</a>
        <a href="trends.html">Trends</a>
        <a href="about.html" class="active">About</a>
      </div>
      <div class="nav-tools">
        <button class="iconbtn" id="theme-toggle" aria-label="Toggle dark mode">☾</button>
        <a class="home-link" href="https://muntasirmasum.com">muntasirmasum.com ↗</a>
      </div>
    </div>
  </nav>

  <main class="wrap prose">
    <div class="eyebrow">About</div>
    <h1 class="h1">What Grant Radar is</h1>
    <p>The NIH Guide publishes dozens of funding notices every week: dense, verbose, and
    easy to miss. Grant Radar reads the stream once, structures it, and presents it in a
    form a researcher can scan in minutes: real opportunities with deadlines up front,
    administrative chatter demoted, and a profile filter that knows what you work on.</p>

    <h2>Where the data comes from</h2>
    <p>Every Sunday evening a GitHub Action pulls structured records from the official
    <a href="https://grants.nih.gov/funding/searchguide/">NIH Guide search API</a> and joins
    each funding opportunity to <a href="https://www.grants.gov">Grants.gov</a> for its
    synopsis, award ceiling, and close date. No scraping, no keys, no server; the site you
    are reading is static files on GitHub Pages.</p>

    <h2>About the TL;DR blocks</h2>
    <p>Cards with a purple <strong>TL;DR</strong> block have been summarized with an LLM
    (Claude) and reviewed by me; the summaries also add do/don't lists for applicants.
    Cards showing a grey <strong>Synopsis</strong> carry the official Grants.gov purpose
    text verbatim. Everything else on a card — dates, institutes, activity codes — comes
    straight from the structured sources, never from the model.</p>

    <h2>Who built it</h2>
    <p>
    <a href="https://muntasirmasum.com">Muntasir Masum</a>. I study aging, alcohol use,
    and mortality, and built this to stop losing Friday afternoons to the Guide. The code
    is open at <a href="https://github.com/muntasirmasum/grant-radar">github.com/muntasirmasum/grant-radar</a>;
    subscribe via <a href="feed.xml">RSS</a> if you want the weekly stream in your reader.</p>
  </main>

  <footer class="footer">
    <div class="foot-inner">
      <span><b>Grant Radar</b> · by <a href="https://muntasirmasum.com">Muntasir Masum</a></span>
      <span>Data: NIH Guide &amp; Grants.gov · refreshed weekly · <a href="feed.xml">RSS</a> ·
        <a href="https://github.com/muntasirmasum/grant-radar">GitHub</a></span>
    </div>
  </footer>

  <script type="module">
    import { initTheme } from "./js/ui.js";
    initTheme();
  </script>
</body>
</html>
```

- [ ] **Step 2: Manual verification**

Open `http://localhost:8080/about.html` — prose styles, links, dark mode.

- [ ] **Step 3: Commit**

```bash
git add site/about.html
git commit -m "feat(site): about page"
```

---

### Task 15: Rewrite `/refresh-tldrs` for the new pipeline

**Files:**
- Modify: `.claude/commands/refresh-tldrs.md` (full replacement)

**Interfaces:**
- Consumes: item JSON files, `pipeline/refresh.py --emit-only` (Task 7), taxonomy topics (Task 1).
- Produces: enriched item files; no code artifacts.

- [ ] **Step 1: Replace the file content entirely with:**

````markdown
---
description: Fill in LLM-extracted fields (TL;DRs, do's/don'ts, topics) for items the API refresh can't summarize. Uses your Claude subscription, not the API.
---

You are completing the enrichment step of the `grant-radar` pipeline. The
weekly refresh has already filled every structured field from the NIH Guide
and Grants.gov APIs. Your job is the free-text fields only.

# Ownership rules (do not violate)

- You may write ONLY: `purpose_tldr`, `eligibility_tldr`, `budget`,
  `mechanisms`, `career_stages`, `topics`, `dos`, `donts`,
  `strategic_priorities`, `llm_model`, `enriched_at`.
- Never edit pipeline-owned fields (`title`, dates, `activity_codes`,
  `synopsis`, `award_*`, `url`, ...). The refresh will not touch your
  fields either — that contract goes both ways.

# Workflow

## 1. Build the queue

```sh
python3 - <<'EOF'
import json, pathlib
items = [json.loads(p.read_text()) for p in pathlib.Path("data/notices").glob("*/*.json")]
queue = [i for i in items if not i.get("purpose_tldr")]
# Priority: profile matches, then nearest due date, then newest.
PROFILE_ICS = {"NIA", "NIAAA", "NICHD", "NIMHD"}
def key(i):
    matches = i.get("primary_ic") in PROFILE_ICS
    due = i.get("next_due_date") or i.get("expiration_date") or "9999"
    return (not matches, due, i.get("release_date") or "")
for i in sorted(queue, key=key)[:40]:
    year = (i.get("release_date") or "1900")[:4]
    print(f"{i['notice_id']}\tdata/notices/{year}/{i['notice_id']}.json\t{i.get('next_due_date') or i.get('expiration_date') or '-'}")
print(f"-- {len(queue)} total in queue")
EOF
```

If the queue is empty, stop.

## 2. For each item, in order

a. **Get the text.** Prefer `data/raw/nih/<year>/<id>.html` (Read tool). If
   absent, fetch `url` from the item JSON (WebFetch). For opportunities the
   item's `synopsis` field is also good input.

b. **Extract.** Produce exactly these keys — faithful to the notice, no
   invented figures, `null` where unstated, summaries 2-3 plain sentences:

```json
{
  "purpose_tldr": "...",
  "eligibility_tldr": "...",
  "budget": {"direct_cost_cap": null, "total_cost_cap": null, "project_period_max": null},
  "mechanisms": ["R01"],
  "career_stages": ["any"],
  "topics": ["aging"],
  "dos": ["..."],
  "donts": ["..."],
  "strategic_priorities": []
}
```

- `career_stages` from: trainee, early_career, midcareer, established, any.
- `topics` from the keys of `data/taxonomy.json` `topics`; 0-4 tags.
- For administrative notices, 1-2 dos/donts suffice.

c. **Apply.** Edit the item JSON directly with the Edit tool: add your keys
   plus `"llm_model": "claude-via-claude-code"` and
   `"enriched_at": "<current UTC ISO>"`. Keep JSON valid, 2-space indented,
   keys sorted (match the file's existing style).

## 3. Every 10 items, checkpoint

```sh
python3 -m pipeline.refresh --emit-only
git add data/
git commit -m "data: LLM enrichment batch ($(date -u +%Y-%m-%d))"
```

## 4. When done

```sh
python3 -m pipeline.refresh --emit-only
git add data/
git commit -m "data: LLM enrichment complete ($(date -u +%Y-%m-%d))" || true
git push
```
````

- [ ] **Step 2: Verify the queue script runs**

```bash
cd ~/projects/grant-radar && python3 - <<'EOF'
import json, pathlib
items = [json.loads(p.read_text()) for p in pathlib.Path("data/notices").glob("*/*.json")]
print(len([i for i in items if not i.get("purpose_tldr")]), "in queue")
EOF
```
Expected: a count ≈ existing item total minus 1.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/refresh-tldrs.md
git commit -m "docs: rewrite /refresh-tldrs for API pipeline and ownership contract"
```

---

### Task 16: First real refresh, README, NEXT.md, deploy

**Files:**
- Modify: `README.md` (full replacement), `NEXT.md` (full replacement)
- Data: first live run of the pipeline

**Interfaces:** consumes everything.

- [ ] **Step 1: Run the real refresh locally**

```bash
cd ~/projects/grant-radar
pip install -r pipeline/requirements.txt
python3 -m pipeline.refresh --days 45
```

`--days 45` covers the gap since the cron died (June 22 → today). Expected output: `fetched=... written=... site_items=...` with several hundred written items (active FOA backlog + missed weeks). Spot-check three things:

```bash
python3 - <<'EOF'
import json
p = json.load(open("data/notices.json"))
items = p["items"]
opps = [i for i in items if i.get("doctype") in ("RFA","PA","PAR","PAS")]
withsyn = [i for i in opps if i.get("synopsis_truncated")]
print("site items:", len(items), "| opportunities:", len(opps), "| with synopsis:", len(withsyn))
hl = json.load(open("data/notices/2026/NOT-HL-26-005.json"))
assert hl["purpose_tldr"], "anti-clobber FAILED on the surviving enriched notice!"
print("enriched notice survived ✓")
EOF
```

If the Grants.gov join returns few synopses, debug `fetch_detail` against a real PAR number before continuing (`python3 -c "import requests; from pipeline.grants_gov import fetch_detail; print(fetch_detail(requests.Session(),'PAR-25-221'))"`).

- [ ] **Step 2: View the real site locally**

```bash
cp data/notices.json site/notices.json
cp data/feed.xml site/feed.xml
python3 -m http.server 8080 --directory site
```

Check against the mockup (`docs/superpowers/specs/2026-07-31-grant-radar-revision-mockup.html`): closing-soon strip populated, purple/gold split sensible, calendar has months of deadlines, trends charts populated, RSS validates (`curl -s localhost:8080/feed.xml | python3 -c "import sys,xml.etree.ElementTree as ET; ET.fromstring(sys.stdin.read()); print('rss ok')"`).

- [ ] **Step 3: Replace `README.md`**

```markdown
# grant-radar

**Live: <https://muntasirmasum.github.io/grant-radar/>**

A weekly radar for NIH funding. Every Sunday a GitHub Action pulls structured
records from the official NIH Guide search API, joins funding opportunities to
Grants.gov for synopses, award ceilings, and close dates, and publishes a
static editorial digest: real opportunities with deadline countdowns up front,
policy chatter demoted, and a client-side profile that ranks what matters to
you.

## Architecture

```
NIH Guide API ─┐
               ├─ pipeline/refresh.py ── data/notices/<yr>/<id>.json  (one file per item)
Grants.gov  ───┘        │
                        ├── data/notices.json   (site payload)
                        └── data/feed.xml       (RSS)
                                 │
                    pages-deploy stages both into site/ → GitHub Pages
```

- **Anti-clobber contract:** the refresh only writes structured fields. LLM
  fields (`purpose_tldr`, `dos`, `donts`, ...) are added manually by running
  `/refresh-tldrs` in Claude Code and are never overwritten.
- **Site:** plain HTML/CSS/JS in `site/`, no build step. Design system shared
  with [muntasirmasum.com](https://muntasirmasum.com).

## Local development

```sh
pip install -r pipeline/requirements.txt pytest
python -m pytest pipeline/tests          # pipeline tests
node --test tests/js/                    # frontend logic tests

python -m pipeline.refresh               # real refresh (writes data/)
cp data/notices.json data/feed.xml site/
python -m http.server 8080 --directory site
```

## Enrichment

Open the repo in Claude Code and run `/refresh-tldrs`. It walks every item
missing a `purpose_tldr` (profile matches and nearest deadlines first), writes
the LLM-owned fields, and rebuilds the site payload with
`python -m pipeline.refresh --emit-only`.

## License

MIT.
```

- [ ] **Step 4: Replace `NEXT.md`**

```markdown
# Where we left off — 2026-07-31

## State

- Full revision shipped: editorial digest UI (muntasirmasum.com design system)
  + Python API pipeline (NIH Guide + Grants.gov). Spec:
  `docs/superpowers/specs/2026-07-31-grant-radar-revision-design.md`.
- R package, Quarto remnants, and parquet are gone (git history has them).
- Weekly cron refreshes structured data; `/refresh-tldrs` remains the manual,
  free enrichment step and can never be clobbered by the cron.

## To resume

```sh
cd ~/projects/grant-radar && git pull
python -m pytest pipeline/tests && node --test tests/js/
```

## Open items, ranked

1. Run `/refresh-tldrs` for the current profile-matched queue.
2. Watch the next two Sunday crons (Actions tab); first unattended runs.
3. Link Grant Radar from muntasirmasum.com (studio/tools page).
4. Later (spec §10): NSF/AHRQ sources, automated enrichment, OG images,
   per-item permalinks.
```

- [ ] **Step 5: Commit and push everything**

```bash
git add -A
git commit -m "feat: first API refresh + README/NEXT for the revision"
git push
```

- [ ] **Step 6: Verify CI end-to-end**

```bash
gh run watch --repo muntasirmasum/grant-radar --exit-status || gh run list --repo muntasirmasum/grant-radar --limit 5
gh workflow run weekly-refresh --repo muntasirmasum/grant-radar
sleep 90 && gh run list --repo muntasirmasum/grant-radar --workflow weekly-refresh --limit 1
```

Expected: `ci` green (pytest + node), the manually dispatched `weekly-refresh` green in ~1 minute, `pages-deploy` green after it. Then open <https://muntasirmasum.github.io/grant-radar/> and confirm the live site matches local.

- [ ] **Step 7: Done marker**

Update the checkboxes in this plan file, commit:

```bash
git add docs/superpowers/plans/2026-07-31-grant-radar-revision.md
git commit -m "docs: mark revision plan executed"
git push
```

---

## Self-review notes (kept for the record)

- Spec §4.1 "first 4 weeks render immediately; older weeks on scroll" → Task 11 `WEEKS_PER_PAGE`/IntersectionObserver. Spec §4.2 three card states → `renderCard` branches. §4.3 tokens → Task 9 CSS. §4.4 profile/matching → Tasks 10–11. §5.x pipeline → Tasks 2–7. §5.5 CI → Task 8. §6 → Task 15. §7 failure behavior → two-phase `run()` + error cards. §8 tests → Tasks 2–7, 10. §9 cleanup → Tasks 1, 16. §10 deferred → nothing here builds it.
- Emission lives in `data/` and is staged into `site/` by pages-deploy (existing pattern, keeps `site/` source-only); this refines spec §5.4's "site/notices.json" wording — same artifact, staged at deploy.
- Type consistency spot-checks: `dueInfo` shape `{date, days, label}` used in cards/calendar; `renderSoonRow(item, due)` matches both call sites; `merge_item` tuple unpacked consistently; `--emit-only` flag name identical in Task 7 CLI, Task 15 command, README.
```
