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


def test_rss_descriptions_from_raw_synopsis_and_rfc822_dates():
    long = "word " * 200
    rss = build_rss([item("NOT-1", synopsis=long)], GEN)
    root = ET.fromstring(rss)
    itm = root.find("./channel/item")
    desc = itm.find("description").text
    assert desc  # non-empty
    assert desc.endswith("…")
    pubdate = itm.find("pubDate").text
    # RFC822 format contains either "GMT" or "+0000" or similar timezone notation
    assert pubdate.endswith("+0000") or "GMT" in pubdate
    lastbuild = root.find("./channel/lastBuildDate").text
    assert lastbuild.endswith("+0000") or "GMT" in lastbuild


def test_rss_tie_ordering_by_notice_id_ascending():
    items = [item("B", release="2026-07-28"), item("A", release="2026-07-28")]
    rss = build_rss(items, GEN)
    root = ET.fromstring(rss)
    rss_items = root.findall("./channel/item")
    assert len(rss_items) == 2
    guids = [itm.find("guid").text for itm in rss_items]
    assert guids == ["A", "B"]
