"""Synthetic operator verification stays separate from all analyst records."""
import json

import pytest

from desk.development import public_cases
from desk.store import Store
from ops.verify_lessons_runtime import ACTOR, FIXTURE_KIND, verify


@pytest.fixture
def source_path(tmp_path):
    case = next(row for row in public_cases() if row["case_id"] == "KDEV001")
    source = {"companies": [{"ticker": ticker, "company": ticker + " invented test issuer", "sector": "Test"} for ticker in case["tickers"]],
              "facts": [{"id": f"{ticker}-{year}", "ticker": ticker, "fiscal_year": year} for ticker in case["tickers"] for year in case["years"]],
              "passages": [{"id": "invented-passage", "ticker": case["tickers"][0], "year": case["years"][0], "item": "1A", "text": "Invented operator test source."}]}
    path = tmp_path / "source.json"; path.write_text(json.dumps(source))
    return path


def test_three_phases_preserve_real_analyst_records_and_publish_aggregate_only_receipts(tmp_path, source_path):
    runtime = tmp_path / "runtime"
    real = Store(runtime / "portal.sqlite", secret="invented-real-fixture-signing-" * 3)
    real.create_run({"question": "Unrelated fictional analyst request"})
    with real.connection() as db:
        db.execute("INSERT INTO notes VALUES(?,?,?,?,?,?)", ("a" * 32, "b" * 32, "local-analyst", "c" * 64,
                                                           json.dumps({"body": "Unrelated fictional approved note"}), 1))
    before = {"runs": real.list_runs(), "notes": real.notes()}
    for phase in ("prepare", "inspect", "cleanup"):
        receipt = verify(phase, runtime_dir=runtime, corpus_path=source_path)
        assert receipt["status"] == "passed" and receipt["checks_passed"] == receipt["checks_total"]
        assert receipt["fixture_kind"] == FIXTURE_KIND
        assert receipt["human_decisions_submitted"] == receipt["generative_model_calls"] == receipt["real_research_runs_created"] == 0
        assert not receipt["real_analyst_namespace_touched"]
        serialized = json.dumps(receipt)
        assert "Unrelated fictional" not in serialized and "lesson_id" not in serialized and "question" not in serialized
        assert real.list_runs() == before["runs"] and real.notes() == before["notes"]
    operator = Store(runtime / "lesson-operator/portal.sqlite")
    assert len(operator.list_runs(ACTOR)) == 1 and operator.list_runs("local-analyst") == []
    with operator.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM store WHERE prefix=?", ("analyst." + ACTOR + ".lesson-decisions",)).fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM store WHERE prefix=?", ("analyst." + ACTOR + ".lesson-revocations",)).fetchone()[0] == 1


def test_inspection_requires_prepared_persistent_fixture(tmp_path, source_path):
    with pytest.raises(ValueError, match="Prepare"):
        verify("inspect", runtime_dir=tmp_path / "runtime", corpus_path=source_path)


def test_repeated_prepare_and_cleanup_do_not_synthesize_duplicate_decisions(tmp_path, source_path):
    runtime = tmp_path / "runtime"
    assert verify("prepare", runtime_dir=runtime, corpus_path=source_path)["synthetic_decisions"] == 2
    assert verify("prepare", runtime_dir=runtime, corpus_path=source_path)["synthetic_decisions"] == 0
    assert verify("cleanup", runtime_dir=runtime, corpus_path=source_path)["synthetic_decisions"] == 1
    assert verify("cleanup", runtime_dir=runtime, corpus_path=source_path)["synthetic_decisions"] == 0


def test_operator_symlink_cannot_redirect_into_real_runtime(tmp_path, source_path):
    runtime = tmp_path / "runtime"; runtime.mkdir()
    actual = tmp_path / "unrelated"; actual.mkdir()
    (runtime / "lesson-operator").symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        verify("prepare", runtime_dir=runtime, corpus_path=source_path)


def test_operator_database_hardlink_cannot_alias_the_real_analyst_database(tmp_path, source_path):
    runtime = tmp_path / "runtime"
    real = Store(runtime / "portal.sqlite")
    real.create_run({"question": "Unrelated fictional record retained across hardlink rejection"})
    before = real.list_runs()
    directory = runtime / "lesson-operator"; directory.mkdir()
    (directory / "portal.sqlite").hardlink_to(real.path)
    with pytest.raises(ValueError, match="real analyst database"):
        verify("prepare", runtime_dir=runtime, corpus_path=source_path)
    assert real.list_runs() == before


def test_changed_source_cannot_claim_persistence_equivalence(tmp_path, source_path):
    runtime = tmp_path / "runtime"
    verify("prepare", runtime_dir=runtime, corpus_path=source_path)
    source_path.write_text(source_path.read_text() + "\n")
    with pytest.raises(ValueError, match="source changed"):
        verify("inspect", runtime_dir=runtime, corpus_path=source_path)
