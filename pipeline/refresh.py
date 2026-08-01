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
    stats = {"fetched": 0, "written": 0, "unchanged": 0, "html_skipped": 0}

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
            enriched = _backfill_primary_ic(_seed_topics(dict(merged), topics_map), institutes)
            if enriched != merged:
                merged = enriched
                merged["updated_at"] = now_iso
                changed = True

            if changed or old is None:
                to_write[docnum] = merged
            else:
                stats["unchanged"] += 1
            merged_all[docnum] = merged

            if docnum in recent_ids and old is None and not merged.get("purpose_tldr"):
                try:
                    html_cache[docnum] = fetch_html(session, merged["url"])
                except Exception:
                    stats["html_skipped"] += 1  # page not published yet (or transient); enrichment fetches live later

        # legacy backfill pass for items the APIs no longer return
        for nid, item in merged_all.items():
            if nid not in to_write:
                fixed = _backfill_primary_ic(dict(item), institutes)
                if fixed != item:
                    fixed["updated_at"] = now_iso
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
        old_path = existing.get(nid, (None, None))[1]
        if old_path and old_path.resolve() != path.resolve():
            old_path.unlink()

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
          f"unchanged={stats['unchanged']} html_skipped={stats['html_skipped']} "
          f"site_items={len(payload['items'])}")
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
