"""Fetch and normalize items from the NIH Guide search API."""
from __future__ import annotations

import re as _re

GUIDE_API = "https://search.grants.nih.gov/guide/api/data"
GUIDE_URL_SUBDIR = {"NOT": "notice-files", "RFA": "rfa-files", "PA": "pa-files", "PAR": "pa-files", "PAS": "pa-files"}
# The Guide API reliably serves only its UI's native page size; larger values
# are clamped or return truncated windows beyond the first page (verified
# empirically 2026-08-01: size=100 yielded 112/412 active items; size=25 yields all 412).
PAGE_SIZE = 25
_DATE_PREFIX = _re.compile(r"^\d{4}-\d{2}-\d{2}")


def _iso_date(value):
    """'2026-07-28T09:00:00.000Z' -> '2026-07-28'; None for absent or non-date text."""
    if not value or not isinstance(value, str):
        return None
    m = _DATE_PREFIX.match(value)
    return m.group(0) if m else None


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
        "nih_file_listed": bool(source.get("filename")),
        "clinical_trials": source.get("clinicaltrials"),
    }


import datetime as _dt

TIMEOUT = 30
MAX_PAGES = 300  # hard stop; 300 * PAGE_SIZE (25) = 7,500 items > entire Guide


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
        rel = _iso_date(src.get("reldate"))
        if rel and rel < cutoff:
            break
        out.append(src)
    return out


def fetch_active(session):
    return list(_pages(session, {"type": "active"}))
