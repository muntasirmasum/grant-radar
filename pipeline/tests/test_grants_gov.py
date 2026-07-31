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


def test_strip_html_preserves_opening_quotes():
    # Regression test: opening quotes should keep their preceding space
    assert _strip_html('He explained the term <i>"population health"</i>.') == 'He explained the term "population health".'
