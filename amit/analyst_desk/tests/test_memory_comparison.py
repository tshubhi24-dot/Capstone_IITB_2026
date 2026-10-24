"""Historical values stay separate from current source truth; all data invented."""
from copy import deepcopy

import pytest

from desk.memory_comparison import compare_approved_note
from desk.store import canonical_hash
from test_store_data import source


def record(**changes):
    row = {"ticker": "TEST", "year": 2025, "revenue": "300", "operating_income": "90", "margin_pct": "30.00",
           "period_start": "2025-01-01", "period_end": "2025-12-31", "unit": "USD", "fact_ids": ["old-rev", "old-op"]}
    row.update(changes)
    payload = {"metrics": [row], "source_fingerprint": "0" * 64}
    return {"id": "a" * 32, "payload": payload, "payload_hash": canonical_hash(payload)}


def test_comparison_uses_current_verified_inputs_and_cites_immutable_history(source):
    old = record()
    result = compare_approved_note(old, source)
    row = result["comparisons"][0]
    assert row["status"] == "compared" and row["current_source_verified"]
    assert row["prior"]["margin_pct"] == "30.00" and row["current"]["margin_pct"] == "33.33"
    assert row["change"]["margin_percentage_points"] == "3.33"
    assert row["change"]["operating_income_usd"] == "10"
    assert row["current"]["fact_ids"] == ["rev", "op"]
    assert row["prior_note_citation"] == "note:" + old["id"] + "@" + old["payload_hash"]
    assert result["archive_only"] and result["generative_model_calls"] == 0


@pytest.mark.parametrize("change", [{"unit": "EUR"}, {"period_start": "2025-02-01"}])
def test_different_dates_or_units_do_not_produce_change_claims(source, change):
    row = compare_approved_note(record(**change), source)["comparisons"][0]
    assert row["status"] == "not_comparable" and "change" not in row


@pytest.mark.parametrize("change", [{"margin_pct": "99"}, {"revenue": "NaN"}, {"revenue": "0"}, {"year": 2022}])
def test_bad_historical_inputs_are_explicitly_unavailable(source, change):
    row = compare_approved_note(record(**change), source)["comparisons"][0]
    assert row["status"] == "unavailable" and "change" not in row


def test_changed_note_cannot_be_used_as_an_approved_record(source):
    old = record(); old["payload"]["metrics"][0]["revenue"] = "999"
    with pytest.raises(ValueError, match="changed"):
        compare_approved_note(old, source)
