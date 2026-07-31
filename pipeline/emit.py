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
