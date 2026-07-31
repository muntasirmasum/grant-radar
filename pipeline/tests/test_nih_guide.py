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
