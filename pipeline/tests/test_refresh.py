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
