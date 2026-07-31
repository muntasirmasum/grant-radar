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
