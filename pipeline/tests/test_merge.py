import pytest

from pipeline.merge import LLM_OWNED, merge_item, validate_item, dumps_item

NOW = "2026-07-31T12:00:00Z"


def incoming(**over):
    base = {
        "notice_id": "NOT-AA-26-012", "source": "nih", "doctype": "NOT",
        "title": "Notice of Special Interest (NOSI): Alcohol Use Among Older Adults",
        "release_date": "2026-07-28", "open_date": None, "expiration_date": "2026-11-17",
        "due_dates": [], "next_due_date": None, "activity_codes": [],
        "primary_ic": "NIAAA", "parent_ic": "NIH",
        "issuing_orgs": ["National Institute on Alcohol Abuse and Alcoholism"],
        "url": "https://grants.nih.gov/grants/guide/notice-files/NOT-AA-26-012.html",
        "clinical_trials": None,
    }
    base.update(over)
    return base


def test_new_item_gets_created_with_updated_at():
    merged, changed = merge_item(None, incoming(), NOW)
    assert changed is True
    assert merged["updated_at"] == NOW
    assert merged["title"].startswith("Notice of Special Interest")


def test_llm_fields_survive_refresh():
    enriched = {**incoming(), "purpose_tldr": "Summary.", "dos": ["do x"],
                "mechanisms": ["R21"], "llm_model": "claude", "updated_at": "2026-05-01T00:00:00Z"}
    fresh = incoming(title="Notice of Special Interest (NOSI): Alcohol Use Among Older Adults v2")
    merged, changed = merge_item(enriched, fresh, NOW)
    assert changed is True
    assert merged["title"].endswith("v2")
    assert merged["purpose_tldr"] == "Summary."
    assert merged["dos"] == ["do x"]
    assert merged["mechanisms"] == ["R21"]


def test_incoming_llm_keys_are_ignored_even_if_present():
    bad = {**incoming(), "purpose_tldr": "PIPELINE MUST NOT WRITE THIS"}
    merged, _ = merge_item(None, bad, NOW)
    assert "purpose_tldr" not in merged


def test_unchanged_data_is_a_noop_and_byte_stable():
    merged1, _ = merge_item(None, incoming(), NOW)
    merged2, changed = merge_item(merged1, incoming(), "2026-08-07T12:00:00Z")
    assert changed is False
    assert merged2["updated_at"] == NOW  # not bumped
    assert dumps_item(merged2) == dumps_item(merged1)


def test_unknown_existing_fields_are_preserved():
    existing, _ = merge_item(None, incoming(), NOW)
    existing["key_dates"] = [{"label": "Release Date", "date": "2026-07-28", "type": "release"}]
    existing["raw_html_hash"] = "abc123"
    merged, _ = merge_item(existing, incoming(), NOW)
    assert merged["key_dates"][0]["date"] == "2026-07-28"
    assert merged["raw_html_hash"] == "abc123"


def test_topics_hybrid_seed_only_when_absent():
    merged, _ = merge_item(None, {**incoming(), "topics": ["alcohol"]}, NOW)
    assert merged["topics"] == ["alcohol"]
    refreshed, _ = merge_item(merged, {**incoming(), "topics": ["alcohol", "aging"]}, NOW)
    assert refreshed["topics"] == ["alcohol"]  # already set -> untouched


def test_none_incoming_values_do_not_erase_existing():
    existing, _ = merge_item(None, incoming(expiration_date="2026-11-17"), NOW)
    merged, changed = merge_item(existing, incoming(expiration_date=None), "2026-08-07T00:00:00Z")
    assert merged["expiration_date"] == "2026-11-17"
    assert changed is False


def test_validate_rejects_bad_items():
    ok, _ = merge_item(None, incoming(), NOW)
    validate_item(ok)  # no raise
    with pytest.raises(ValueError, match="NOT-AA-26-012"):
        validate_item({**ok, "release_date": "07/28/2026"})
    with pytest.raises(ValueError, match="title"):
        validate_item({**ok, "title": ""})
    with pytest.raises(ValueError, match="notice_id"):
        validate_item({k: v for k, v in ok.items() if k != "notice_id"})
