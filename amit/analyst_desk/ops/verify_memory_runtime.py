"""Verify persistent analyst memory using only a reserved operator namespace.

Prepare writes the declared synthetic operator preference and public coverage;
inspect is suitable after an external service restart; cleanup leaves an empty
version tombstone. Real analyst preferences, runs and publications stay intact.
Receipts contain counts, checks and public corpus identity, never private values.
"""
import argparse
import asyncio
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desk.data import Corpus
from desk.history import REFERENCE_FIELDS, note_reference
from desk.memory import MemoryConflict, MemoryStore
from desk.store import Store
from desk.workflow import Engine

OPERATOR_ACTOR = "operator-memory-check"
ANALYST_ACTOR = "local-analyst"
OPERATOR_VALUES = {"default_companies": ["MSFT"], "default_years": [2025],
                   "report_style": "summary_first", "history_limit": 2}


def _real_analyst_snapshot(store, memory):
    item = memory.langgraph_store.get(("analyst", ANALYST_ACTOR, "preferences"), "profile", refresh_ttl=False)
    return {"preferences": deepcopy(item.value) if item else None,
            "policy": memory.get_note_policy(ANALYST_ACTOR),
            "runs": store.list_runs(ANALYST_ACTOR), "notes": store.notes(ANALYST_ACTOR)}


def _coverage_checks(source, coverage):
    companies = source.companies()
    wanted = {(company["ticker"], year) for company in companies for year in source.years(company["ticker"])}
    if not isinstance(coverage, dict):
        return False
    rows = coverage.get("rows")
    if (not isinstance(rows, list) or coverage.get("source_fingerprint") != source.fingerprint
            or coverage.get("company_count") != len(companies)
            or coverage.get("company_year_count") != len(wanted)
            or len(rows) != len(wanted)
            or {(row.get("ticker"), row.get("fiscal_year")) for row in rows} != wanted):
        return False
    for row in rows:
        passages = [passage for passage in source._passages.values()
                    if passage["ticker"] == row["ticker"] and passage["year"] == row["fiscal_year"]]
        if (row.get("fact_count") != len(source.facts(row["ticker"], [row["fiscal_year"]]))
                or row.get("passage_count") != len(passages)
                or row.get("table_count") != sum(bool(passage.get("table")) for passage in passages)
                or row.get("original_boundaries_verified") is not False):
            return False
    return True


async def verify(phase="inspect"):
    if phase not in {"prepare", "inspect", "cleanup"}:
        raise ValueError("Unknown memory verification phase")
    source, store = Corpus(), Store()
    companies = source.companies()
    sectors = Counter(company["sector"] for company in companies)
    if (len(companies) != 12 or sectors != {"Technology": 6, "Healthcare": 6}
            or any(source.years(company["ticker"]) != [2023, 2024, 2025] for company in companies)):
        raise ValueError("The declared twelve-company source snapshot is required")
    memory = MemoryStore(store.path)
    checks, tool_calls, reference_count = {}, 0, 0
    before = _real_analyst_snapshot(store, memory)
    try:
        if phase == "prepare":
            initial = memory.get_preferences(OPERATOR_ACTOR)
            if initial["status"] == "active" and initial["values"] != OPERATOR_VALUES:
                raise ValueError("The reserved operator namespace contains an unexpected preference")
            saved = memory.put_preferences(OPERATOR_ACTOR, OPERATOR_VALUES, initial["revision"])
            checks["operator_profile_saved_with_compare_and_swap"] = saved["status"] == "active" and saved["values"] == OPERATOR_VALUES
            try:
                memory.put_preferences(OPERATOR_ACTOR, OPERATOR_VALUES, initial["revision"])
            except MemoryConflict:
                checks["stale_operator_revision_rejected"] = True
            else:
                checks["stale_operator_revision_rejected"] = False
            memory.remember_coverage(source, OPERATOR_ACTOR)
            memory.close()
            memory = MemoryStore(store.path)
            checks["operator_profile_survives_close_and_reopen"] = memory.get_preferences(OPERATOR_ACTOR) == saved
            checks["public_coverage_survives_close_and_reopen"] = _coverage_checks(
                source, memory.get_coverage(source.fingerprint, OPERATOR_ACTOR))
        elif phase == "inspect":
            profile = memory.get_preferences(OPERATOR_ACTOR)
            checks["operator_profile_persisted"] = profile["status"] == "active" and profile["values"] == OPERATOR_VALUES
            checks["public_coverage_persisted"] = _coverage_checks(source, memory.get_coverage(source.fingerprint, OPERATOR_ACTOR))
            reader = object.__new__(Engine)
            tool_calls += 1
            response = await reader._wire_call("planner", "research-portal", "search_past_notes", {
                "query": "annual operating margins and disclosed risks", "tickers": ["MSFT", "AAPL"],
                "years": [2023, 2024, 2025], "current_source_fingerprint": source.fingerprint, "k": 3})
            if not isinstance(response, dict) or set(response) != {"references", "source_fingerprint"}:
                raise ValueError("Portal history response must contain bounded metadata only")
            references = response["references"]
            if (response["source_fingerprint"] != source.fingerprint or not isinstance(references, list)
                    or len(references) > 3 or len(json.dumps(response).encode("utf-8")) > 24000):
                raise ValueError("Portal history response differs from the frozen bounded scope")
            reference_count = len(references)
            seen, correct, isolated = set(), True, True
            excluded = set(memory.get_note_policy(ANALYST_ACTOR)["excluded_note_ids"])
            for reference in references:
                if not isinstance(reference, dict) or set(reference) != REFERENCE_FIELDS:
                    raise ValueError("Portal history exposed non-metadata fields")
                identifier = reference["note_id"]
                approved = store.approved_note(identifier, ANALYST_ACTOR)
                if approved is None or identifier in seen or identifier in excluded:
                    correct = False
                else:
                    correct &= note_reference(approved, source.fingerprint) == reference
                    correct &= any(row["ticker"] in {"MSFT", "AAPL"} and row["year"] in {2023, 2024, 2025}
                                   for row in approved["payload"]["metrics"])
                isolated &= store.approved_note(identifier, OPERATOR_ACTOR) is None
                seen.add(identifier)
            checks["authenticated_portal_returns_only_approved_scoped_metadata"] = correct
            checks["portal_note_hashes_and_archive_flags_match_library"] = correct
            checks["operator_actor_cannot_read_real_analyst_notes"] = isolated
            checks["operator_fixture_leaves_real_namespace_unchanged"] = (
                memory.get_preferences(OPERATOR_ACTOR)["revision"] > 0
                and _real_analyst_snapshot(store, memory)["preferences"] == before["preferences"])
        else:
            current = memory.get_preferences(OPERATOR_ACTOR)
            deleted = (memory.delete_preferences(OPERATOR_ACTOR, current["revision"])
                       if current["status"] != "absent" else current)
            checks["operator_preferences_deleted_to_empty_version_tombstone"] = deleted["status"] == "absent" and deleted["values"] == {}
            memory.close()
            memory = MemoryStore(store.path)
            checks["operator_preference_deletion_survives_reopen"] = memory.get_preferences(OPERATOR_ACTOR) == deleted
            checks["public_coverage_retained_separately"] = _coverage_checks(
                source, memory.get_coverage(source.fingerprint, OPERATOR_ACTOR))
        after = _real_analyst_snapshot(store, memory)
        checks["real_analyst_preferences_unchanged"] = before["preferences"] == after["preferences"]
        checks["real_analyst_note_policy_unchanged"] = before["policy"] == after["policy"]
        checks["existing_research_runs_unchanged"] = before["runs"] == after["runs"]
        checks["existing_approved_note_versions_unchanged"] = before["notes"] == after["notes"]
        operator_item = memory.langgraph_store.get(("analyst", OPERATOR_ACTOR, "preferences"), "profile", refresh_ttl=False)
        checks["operator_profile_uses_separate_langgraph_namespace"] = (
            operator_item is not None and tuple(operator_item.namespace) == ("analyst", OPERATOR_ACTOR, "preferences"))
        return {"status": "passed" if all(checks.values()) else "failed", "phase": phase,
                "verification_kind": "operator_persistent_memory_and_authenticated_portal",
                "source_fingerprint": source.fingerprint, "company_count": len(companies),
                "company_year_count": 36, "sector_counts": dict(sectors),
                "checks": checks, "checks_passed": sum(checks.values()), "checks_total": len(checks),
                "authenticated_tool_calls": tool_calls, "approved_history_reference_count": reference_count,
                "existing_approved_note_count": len(before["notes"]), "existing_research_run_count": len(before["runs"]),
                "generative_model_calls": 0, "external_provider_requests": 0, "research_runs_created": 0,
                "human_decisions_submitted": 0, "notes_published": 0,
                "limitations": [
                    "The operator preference is a declared synthetic fixture in a separate namespace, not an analyst's preference or human review.",
                    "Close/reopen checks confirm database persistence; a receipt from inspect after an externally recorded service restart is separate restart evidence.",
                    "Cleanup removes the synthetic preference values while retaining its revision tombstone, minimal audit and public source coverage.",
                    "This does not claim secure erasure of SQLite pages, backups or old checkpoints, or independent memory-quality evaluation.",
                ]}
    finally:
        memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "inspect", "cleanup"), default="inspect")
    arguments = parser.parse_args()
    try:
        receipt = asyncio.run(verify(arguments.phase))
        print(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False))
        raise SystemExit(0 if receipt["status"] == "passed" else 1)
    except Exception as error:
        print("Memory runtime verification failed: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
