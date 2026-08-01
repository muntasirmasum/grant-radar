import json
from pathlib import Path

from pipeline.nih_guide import normalize

FIX = Path(__file__).parent / "fixtures"
INSTITUTES = {"NIAAA": "National Institute on Alcohol Abuse and Alcoholism"}


def load(name):
    return json.loads((FIX / name).read_text())


def test_normalize_active_rfa():
    item = normalize(load("guide_active_rfa.json"), INSTITUTES)
    assert item["notice_id"] == "RFA-OH-22-006"
    assert item["source"] == "nih"
    assert item["doctype"] == "RFA"
    assert item["release_date"] == "2022-06-28"
    assert item["open_date"] == "2022-07-29"
    assert item["expiration_date"] == "2028-01-31"
    assert item["due_dates"] == [{"label": "Last application receipt", "date": "2028-01-30"}]
    assert item["next_due_date"] == "2028-01-30"
    assert item["activity_codes"] == ["T03"]
    assert item["primary_ic"] == "NIOSH"
    assert item["parent_ic"] == "CDC"
    assert item["issuing_orgs"] == ["NIOSH"]  # not in institutes map -> code passthrough
    assert item["url"] == "https://grants.nih.gov/grants/guide/rfa-files/RFA-OH-22-006.html"
    assert item["clinical_trials"] == "Not_Allowed"


def test_normalize_notice_maps_org_name_and_handles_empty_ac():
    item = normalize(load("guide_notice.json"), INSTITUTES)
    assert item["notice_id"] == "NOT-AA-26-012"
    assert item["doctype"] == "NOT"
    assert item["activity_codes"] == []
    assert item["due_dates"] == []
    assert item["next_due_date"] is None
    assert item["expiration_date"] == "2026-11-17"
    assert item["issuing_orgs"] == ["National Institute on Alcohol Abuse and Alcoholism"]
    assert item["url"] == "https://grants.nih.gov/grants/guide/notice-files/NOT-AA-26-012.html"


def test_normalize_par_uses_pa_files_subdir():
    src = load("guide_active_rfa.json")
    src["docnum"] = "PAR-26-118"
    src["doctype"] = "PAR"
    src["filename"] = "PAR-26-118.html"
    item = normalize(src, INSTITUTES)
    assert item["url"] == "https://grants.nih.gov/grants/guide/pa-files/PAR-26-118.html"


def test_normalize_due_dates_ordering_with_both_lard_and_receipt():
    """Test that due_dates sorts two entries in ascending date order."""
    src = load("guide_active_rfa.json")
    # Set lard earlier than appreceiptdate to test sorting
    src["appreceiptdate"] = "2028-01-30T00:00:00.000Z"
    src["lard"] = "2028-01-25T00:00:00.000Z"
    item = normalize(src, INSTITUTES)
    assert len(item["due_dates"]) == 2
    assert item["due_dates"][0]["date"] == "2028-01-25"
    assert item["due_dates"][0]["label"] == "Last application receipt"
    assert item["due_dates"][1]["date"] == "2028-01-30"
    assert item["due_dates"][1]["label"] == "Application receipt"
    assert item["next_due_date"] == "2028-01-25"


def test_normalize_due_dates_dedup_when_lard_equals_receipt():
    """Test that duplicate due dates (lard == appreceiptdate) yield single entry."""
    src = load("guide_active_rfa.json")
    src["appreceiptdate"] = "2028-01-30T00:00:00.000Z"
    src["lard"] = "2028-01-30T00:00:00.000Z"
    item = normalize(src, INSTITUTES)
    assert len(item["due_dates"]) == 1
    assert item["due_dates"][0]["label"] == "Application receipt"
    assert item["due_dates"][0]["date"] == "2028-01-30"
    assert item["next_due_date"] == "2028-01-30"


def test_normalize_missing_filename_uses_docnum_fallback():
    """Test that missing filename key falls back to {docnum}.html."""
    src = load("guide_active_rfa.json")
    del src["filename"]
    item = normalize(src, INSTITUTES)
    assert item["url"] == "https://grants.nih.gov/grants/guide/rfa-files/RFA-OH-22-006.html"


def test_normalize_malformed_short_dates_return_none():
    """Test that malformed/short date strings return None."""
    src = load("guide_active_rfa.json")
    src["reldate"] = "2026"  # too short
    src["opendate"] = ""     # empty string
    item = normalize(src, INSTITUTES)
    assert item["release_date"] is None
    assert item["open_date"] is None


def test_normalize_notice_asserts_none_passthrough_and_fields():
    """Verify that notice fixture None fields pass through and other fields are correct."""
    item = normalize(load("guide_notice.json"), INSTITUTES)
    # Existing assertions on fields already tested
    assert item["notice_id"] == "NOT-AA-26-012"
    assert item["doctype"] == "NOT"
    # Now assert the None passthrough fields
    assert item["open_date"] is None
    assert item["clinical_trials"] is None
    # And the mapped/passthrough IC fields
    assert item["primary_ic"] == "NIAAA"
    assert item["parent_ic"] == "NIH"
    # And the title field
    assert item["title"] == "Notice of Special Interest (NOSI): Alcohol Use Among Older Adults"


def test_normalize_freetext_appreceiptdate_without_valid_lard():
    """Test free-text appreceiptdate (e.g. 'Multiple dates...') with no valid lard yields empty due_dates."""
    src = load("guide_active_rfa.json")
    src["appreceiptdate"] = "Multiple dates, see announcement."
    src["lard"] = None
    item = normalize(src, INSTITUTES)
    assert item["due_dates"] == []
    assert item["next_due_date"] is None


def test_normalize_freetext_appreceiptdate_with_valid_lard():
    """Test free-text appreceiptdate with valid lard yields one due_dates entry for lard only."""
    src = load("guide_active_rfa.json")
    src["appreceiptdate"] = "Multiple dates, see announcement."
    src["lard"] = "2027-01-07T00:00:00.000Z"
    item = normalize(src, INSTITUTES)
    assert len(item["due_dates"]) == 1
    assert item["due_dates"][0]["label"] == "Last application receipt"
    assert item["due_dates"][0]["date"] == "2027-01-07"
    assert item["next_due_date"] == "2027-01-07"
