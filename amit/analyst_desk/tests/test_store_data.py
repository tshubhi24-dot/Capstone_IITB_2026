"""Independent boundary checks for evidence and publication, using invented data."""
import json

import pytest

from desk.data import Corpus
from desk.store import Store, canonical_hash


@pytest.fixture
def source(tmp_path):
    common = {"ticker": "TEST", "fiscal_year": 2025, "start": "2025-01-01", "end": "2025-12-31", "unit": "USD", "accession": "test-only"}
    document = {"companies": [{"ticker": "TEST"}], "facts": [
        {**common, "id": "rev", "concept": "revenue", "value": 300},
        {**common, "id": "op", "concept": "operating_income", "value": 100}],
        "passages": [{"id": "p", "ticker": "TEST", "year": 2025, "item": "1A", "text": "Invented test-only disclosure."}]}
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(document))
    return Corpus(path)


def test_decimal_verifier_rejects_altered_numbers_and_periods(source):
    row = {"ticker": "TEST", "year": 2025, "fact_ids": ["rev", "op"], "revenue": "300", "operating_income": "100", "margin_pct": "33.33", "period_start": "2025-01-01", "period_end": "2025-12-31", "unit": "USD"}
    assert source.verify_row(row)
    for key, value in (("margin_pct", "33.34"), ("revenue", "301"), ("period_end", "2025-12-30"), ("unit", "EUR"), ("ticker", "OTHER")):
        assert not source.verify_row({**row, key: value})
    assert not source.verify_row({**row, "fact_ids": ["op", "rev"]})


@pytest.mark.parametrize("field,value", [("unit", "EUR"), ("accession", "other"), ("end", "2025-03-31"), ("ticker", "OTHER")])
def test_calculator_inputs_cannot_mix_incompatible_facts(source, field, value):
    source._facts["op"][field] = value
    with pytest.raises(ValueError, match="Incompatible"):
        source.canonical_pair("rev", "op")


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_source_amounts_cannot_verify(source, amount):
    source._facts["op"]["value"] = amount
    with pytest.raises(ValueError, match="finite"):
        source.canonical_pair("rev", "op")


def test_publication_requires_approved_exact_payload_and_is_idempotent(tmp_path):
    store = Store(tmp_path / "state.sqlite", secret="test-only-signing-secret-" * 3)
    run = store.create_run({"question": "Test only"})
    payload = {"run_id": run["id"], "actor": "local-analyst", "body": "Reviewed test-only note"}
    digest = canonical_hash(payload)
    with pytest.raises(ValueError):
        store.make_capability(run["id"], "local-analyst", digest)
    run.update(pending={"kind": "note", "payload": payload}, draft=payload, critic={"passed": False})
    store.save_run(run)
    with pytest.raises(ValueError, match="failed"):
        store.record_approval(run["id"], "local-analyst", digest)
    run["critic"]["passed"] = True
    store.save_run(run)
    store.record_approval(run["id"], "local-analyst", digest)
    capability = store.make_capability(run["id"], "local-analyst", digest)
    with pytest.raises(ValueError):
        store.publish({**payload, "body": "Changed"}, capability)
    with pytest.raises(ValueError):
        store.publish(payload, capability + "0")
    receipt = store.publish(payload, capability)
    assert not receipt["idempotent"]
    assert store.publish(payload, capability)["idempotent"]
    assert len(Store(tmp_path / "state.sqlite", secret=store.secret).notes()) == 1


def test_expired_and_invalidated_approvals_cannot_publish(tmp_path):
    store = Store(tmp_path, secret="test-only-signing-secret-" * 3)
    run = store.create_run({})
    payload = {"run_id": run["id"], "actor": run["actor"], "body": "Test"}
    digest = canonical_hash(payload)
    run.update(pending={"kind": "note", "payload": payload}, critic={"passed": True})
    store.save_run(run)
    store.record_approval(run["id"], run["actor"], digest, ttl=-1)
    with pytest.raises(ValueError, match="No current"):
        store.make_capability(run["id"], run["actor"], digest)
    store.record_approval(run["id"], run["actor"], digest)
    capability = store.make_capability(run["id"], run["actor"], digest)
    store.invalidate_approval(run["id"])
    with pytest.raises(ValueError, match="missing"):
        store.publish(payload, capability)
    assert store.notes() == []
