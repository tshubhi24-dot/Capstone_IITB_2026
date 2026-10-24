"""Runtime-verifier phases against invented local SQLite and fake portal MCP."""
import asyncio
from copy import deepcopy
import json

import pytest

from desk.data import Corpus
from desk.history import search_approved_notes
from desk.memory import MemoryStore
from desk.store import Store, canonical_hash
from desk.workflow import Engine
from ops import verify_memory_runtime as verification


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    tickers = {"Technology": ["MSFT", "AAPL", "GOOGL", "ORCL", "ADBE", "CRM"],
               "Healthcare": ["ABBV", "AMGN", "GILD", "ABT", "UNH", "TMO"]}
    document = {"companies": [], "facts": [], "passages": []}
    for sector, issuers in tickers.items():
        for ticker in issuers:
            document["companies"].append({"ticker": ticker, "company": "Invented " + ticker, "sector": sector})
            for year in (2023, 2024, 2025):
                for concept in ("revenue", "operating_income"):
                    document["facts"].append({"id": f"{ticker}-{year}-{concept}", "ticker": ticker,
                                              "fiscal_year": year, "concept": concept})
                for item in ("1A", "7"):
                    document["passages"].append({"id": f"{ticker}-{year}-{item}", "ticker": ticker,
                                                 "year": year, "item": item, "text": "Invented public annual filing."})
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(document))
    monkeypatch.setenv("CORPUS_PATH", str(path))
    monkeypatch.setenv("RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("PUBLICATION_SECRET", "invented-runtime-verifier-signing-secret-" * 2)
    monkeypatch.delenv("SCOPED_CONFIG", raising=False)
    source, store = Corpus(path), Store()
    memory = MemoryStore(store.path)
    memory.put_preferences("local-analyst", {"report_style": "table_first", "default_companies": ["AAPL"]}, 0)
    run = store.create_run({"question": "INVENTED_PRIVATE_QUESTION"})
    payload = {"run_id": run["id"], "actor": "local-analyst", "title": "INVENTED_PRIVATE_NOTE_TITLE",
               "body": "INVENTED_PRIVATE_BODY. Annual operating margins and disclosed risks.",
               "source_fingerprint": "f" * 64, "metrics": [{"ticker": "MSFT", "year": 2025}]}
    run.update(draft=payload, pending={"kind": "note", "payload": payload}, critic={"passed": True})
    store.save_run(run)
    digest = canonical_hash(payload)
    store.record_approval(run["id"], "local-analyst", digest)
    publication = store.publish(payload, store.make_capability(run["id"], "local-analyst", digest))
    calls, mutation = [], {"response": None, "change_real_profile": False, "raise_error": False}
    async def wire(self, role, server, tool, arguments):
        assert (role, server, tool) == ("planner", "research-portal", "search_past_notes")
        assert arguments["tickers"] == ["MSFT", "AAPL"] and arguments["years"] == [2023, 2024, 2025]
        assert arguments["current_source_fingerprint"] == source.fingerprint and arguments["k"] == 3
        calls.append((role, server, tool, deepcopy(arguments)))
        if mutation["raise_error"]:
            raise RuntimeError("INVENTED_PRIVATE_TRANSPORT_ERROR")
        if mutation["change_real_profile"]:
            profile = memory.get_preferences("local-analyst")
            memory.put_preferences("local-analyst", {"report_style": "summary_first"}, profile["revision"])
        refs = search_approved_notes(store, memory, arguments["query"], arguments["tickers"], arguments["years"],
                                     k=arguments["k"], actor="local-analyst", current_source_fingerprint=source.fingerprint)
        response = {"references": refs, "source_fingerprint": source.fingerprint}
        if mutation["response"]:
            mutation["response"](response)
        return response
    monkeypatch.setattr(Engine, "_wire_call", wire)
    monkeypatch.setattr(Engine, "__init__", lambda *args, **kwargs: pytest.fail("Verifier must not create a research engine"))
    yield {"source": source, "store": store, "memory": memory, "calls": calls,
           "mutation": mutation, "publication": publication, "payload": payload}
    memory.close()


def phase(name):
    return asyncio.run(verification.verify(name))


def test_prepare_inspect_cleanup_persist_only_reserved_operator_namespace(runtime):
    memory, store = runtime["memory"], runtime["store"]
    before_preferences = memory.get_preferences("local-analyst")
    before_notes, before_runs = store.notes(), store.list_runs()
    prepared = phase("prepare")
    assert prepared["status"] == "passed" and prepared["authenticated_tool_calls"] == 0
    assert prepared["checks"]["stale_operator_revision_rejected"]
    profile = memory.get_preferences(verification.OPERATOR_ACTOR)
    assert profile["values"] == verification.OPERATOR_VALUES and profile["status"] == "active"
    inspected = phase("inspect")
    assert inspected["status"] == "passed" and inspected["authenticated_tool_calls"] == 1
    assert inspected["approved_history_reference_count"] == 1
    assert inspected["company_count"] == 12 and inspected["company_year_count"] == 36
    assert all(inspected["checks"].values())
    cleaned = phase("cleanup")
    assert cleaned["status"] == "passed" and cleaned["authenticated_tool_calls"] == 0
    final = memory.get_preferences(verification.OPERATOR_ACTOR)
    assert final["values"] == {} and final["status"] == "absent" and final["revision"] > profile["revision"]
    assert memory.get_preferences("local-analyst") == before_preferences
    assert store.notes() == before_notes and store.list_runs() == before_runs
    assert len(runtime["calls"]) == 1


def test_receipt_never_contains_real_or_synthetic_preference_values_notes_ids_or_private_prose(runtime):
    prepared = phase("prepare")
    inspected = phase("inspect")
    cleaned = phase("cleanup")
    serialized = json.dumps([prepared, inspected, cleaned])
    for private in ("INVENTED_PRIVATE_QUESTION", "INVENTED_PRIVATE_BODY", "INVENTED_PRIVATE_NOTE_TITLE",
                    runtime["publication"]["note_id"], runtime["payload"]["run_id"],
                    runtime["publication"]["payload_hash"], "default_companies", "summary_first"):
        assert private not in serialized
    assert all(value["generative_model_calls"] == value["external_provider_requests"] == 0
               for value in (prepared, inspected, cleaned))
    assert all(value["research_runs_created"] == value["human_decisions_submitted"] == value["notes_published"] == 0
               for value in (prepared, inspected, cleaned))


def test_inspect_without_prepare_does_not_invent_persistent_success(runtime):
    result = phase("inspect")
    assert result["status"] == "failed"
    assert result["checks"]["operator_profile_persisted"] is False
    assert result["checks"]["public_coverage_persisted"] is False
    assert result["checks"]["operator_profile_uses_separate_langgraph_namespace"] is False


def test_prepare_refuses_unexpected_existing_reserved_profile(runtime):
    memory = runtime["memory"]
    saved = memory.put_preferences(verification.OPERATOR_ACTOR, {"report_style": "table_first"}, 0)
    before = memory.get_preferences("local-analyst")
    with pytest.raises(ValueError, match="unexpected preference"):
        phase("prepare")
    assert memory.get_preferences(verification.OPERATOR_ACTOR) == saved
    assert memory.get_preferences("local-analyst") == before


def test_cleanup_is_idempotent_and_does_not_delete_public_coverage(runtime):
    phase("prepare")
    assert phase("cleanup")["status"] == "passed"
    before = runtime["memory"].get_preferences(verification.OPERATOR_ACTOR)
    assert phase("cleanup")["status"] == "passed"
    assert runtime["memory"].get_preferences(verification.OPERATOR_ACTOR) == before
    assert runtime["memory"].get_coverage(runtime["source"].fingerprint, verification.OPERATOR_ACTOR) is not None


def test_changed_persisted_coverage_is_reported_as_failure(runtime):
    phase("prepare")
    memory, source = runtime["memory"], runtime["source"]
    coverage = memory.get_coverage(source.fingerprint, verification.OPERATOR_ACTOR)
    coverage["rows"][0]["passage_count"] += 1
    memory.langgraph_store.put(("analyst", verification.OPERATOR_ACTOR, "coverage"), source.fingerprint,
                               coverage, index=False)
    result = phase("inspect")
    assert result["status"] == "failed" and result["checks"]["public_coverage_persisted"] is False


def test_inspection_detects_accidental_real_namespace_mutation(runtime):
    phase("prepare")
    runtime["mutation"]["change_real_profile"] = True
    result = phase("inspect")
    assert result["status"] == "failed"
    assert result["checks"]["real_analyst_preferences_unchanged"] is False


@pytest.mark.parametrize("mutation", [
    lambda response: response.update(body="Private prose is not metadata"),
    lambda response: response.update(source_fingerprint="0" * 64),
    lambda response: response["references"][0].update(body="Private note prose"),
])
def test_portal_response_cannot_expose_bodies_or_change_corpus_identity(runtime, mutation):
    phase("prepare")
    runtime["mutation"]["response"] = mutation
    with pytest.raises(ValueError):
        phase("inspect")


def test_wrong_archival_status_is_not_accepted_as_current_source_history(runtime):
    phase("prepare")
    runtime["mutation"]["response"] = lambda response: response["references"][0].update(archive_only=False, current_source=True)
    result = phase("inspect")
    assert result["status"] == "failed"
    assert result["checks"]["portal_note_hashes_and_archive_flags_match_library"] is False


def test_namespace_policy_exclusions_are_honored_by_portal(runtime):
    phase("prepare")
    note_id = runtime["publication"]["note_id"]
    runtime["memory"].set_note_excluded("local-analyst", note_id, True, 0)
    result = phase("inspect")
    assert result["status"] == "passed" and result["approved_history_reference_count"] == 0


def test_unavailable_portal_stops_without_any_workflow_or_provider_fallback(runtime):
    phase("prepare")
    runtime["mutation"]["raise_error"] = True
    before_notes = runtime["store"].notes()
    with pytest.raises(RuntimeError):
        phase("inspect")
    assert len(runtime["calls"]) == 1 and runtime["store"].notes() == before_notes
