"""Invented analyst-memory fixtures; no provider or live personal context."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import threading

import pytest
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.store.sqlite import SqliteStore

from desk.data import Corpus
from desk.memory import (MAX_EXCLUDED_NOTES, MemoryConflict, MemoryStore,
                         PREFERENCE_TTL_SECONDS, TransactionalSqliteStore, validate_memory_versions)
from desk.store import Store


@pytest.fixture
def memory(tmp_path):
    clock = [1000.0]
    value = MemoryStore(tmp_path / "portal.sqlite", clock=lambda: clock[0])
    yield value, clock
    value.close()


def snapshot(memory, actor="local-analyst"):
    profile, policy = memory.get_preferences(actor), memory.get_note_policy(actor)
    return {"enabled": True, "actor": actor, "preference_revision": profile["revision"],
            "preferences_expires_at": profile["expires_at"], "preferences_status": profile["status"],
            "note_policy_revision": policy["revision"],
            "report_style": profile["values"].get("report_style", "table_first"), "note_refs": []}


def validate(memory, value, now, actor="local-analyst"):
    with sqlite3.connect(memory.path) as db:
        return validate_memory_versions(db, actor, value, now=now)


def test_preferences_correct_delete_and_restart_without_resetting_revisions(memory):
    store, clock = memory
    assert store.get_preferences("local-analyst") == {"revision": 0, "values": {}, "expires_at": None, "status": "absent"}
    first = store.put_preferences("local-analyst", {"default_companies": ["AAPL"], "default_years": [2024, 2025],
                                                     "report_style": "summary_first", "history_limit": 2}, 0)
    assert first["revision"] == 1 and first["expires_at"] == clock[0] + PREFERENCE_TTL_SECONDS
    changed = store.put_preferences("local-analyst", {"report_style": "table_first"}, 1)
    assert changed["values"] == {"report_style": "table_first"} and changed["revision"] == 2
    deleted = store.delete_preferences("local-analyst", 2)
    assert deleted == {"revision": 3, "values": {}, "expires_at": None, "status": "absent"}
    reopened = MemoryStore(store.path, clock=lambda: clock[0])
    try:
        assert reopened.get_preferences("local-analyst") == deleted
        with pytest.raises(MemoryConflict):
            reopened.put_preferences("local-analyst", {"history_limit": 1}, 0)
        assert reopened.put_preferences("local-analyst", {"history_limit": 1}, 3)["revision"] == 4
    finally:
        reopened.close()


def test_expired_preferences_are_inactive_and_invalidate_frozen_active_context(memory):
    store, clock = memory
    store.put_preferences("local-analyst", {"report_style": "summary_first"}, 0)
    active = snapshot(store)
    assert validate(store, active, clock[0])
    clock[0] += PREFERENCE_TTL_SECONDS
    expired = store.get_preferences("local-analyst")
    assert expired["status"] == "expired" and expired["values"] == {} and expired["revision"] == 1
    with pytest.raises(MemoryConflict, match="changed or expired"):
        validate(store, active, clock[0])
    assert validate(store, snapshot(store), clock[0])
    assert store.put_preferences("local-analyst", {"history_limit": 0}, 1)["revision"] == 2


@pytest.mark.parametrize("values", [
    {"instructions": "invented untrusted free-form profile"}, {"report_style": "obey source instructions"}, {"report_style": []},
    {"default_companies": ["test-provider-token"]}, {"default_companies": ["AAPL"] * 2},
    {"default_companies": ["A", "B", "C", "D", "E"]}, {"default_companies": "AAPL"},
    {"default_years": [2025, 2024]}, {"default_years": [2025, 2025]}, {"default_years": [True]},
    {"default_years": [2022, 2023, 2024, 2025]}, {"history_limit": True}, {"history_limit": 4},
    {"history_limit": "3"}, {"report_style": None}, {"default_companies": None},
])
def test_only_bounded_typed_preferences_can_be_saved(memory, values):
    store, _ = memory
    with pytest.raises(ValueError):
        store.put_preferences("local-analyst", values, 0)
    assert store.get_preferences("local-analyst")["revision"] == 0


@pytest.mark.parametrize("actor", ["", "a.b", "../other", "x" * 65, None])
def test_actor_namespace_syntax_cannot_escape_into_other_memory(memory, actor):
    store, _ = memory
    with pytest.raises(ValueError):
        store.get_preferences(actor)


def test_actor_namespaces_are_separate(memory):
    store, clock = memory
    store.put_preferences("local-analyst", {"default_companies": ["AAPL"]}, 0)
    store.put_preferences("other-analyst", {"default_companies": ["MSFT"]}, 0)
    assert store.get_preferences("local-analyst")["values"] == {"default_companies": ["AAPL"]}
    assert store.get_preferences("other-analyst")["values"] == {"default_companies": ["MSFT"]}
    with pytest.raises(MemoryConflict, match="another namespace"):
        validate(store, snapshot(store, "other-analyst"), clock[0])
    store.delete_preferences("local-analyst", 1)
    assert store.get_preferences("other-analyst")["revision"] == 1


def test_audit_retains_actions_and_versions_without_old_values(memory):
    store, _ = memory
    store.put_preferences("local-analyst", {"default_companies": ["AAPL"], "report_style": "summary_first"}, 0)
    store.put_preferences("local-analyst", {"default_companies": ["MSFT"]}, 1)
    store.delete_preferences("local-analyst", 2)
    audits = store.langgraph_store.search(("analyst", "local-analyst", "memory-audit"), limit=10)
    assert len(audits) == 3
    assert all(set(row.value) == {"action", "revision", "time"} for row in audits)
    assert "AAPL" not in json.dumps([row.value for row in audits])
    assert "summary_first" not in json.dumps([row.value for row in audits])
    raw = store.langgraph_store.get(("analyst", "local-analyst", "preferences"), "profile").value
    assert raw["values"] == {} and raw["revision"] == 3


def test_two_connections_cannot_both_win_the_same_preference_revision(memory):
    first, clock = memory
    second = MemoryStore(first.path, clock=lambda: clock[0])
    barrier = threading.Barrier(2)
    def write(store, style):
        barrier.wait(timeout=5)
        try:
            return store.put_preferences("local-analyst", {"report_style": style}, 0)
        except MemoryConflict:
            return "stale"
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(write, first, "table_first"), executor.submit(write, second, "summary_first")]
            results = [future.result(timeout=10) for future in futures]
        assert results.count("stale") == 1
        assert first.get_preferences("local-analyst")["revision"] == 1
    finally:
        second.close()


def test_concurrent_cold_start_initializes_the_real_store_once(tmp_path):
    path = tmp_path / "cold-portal.sqlite"
    barrier = threading.Barrier(4)
    def initialize(index):
        barrier.wait(timeout=5)
        store = MemoryStore(path)
        try:
            return store.put_preferences(f"invented-actor-{index}", {"history_limit": index % 4}, 0)["revision"]
        finally:
            store.close()
            store.close()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(initialize, index) for index in range(4)]
        assert [future.result(timeout=15) for future in futures] == [1] * 4
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM store_migrations").fetchone()[0] == len(SqliteStore.MIGRATIONS)


def test_busy_migration_retries_roll_back_partial_work_before_retry(tmp_path, monkeypatch):
    import desk.memory as module
    original = TransactionalSqliteStore.setup
    attempts, pauses = [], []
    def temporarily_busy(store):
        attempts.append(1)
        if len(attempts) <= 2:
            store.conn.execute("BEGIN IMMEDIATE")
            store.conn.execute("CREATE TABLE invented_partial_migration(value INTEGER)")
            error = sqlite3.OperationalError("invented transient migration lock")
            error.sqlite_errorcode = sqlite3.SQLITE_BUSY_SNAPSHOT
            raise error
        return original(store)
    monkeypatch.setattr(TransactionalSqliteStore, "setup", temporarily_busy)
    monkeypatch.setattr(module, "_init_sleep", pauses.append)
    store = MemoryStore(tmp_path / "busy.sqlite")
    try:
        assert len(attempts) == 3 and pauses == [.01, .02]
        assert store.get_preferences("local-analyst")["status"] == "absent"
        assert store.conn.execute("SELECT name FROM sqlite_master WHERE name='invented_partial_migration'").fetchone() is None
    finally:
        store.close()


def test_initialization_never_retries_other_sql_failures_and_closes_connection(tmp_path, monkeypatch):
    import desk.memory as module
    connections = []
    def invalid_sql(store):
        connections.append(store.conn)
        error = sqlite3.OperationalError("invented nontransient schema error")
        error.sqlite_errorcode = sqlite3.SQLITE_ERROR
        raise error
    monkeypatch.setattr(TransactionalSqliteStore, "setup", invalid_sql)
    monkeypatch.setattr(module, "_init_sleep", lambda delay: pytest.fail("Nontransient SQL errors must not retry"))
    with pytest.raises(sqlite3.OperationalError, match="nontransient"):
        MemoryStore(tmp_path / "invalid.sqlite")
    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connections[0].execute("SELECT 1")


def test_initialization_has_one_bounded_deadline_for_all_busy_retries(tmp_path, monkeypatch):
    import desk.memory as module
    times = iter([0, 0, 31])
    connections = []
    def remains_busy(store):
        connections.append(store.conn)
        error = sqlite3.OperationalError("invented persistent lock")
        error.sqlite_errorcode = sqlite3.SQLITE_LOCKED
        raise error
    monkeypatch.setattr(TransactionalSqliteStore, "setup", remains_busy)
    monkeypatch.setattr(module, "_init_monotonic", lambda: next(times))
    monkeypatch.setattr(module, "_init_sleep", lambda delay: pytest.fail("Expired initialization must stop"))
    with pytest.raises(MemoryConflict, match="remained busy"):
        MemoryStore(tmp_path / "deadline.sqlite")
    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connections[0].execute("SELECT 1")


def test_real_langgraph_store_is_attached_to_compiled_graph(memory):
    store, _ = memory
    assert isinstance(store.langgraph_store, (BaseStore, SqliteStore))
    store.put_preferences("local-analyst", {"report_style": "summary_first"}, 0)
    def inspect_preference(state, runtime: Runtime):
        item = runtime.store.get(("analyst", "local-analyst", "preferences"), "profile")
        return {"observed_style": item.value["values"]["report_style"]}
    graph = StateGraph(dict)
    graph.add_node("inspect", inspect_preference)
    graph.add_edge(START, "inspect")
    graph.add_edge("inspect", END)
    compiled = graph.compile(store=store.langgraph_store)
    assert compiled.invoke({}) == {"observed_style": "summary_first"}


def test_langgraph_nested_put_does_not_commit_an_outer_failed_transaction(memory):
    store, _ = memory
    with pytest.raises(RuntimeError):
        with store._transaction():
            store.langgraph_store.put(("analyst", "local-analyst", "test"), "pending", {"invented": True})
            assert store.conn.in_transaction
            raise RuntimeError("invented transaction failure")
    assert store.langgraph_store.get(("analyst", "local-analyst", "test"), "pending") is None


def test_failed_owned_store_cursor_rolls_back_instead_of_committing_partial_writes(memory):
    store, _ = memory
    with pytest.raises(sqlite3.OperationalError):
        with store.langgraph_store._cursor() as cursor:
            cursor.execute("INSERT INTO store(prefix,key,value) VALUES(?,?,?)", ("analyst.local-analyst.test", "pending", '{"invented":true}'))
            cursor.execute("INSERT INTO missing_test_only_table VALUES(1)")
    assert not store.conn.in_transaction
    assert store.langgraph_store.get(("analyst", "local-analyst", "test"), "pending") is None


def test_note_reuse_tombstones_are_bounded_actor_scoped_and_revisioned(memory):
    store, clock = memory
    note_id = "a" * 32
    original = snapshot(store)
    excluded = store.set_note_excluded("local-analyst", note_id, True, 0)
    assert excluded == {"revision": 1, "excluded_note_ids": [note_id]}
    assert store.get_note_policy("other-analyst") == {"revision": 0, "excluded_note_ids": []}
    assert store.set_note_excluded("local-analyst", note_id, True, 1) == excluded
    with pytest.raises(MemoryConflict):
        validate(store, original, clock[0])
    assert store.set_note_excluded("local-analyst", note_id, False, 1) == {"revision": 2, "excluded_note_ids": []}
    with pytest.raises(MemoryConflict):
        store.set_note_excluded("local-analyst", note_id, True, 0)
    assert MAX_EXCLUDED_NOTES == 256


def test_exclusion_limit_rejects_growth_but_permits_restoring_a_note(memory):
    store, clock = memory
    identifiers = [f"{index:032x}" for index in range(MAX_EXCLUDED_NOTES)]
    store.langgraph_store.put(("analyst", "local-analyst", "note-policy"), "policy",
                              {"revision": 1, "excluded_note_ids": identifiers, "updated_at": clock[0]})
    with pytest.raises(ValueError, match="exclusion limit"):
        store.set_note_excluded("local-analyst", "f" * 32, True, 1)
    assert store.get_note_policy("local-analyst")["revision"] == 1
    assert len(store.set_note_excluded("local-analyst", identifiers[0], False, 1)["excluded_note_ids"]) == MAX_EXCLUDED_NOTES - 1


def test_version_validator_rejects_forged_style_and_currently_excluded_reference(memory):
    store, clock = memory
    store.put_preferences("local-analyst", {"report_style": "summary_first"}, 0)
    current = snapshot(store)
    assert validate(store, current, clock[0])
    with pytest.raises(MemoryConflict, match="style"):
        validate(store, {**current, "report_style": "table_first"}, clock[0])
    store.set_note_excluded("local-analyst", "a" * 32, True, 0)
    forged = {**snapshot(store), "note_refs": [{"note_id": "a" * 32}]}
    with pytest.raises(MemoryConflict, match="excluded"):
        validate(store, forged, clock[0])


def test_saved_zero_history_limit_rejects_rehashed_note_references(memory):
    store, clock = memory
    store.put_preferences("local-analyst", {"history_limit": 0}, 0)
    frozen = snapshot(store)
    assert validate(store, frozen, clock[0])
    with pytest.raises(MemoryConflict, match="reference"):
        validate(store, {**frozen, "note_refs": [{"note_id": "a" * 32}]}, clock[0])


def test_validation_uses_existing_publication_transaction_without_committing_or_writing(memory):
    store, clock = memory
    frozen = snapshot(store)
    db = sqlite3.connect(store.path, isolation_level=None)
    try:
        db.execute("BEGIN IMMEDIATE")
        before = db.total_changes
        assert validate_memory_versions(db, "local-analyst", frozen, now=clock[0])
        assert db.in_transaction and db.total_changes == before
        db.rollback()
    finally:
        db.close()


def test_publication_write_lock_serializes_preference_changes(memory):
    store, clock = memory
    frozen = snapshot(store)
    db = sqlite3.connect(store.path, isolation_level=None)
    started = threading.Event()
    def write():
        started.set()
        return store.put_preferences("local-analyst", {"history_limit": 1}, 0)
    try:
        db.execute("BEGIN IMMEDIATE")
        assert validate_memory_versions(db, "local-analyst", frozen, now=clock[0])
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(write)
            assert started.wait(timeout=5)
            assert not future.done()
            db.commit()
            assert future.result(timeout=5)["revision"] == 1
        with pytest.raises(MemoryConflict):
            validate(store, frozen, clock[0])
    finally:
        db.close()


def test_disabled_memory_does_not_read_memory_tables(tmp_path):
    db = sqlite3.connect(tmp_path / "empty.sqlite")
    try:
        assert validate_memory_versions(db, "local-analyst", {"enabled": False, "actor": "local-analyst"})
        with pytest.raises(MemoryConflict):
            validate_memory_versions(db, "local-analyst", {"enabled": True, "actor": "local-analyst"})
    finally:
        db.close()


@pytest.fixture
def corpus(tmp_path):
    document = {"companies": [{"ticker": ticker, "company": ticker + " invented company", "sector": "Test"} for ticker in ("A", "B")],
                "facts": [], "passages": []}
    for ticker in ("A", "B"):
        for year in (2024, 2025):
            for concept in ("revenue", "operating_income"):
                document["facts"].append({"id": f"{ticker}-{year}-{concept}", "ticker": ticker, "fiscal_year": year})
            for item in ("1A", "7"):
                document["passages"].append({"id": f"{ticker}-{year}-{item}", "ticker": ticker, "year": year,
                                             "item": item, "text": "Invented public-source fixture.",
                                             "table": [["Invented cell", "value"]] if item == "7" else []})
    path = tmp_path / "source.json"
    path.write_text(json.dumps(document))
    return Corpus(path)


def test_source_coverage_is_derived_immutable_and_actor_scoped(memory, corpus):
    store, _ = memory
    assert store.get_coverage(corpus.fingerprint, "local-analyst") is None
    coverage = store.remember_coverage(corpus, "local-analyst")
    assert coverage["company_count"] == 2 and coverage["company_year_count"] == 4
    assert all(row["fact_count"] == 2 and row["passage_count"] == 2 and row["table_count"] == 1 for row in coverage["rows"])
    assert all(row["original_boundaries_verified"] is False for row in coverage["rows"])
    assert "unverified" in " ".join(coverage["limitations"])
    assert store.remember_coverage(corpus, "local-analyst") == coverage
    assert store.get_coverage(corpus.fingerprint, "other-analyst") is None
    corpus._passages["new"] = {**corpus._passages["A-2025-7"], "id": "new"}
    with pytest.raises(MemoryConflict, match="same frozen"):
        store.remember_coverage(corpus, "local-analyst")
    assert store.get_coverage(corpus.fingerprint, "local-analyst") == coverage


def test_coverage_restart_and_new_source_identity_preserve_prior_snapshot(memory, corpus):
    store, clock = memory
    original = store.remember_coverage(corpus, "local-analyst")
    restarted = MemoryStore(store.path, clock=lambda: clock[0])
    try:
        assert restarted.get_coverage(corpus.fingerprint, "local-analyst") == original
        document = json.loads(corpus.path.read_text())
        document["passages"].append({**document["passages"][0], "id": "new-public-source-passage"})
        corpus.path.write_text(json.dumps(document))
        corrected = Corpus(corpus.path)
        current = restarted.remember_coverage(corrected, "local-analyst")
        assert current["source_fingerprint"] != original["source_fingerprint"]
        assert restarted.get_coverage(original["source_fingerprint"], "local-analyst") == original
        assert sum(row["passage_count"] for row in current["rows"]) == 9
    finally:
        restarted.close()


def test_preference_deletion_invalidates_old_frozen_context(memory):
    store, clock = memory
    store.put_preferences("local-analyst", {"history_limit": 2}, 0)
    old = snapshot(store)
    store.delete_preferences("local-analyst", 1)
    with pytest.raises(MemoryConflict):
        validate(store, old, clock[0])
    assert validate(store, snapshot(store), clock[0])


def test_memory_tables_preserve_preexisting_portal_runs_and_notes(tmp_path):
    portal = Store(tmp_path / "portal.sqlite", secret="invented-publication-secret-" * 3)
    run = portal.create_run({"question": "Invented prior research request"})
    with portal.connection() as db:
        db.execute("INSERT INTO notes VALUES(?,?,?,?,?,?)", ("a" * 32, run["id"], "local-analyst", "b" * 64,
                                                           json.dumps({"body": "Invented previously approved note"}), 100))
    before = {"runs": portal.list_runs(), "notes": portal.notes()}
    memory = MemoryStore(portal.path)
    try:
        memory.put_preferences("local-analyst", {"history_limit": 2}, 0)
        memory.delete_preferences("local-analyst", 1)
        memory.set_note_excluded("local-analyst", "a" * 32, True, 0)
        assert portal.list_runs() == before["runs"] and portal.notes() == before["notes"]
    finally:
        memory.close()
