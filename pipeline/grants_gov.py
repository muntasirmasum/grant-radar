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
_SPACE_PUNCT = _re.compile(r"\s+([.,:;!?)])")


def _strip_html(text):
    if not text:
        return None
    text = _TAG.sub(" ", text)
    text = _html.unescape(text)
    text = _WS.sub(" ", text).strip()
    # Remove spaces before closing punctuation only
    text = _SPACE_PUNCT.sub(r'\1', text)
    return text or None


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
