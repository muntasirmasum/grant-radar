import datetime as dt
import json
from pathlib import Path

from pipeline import refresh
from pipeline.nih_guide import normalize


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


def test_truly_unchanged_second_run_writes_nothing(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2026").mkdir(parents=True)
    (root / "data/taxonomy.json").write_text(json.dumps(
        {"institutes": {"NIA": "National Institute on Aging"}, "topics": {}}))

    recent = [guide_src("NOT-AA-26-050", "2026-07-15T00:00:00.000Z")]
    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: recent)
    monkeypatch.setattr(refresh, "fetch_active", lambda s: [])
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: None)
    monkeypatch.setattr(refresh, "fetch_html", lambda s, url: "<html></html>")

    stats1 = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)
    assert stats1["written"] >= 1
    path = root / "data/notices/2026/NOT-AA-26-050.json"
    before = path.read_text()

    stats2 = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)
    after = path.read_text()

    assert stats2["written"] == 0
    assert before == after


def test_seed_only_change_persists_to_disk_and_survives_emit_only(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2026").mkdir(parents=True)
    institutes = {"NIA": "National Institute on Aging"}
    topics = {"aging": ["aging", "older adult"]}
    (root / "data/taxonomy.json").write_text(json.dumps(
        {"institutes": institutes, "topics": topics}))

    source = {"docnum": "NOT-AG-26-777", "reldate": "2026-07-10T00:00:00.000Z",
              "doctype": "NOT", "title": "Research on Aging Populations",
              "organization": {"parent": "NIH", "primary": "NIA"},
              "filename": "NOT-AG-26-777.html", "expdate": None, "ac": ""}

    # On-disk item whose pipeline fields exactly match what normalize() will
    # recompute for `source` (so merge_item alone reports unchanged), but
    # which lacks `topics` even though the title matches a taxonomy keyword.
    existing_item = normalize(source, institutes)
    existing_item["updated_at"] = "2020-01-01T00:00:00Z"
    (root / "data/notices/2026/NOT-AG-26-777.json").write_text(json.dumps(existing_item))

    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: [source])
    monkeypatch.setattr(refresh, "fetch_active", lambda s: [])
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: None)
    monkeypatch.setattr(refresh, "fetch_html", lambda s, url: "<html></html>")

    stats = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)

    on_disk = json.loads((root / "data/notices/2026/NOT-AG-26-777.json").read_text())
    assert on_disk["topics"] == ["aging"]
    assert on_disk["updated_at"] != "2020-01-01T00:00:00Z"
    assert stats["written"] >= 1

    # A fresh --emit-only run must not regress the seeded topics.
    refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14, emit_only=True)
    payload = json.loads((root / "data/notices.json").read_text())
    item = next(i for i in payload["items"] if i["notice_id"] == "NOT-AG-26-777")
    assert item["topics"] == ["aging"]


def test_year_change_migrates_file_and_removes_stale_copy(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2025").mkdir(parents=True)
    (root / "data/taxonomy.json").write_text(json.dumps({"institutes": {}, "topics": {}}))

    old_path = root / "data/notices/2025/NOT-X.json"
    old_path.write_text(json.dumps({
        "notice_id": "NOT-X", "source": "nih", "doctype": "NOT", "title": "Title NOT-X",
        "release_date": "2025-12-30",
        "url": "https://grants.nih.gov/grants/guide/notice-files/NOT-X.html"}))

    source = guide_src("NOT-X", "2026-01-02T00:00:00.000Z")
    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: [source])
    monkeypatch.setattr(refresh, "fetch_active", lambda s: [])
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: None)
    monkeypatch.setattr(refresh, "fetch_html", lambda s, url: "<html></html>")

    refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)

    new_path = root / "data/notices/2026/NOT-X.json"
    assert new_path.exists()
    assert json.loads(new_path.read_text())["release_date"] == "2026-01-02"
    assert not old_path.exists()


def test_html_fetch_failure_is_non_fatal_and_counted(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2026").mkdir(parents=True)
    (root / "data/taxonomy.json").write_text(json.dumps({"institutes": {}, "topics": {}}))

    recent = [guide_src("NOT-AA-26-070", "2026-07-20T00:00:00.000Z"),
              guide_src("NOT-AA-26-071", "2026-07-21T00:00:00.000Z")]
    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: recent)
    monkeypatch.setattr(refresh, "fetch_active", lambda s: [])
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: None)

    def flaky_fetch_html(session, url):
        if "NOT-AA-26-070" in url:
            raise RuntimeError("404")  # NIH hasn't published the HTML yet
        return "<html>ok</html>"

    monkeypatch.setattr(refresh, "fetch_html", flaky_fetch_html)

    stats = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)

    assert (root / "data/notices/2026/NOT-AA-26-070.json").exists()
    assert (root / "data/notices/2026/NOT-AA-26-071.json").exists()
    assert not (root / "data/raw/nih/2026/NOT-AA-26-070.html").exists()
    assert (root / "data/raw/nih/2026/NOT-AA-26-071.html").read_text() == "<html>ok</html>"
    assert stats["html_skipped"] == 1


def test_grants_gov_canonical_url_when_nih_file_unlisted(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2026").mkdir(parents=True)
    (root / "data/taxonomy.json").write_text(json.dumps({"institutes": {}, "topics": {}}))

    unlisted = guide_src("PAR-26-200", "2026-07-05T00:00:00.000Z", doctype="PAR",
                          exp="2027-01-01T00:00:00.000Z")
    unlisted["filename"] = None  # NIH Guide API omitted the file: page not published yet
    listed = guide_src("PAR-26-201", "2026-07-06T00:00:00.000Z", doctype="PAR",
                        exp="2027-01-01T00:00:00.000Z")

    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: [])
    monkeypatch.setattr(refresh, "fetch_active", lambda s: [unlisted, listed])

    def fake_detail(s, docnum):
        gg_id = 357021 if docnum == "PAR-26-200" else 357022
        return {"grants_gov_id": gg_id, "synopsis": "Detail.", "award_ceiling": None,
                "award_floor": None, "close_date": None}

    monkeypatch.setattr(refresh, "fetch_detail", fake_detail)
    monkeypatch.setattr(refresh, "fetch_html", lambda s, url: "<html></html>")

    refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)

    unlisted_on_disk = json.loads((root / "data/notices/2026/PAR-26-200.json").read_text())
    assert unlisted_on_disk["url"] == "https://www.grants.gov/search-results-detail/357021"

    listed_on_disk = json.loads((root / "data/notices/2026/PAR-26-201.json").read_text())
    assert listed_on_disk["url"].startswith("https://grants.nih.gov/")


def test_url_heal_is_durable_across_runs(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2026").mkdir(parents=True)
    (root / "data/taxonomy.json").write_text(json.dumps({"institutes": {}, "topics": {}}))

    unlisted = guide_src("PAR-26-300", "2026-07-05T00:00:00.000Z", doctype="PAR",
                          exp="2027-01-01T00:00:00.000Z")
    unlisted["filename"] = None
    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: [])
    monkeypatch.setattr(refresh, "fetch_active", lambda s: [unlisted])
    monkeypatch.setattr(refresh, "fetch_html", lambda s, url: "<html></html>")
    path = root / "data/notices/2026/PAR-26-300.json"

    # Run 1: Grants.gov succeeds -> url heals.
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: {
        "grants_gov_id": 357099, "synopsis": "S1", "award_ceiling": None,
        "award_floor": None, "close_date": None})
    refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)
    healed = json.loads(path.read_text())
    assert healed["url"] == "https://www.grants.gov/search-results-detail/357099"
    healed_bytes = path.read_text()

    # Run 2: Grants.gov returns an ordinary soft miss (None). The healed url must
    # NOT latch back to the broken NIH guess, and the file must not even be rewritten.
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: None)
    refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)
    assert json.loads(path.read_text())["url"] == "https://www.grants.gov/search-results-detail/357099"
    assert path.read_text() == healed_bytes

    # Run 3: Grants.gov succeeds again. Still stable, still zero churn.
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: {
        "grants_gov_id": 357099, "synopsis": "S1", "award_ceiling": None,
        "award_floor": None, "close_date": None})
    stats3 = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)
    assert stats3["written"] == 0
    assert path.read_text() == healed_bytes


def test_fetch_detail_failure_is_non_fatal_and_retries_next_run(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2026").mkdir(parents=True)
    (root / "data/taxonomy.json").write_text(json.dumps({"institutes": {}, "topics": {}}))

    failing = guide_src("PAR-26-400", "2026-07-05T00:00:00.000Z", doctype="PAR",
                         exp="2027-01-01T00:00:00.000Z")
    failing["filename"] = None  # NIH page unpublished; only Grants.gov can heal this one
    ok = guide_src("PAR-26-401", "2026-07-06T00:00:00.000Z", doctype="PAR",
                    exp="2027-01-01T00:00:00.000Z")

    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: [])
    monkeypatch.setattr(refresh, "fetch_active", lambda s: [failing, ok])
    monkeypatch.setattr(refresh, "fetch_html", lambda s, url: "<html></html>")

    def flaky_detail(s, docnum):
        if docnum == "PAR-26-400":
            raise RuntimeError("502")  # Grants.gov transient failure, not a 404
        return {"grants_gov_id": 357555, "synopsis": "S", "award_ceiling": None,
                "award_floor": None, "close_date": None}

    monkeypatch.setattr(refresh, "fetch_detail", flaky_detail)

    stats = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)

    assert stats["detail_failed"] == 1
    failing_path = root / "data/notices/2026/PAR-26-400.json"
    ok_path = root / "data/notices/2026/PAR-26-401.json"
    assert failing_path.exists()
    assert ok_path.exists()

    failing_item = json.loads(failing_path.read_text())
    assert failing_item["url"].startswith("https://grants.nih.gov/")
    assert not failing_item.get("grants_gov_id")

    # Next run: Grants.gov answers this time. needs_detail must still be True
    # (grants_gov_id was never captured), so the item gets another chance and heals.
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: {
        "grants_gov_id": 357556, "synopsis": "S2", "award_ceiling": None,
        "award_floor": None, "close_date": None})
    refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)
    healed = json.loads(failing_path.read_text())
    assert healed["url"] == "https://www.grants.gov/search-results-detail/357556"


def test_two_successful_detail_runs_produce_no_churn(tmp_path, monkeypatch):
    root = tmp_path
    (root / "data" / "notices" / "2026").mkdir(parents=True)
    (root / "data/taxonomy.json").write_text(json.dumps({"institutes": {}, "topics": {}}))

    unlisted = guide_src("PAR-26-500", "2026-07-05T00:00:00.000Z", doctype="PAR",
                          exp="2027-01-01T00:00:00.000Z")
    unlisted["filename"] = None
    monkeypatch.setattr(refresh, "fetch_recent", lambda s, days, today: [])
    monkeypatch.setattr(refresh, "fetch_active", lambda s: [unlisted])
    monkeypatch.setattr(refresh, "fetch_html", lambda s, url: "<html></html>")
    monkeypatch.setattr(refresh, "fetch_detail", lambda s, n: {
        "grants_gov_id": 357700, "synopsis": "S", "award_ceiling": None,
        "award_floor": None, "close_date": None})

    stats1 = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)
    assert stats1["written"] == 1
    path = root / "data/notices/2026/PAR-26-500.json"
    before = path.read_text()

    stats2 = refresh.run(root=root, session=None, today=dt.date(2026, 7, 31), days=14)
    assert stats2["written"] == 0
    assert path.read_text() == before
