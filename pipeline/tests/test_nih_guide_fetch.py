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
