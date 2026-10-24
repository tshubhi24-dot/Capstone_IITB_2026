"""Bounded analyst memory in the portal's actual LangGraph SQLite store.

Preferences contain typed controls, never free-form instructions. Approved note
bodies and publication grants remain in their existing portal tables. The
version validator deliberately uses the publisher's existing transaction.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import sqlite3
import threading
import time
from time import monotonic as _init_monotonic, sleep as _init_sleep
import uuid

from langgraph.store.sqlite import SqliteStore


PREFERENCE_TTL_SECONDS = 30 * 24 * 60 * 60
INITIALIZATION_TIMEOUT_SECONDS = 30
MAX_EXCLUDED_NOTES = 256
ACTOR_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
TICKER_PATTERN = re.compile(r"[A-Z][A-Z0-9.-]{0,9}\Z")
NOTE_PATTERN = re.compile(r"[0-9a-f]{32}\Z")
FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
PREFERENCE_KEYS = {"default_companies", "default_years", "report_style", "history_limit"}


class MemoryConflict(ValueError):
    """A stale revision or unavailable memory cannot silently affect research."""


def _actor(actor):
    if not isinstance(actor, str) or not ACTOR_PATTERN.fullmatch(actor):
        raise ValueError("Invalid analyst namespace.")
    return actor


def _namespace(actor, kind):
    return ("analyst", _actor(actor), kind)


def _finite_time(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _revision(value):
    if type(value) is not int or value < 0:
        raise ValueError("A nonnegative integer memory revision is required.")
    return value


def _preferences(values):
    if not isinstance(values, dict) or not set(values) <= PREFERENCE_KEYS:
        raise ValueError("Preferences support only the declared typed settings.")
    result = deepcopy(values)
    companies = values.get("default_companies")
    if companies is not None and (not isinstance(companies, list) or len(companies) > 4
            or any(not isinstance(value, str) or not TICKER_PATTERN.fullmatch(value) for value in companies)
            or len(set(companies)) != len(companies)):
        raise ValueError("Default companies require at most four distinct ticker symbols.")
    years = values.get("default_years")
    if years is not None and (not isinstance(years, list) or len(years) > 3
            or any(type(value) is not int or not 1000 <= value <= 9999 for value in years)
            or years != sorted(set(years))):
        raise ValueError("Default years require at most three distinct ascending fiscal years.")
    if "report_style" in values and (not isinstance(values["report_style"], str)
                                      or values["report_style"] not in {"table_first", "summary_first"}):
        raise ValueError("Choose a supported report style.")
    if "history_limit" in values and (type(values["history_limit"]) is not int or not 0 <= values["history_limit"] <= 3):
        raise ValueError("History limit must be an integer from zero through three.")
    # Explicit nulls are not an alternative free-form/default channel.
    if any(value is None for value in values.values()):
        raise ValueError("Preference settings cannot be null.")
    return result


def _preference_projection(raw, now):
    if raw is None:
        return {"revision": 0, "values": {}, "expires_at": None, "status": "absent"}
    try:
        if set(raw) != {"revision", "values", "expires_at", "updated_at"}:
            raise ValueError
        revision = _revision(raw["revision"])
        values = _preferences(raw["values"])
        expires, updated = raw["expires_at"], raw["updated_at"]
        if revision == 0 or not _finite_time(updated):
            raise ValueError
        if expires is None:
            if values:
                raise ValueError
            status = "absent"
        else:
            if not _finite_time(expires) or not math.isclose(expires - updated, PREFERENCE_TTL_SECONDS, abs_tol=1e-6, rel_tol=0):
                raise ValueError
            status = "active" if expires > now else "expired"
        return {"revision": revision, "values": values if status == "active" else {},
                "expires_at": expires, "status": status}
    except (KeyError, TypeError, ValueError) as error:
        raise MemoryConflict("Stored analyst preferences are invalid.") from error


def _policy_projection(raw):
    if raw is None:
        return {"revision": 0, "excluded_note_ids": []}
    try:
        if set(raw) != {"revision", "excluded_note_ids", "updated_at"}:
            raise ValueError
        revision, identifiers = _revision(raw["revision"]), raw["excluded_note_ids"]
        if revision == 0 or not _finite_time(raw["updated_at"]) or not isinstance(identifiers, list):
            raise ValueError
        if (len(identifiers) > MAX_EXCLUDED_NOTES or any(not isinstance(value, str) or not NOTE_PATTERN.fullmatch(value) for value in identifiers)
                or identifiers != sorted(set(identifiers))):
            raise ValueError
        return {"revision": revision, "excluded_note_ids": deepcopy(identifiers)}
    except (KeyError, TypeError, ValueError) as error:
        raise MemoryConflict("Stored note-reuse policy is invalid.") from error


class TransactionalSqliteStore(SqliteStore):
    """Real LangGraph store whose nested calls honor the caller's transaction.

    The dependency's default cursor commits in finally, including on failure.
    Here only the cursor that starts a transaction may commit or roll it back.
    An RLock also permits atomic read/check/put operations on one connection.
    """
    def __init__(self, conn):
        super().__init__(conn)
        self.lock = threading.RLock()

    def setup(self):
        # The pinned store migrations are individual SQL statements. Applying
        # them in one SQLite write transaction prevents concurrent first-use
        # migration races and avoids executescript's implicit outer commit.
        with self.lock:
            if self.is_setup:
                return
            if self.conn.in_transaction:
                raise MemoryConflict("Memory setup must finish before a publication transaction.")
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.conn.execute("CREATE TABLE IF NOT EXISTS store_migrations (v INTEGER PRIMARY KEY)")
                row = self.conn.execute("SELECT v FROM store_migrations ORDER BY v DESC LIMIT 1").fetchone()
                current = row[0] if row else -1
                for version, statement in enumerate(self.MIGRATIONS[current + 1:], current + 1):
                    self.conn.execute(statement)
                    self.conn.execute("INSERT INTO store_migrations(v) VALUES(?)", (version,))
                self.conn.commit()
            except BaseException:
                self.conn.rollback()
                raise
            self.is_setup = True

    @contextmanager
    def _cursor(self, *, transaction=True):
        if not self.is_setup:
            self.setup()
        with self.lock:
            owned = transaction and not self.conn.in_transaction
            if owned:
                self.conn.execute("BEGIN")
            cursor = self.conn.cursor()
            try:
                yield cursor
            except BaseException:
                if owned:
                    self.conn.rollback()
                raise
            else:
                if owned:
                    self.conn.commit()
            finally:
                cursor.close()


class MemoryStore:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = Path(path), clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=.25, check_same_thread=False, isolation_level=None)
        self.langgraph_store = TransactionalSqliteStore(self.conn)
        deadline = _init_monotonic() + INITIALIZATION_TIMEOUT_SECONDS
        delay = .01
        try:
            while True:
                # Journal-mode changes can return SQLITE_BUSY immediately,
                # even with SQLite's busy handler enabled. Bound the whole
                # WAL/migration sequence, rather than granting each retry a
                # new thirty-second wait or retrying arbitrary SQL failures.
                remaining = deadline - _init_monotonic()
                if remaining <= 0:
                    raise MemoryConflict("Analyst memory initialization remained busy; retry after the other writer finishes.")
                timeout_ms = max(1, min(250, int(remaining * 1000)))
                self.conn.execute(f"PRAGMA busy_timeout={timeout_ms}")
                try:
                    self.conn.execute("PRAGMA journal_mode=WAL")
                    self.conn.execute("PRAGMA secure_delete=ON")
                    self.langgraph_store.setup()
                except sqlite3.OperationalError as error:
                    if self.conn.in_transaction:
                        self.conn.rollback()
                    code = getattr(error, "sqlite_errorcode", None)
                    if type(code) is not int or (code & 0xFF) not in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                        raise
                    remaining = deadline - _init_monotonic()
                    if remaining <= 0:
                        raise MemoryConflict("Analyst memory initialization remained busy; retry after the other writer finishes.") from error
                    _init_sleep(min(delay, remaining))
                    delay = min(delay * 2, .25)
                    continue
                self.conn.execute("PRAGMA busy_timeout=30000")
                break
        except BaseException:
            self.conn.close()
            self._closed = True
            raise

    def close(self):
        with self.langgraph_store.lock:
            if not getattr(self, "_closed", False):
                self.conn.close()
                self._closed = True

    @contextmanager
    def _transaction(self):
        with self.langgraph_store.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self.conn.rollback()
                raise
            else:
                self.conn.commit()

    def _get(self, actor, kind, key):
        item = self.langgraph_store.get(_namespace(actor, kind), key, refresh_ttl=False)
        return item.value if item else None

    def _audit(self, actor, action, revision):
        self.langgraph_store.put(_namespace(actor, "memory-audit"), uuid.uuid4().hex,
                                 {"action": action, "revision": revision, "time": self.clock()}, index=False)

    def get_preferences(self, actor):
        return _preference_projection(self._get(actor, "preferences", "profile"), self.clock())

    def put_preferences(self, actor, values, expected_revision):
        _actor(actor)
        values, expected_revision = _preferences(values), _revision(expected_revision)
        with self._transaction():
            current = self.get_preferences(actor)
            if current["revision"] != expected_revision:
                raise MemoryConflict("Preferences changed; reload before saving.")
            now = self.clock()
            raw = {"revision": expected_revision + 1, "values": values,
                   "updated_at": now, "expires_at": now + PREFERENCE_TTL_SECONDS}
            self.langgraph_store.put(_namespace(actor, "preferences"), "profile", raw, index=False)
            self._audit(actor, "preferences_updated", raw["revision"])
            return _preference_projection(raw, now)

    def delete_preferences(self, actor, expected_revision):
        _actor(actor)
        expected_revision = _revision(expected_revision)
        with self._transaction():
            current = self.get_preferences(actor)
            if current["revision"] != expected_revision:
                raise MemoryConflict("Preferences changed; reload before deleting.")
            raw = {"revision": expected_revision + 1, "values": {}, "updated_at": self.clock(), "expires_at": None}
            self.langgraph_store.put(_namespace(actor, "preferences"), "profile", raw, index=False)
            self._audit(actor, "preferences_deleted", raw["revision"])
            return _preference_projection(raw, self.clock())

    def get_note_policy(self, actor):
        return _policy_projection(self._get(actor, "note-policy", "policy"))

    def set_note_excluded(self, actor, note_id, excluded, expected_revision):
        _actor(actor)
        expected_revision = _revision(expected_revision)
        if not isinstance(note_id, str) or not NOTE_PATTERN.fullmatch(note_id) or type(excluded) is not bool:
            raise ValueError("Note reuse requires a canonical note identifier and boolean choice.")
        with self._transaction():
            current = self.get_note_policy(actor)
            if current["revision"] != expected_revision:
                raise MemoryConflict("Note reuse changed; reload before saving.")
            identifiers = set(current["excluded_note_ids"])
            if (note_id in identifiers) == excluded:
                return current
            identifiers.add(note_id) if excluded else identifiers.discard(note_id)
            if len(identifiers) > MAX_EXCLUDED_NOTES:
                raise ValueError("The bounded note-reuse exclusion limit has been reached.")
            raw = {"revision": expected_revision + 1, "excluded_note_ids": sorted(identifiers), "updated_at": self.clock()}
            self.langgraph_store.put(_namespace(actor, "note-policy"), "policy", raw, index=False)
            self._audit(actor, "note_reuse_changed", raw["revision"])
            return _policy_projection(raw)

    def remember_coverage(self, corpus, actor):
        _actor(actor)
        fingerprint = corpus.fingerprint
        if not isinstance(fingerprint, str) or not FINGERPRINT_PATTERN.fullmatch(fingerprint):
            raise ValueError("Coverage requires a frozen source fingerprint.")
        rows = []
        companies = sorted(corpus.companies(), key=lambda company: company["ticker"])
        for company in companies:
            ticker = company["ticker"]
            for year in corpus.years(ticker):
                passages = [row for row in corpus._passages.values() if row["ticker"] == ticker and int(row["year"]) == year]
                groups = [{"item": item, "passage_count": sum(row["item"].upper() == item for row in passages),
                           "table_count": sum(row["item"].upper() == item and bool(row.get("table")) for row in passages)}
                          for item in ("1A", "7")]
                rows.append({"ticker": ticker, "company": company.get("company", ticker), "sector": company.get("sector", ""),
                             "fiscal_year": year, "fact_count": len(corpus.facts(ticker, [year])),
                             "passage_count": len(passages), "table_count": sum(bool(row.get("table")) for row in passages),
                             "section_groups": groups, "original_boundaries_verified": False})
        coverage = {"source_fingerprint": fingerprint, "company_count": len(companies), "company_year_count": len(rows), "rows": rows,
                    "limitations": ["Coverage describes only the frozen supplied source snapshot.",
                                    "Original filing Item boundaries and complete table extraction are unverified.",
                                    "Coverage counts do not establish financial comparability or economic risk interpretation."]}
        with self._transaction():
            existing = self._get(actor, "coverage", fingerprint)
            if existing is not None:
                if existing != coverage:
                    raise MemoryConflict("Coverage differs under the same frozen source fingerprint.")
                return deepcopy(existing)
            self.langgraph_store.put(_namespace(actor, "coverage"), fingerprint, coverage, index=False)
        return deepcopy(coverage)

    def get_coverage(self, source_fingerprint, actor):
        if not isinstance(source_fingerprint, str) or not FINGERPRINT_PATTERN.fullmatch(source_fingerprint):
            raise ValueError("Coverage requires a frozen source fingerprint.")
        return deepcopy(self._get(actor, "coverage", source_fingerprint))


def _transaction_value(db, actor, kind, key):
    row = db.execute("SELECT value FROM store WHERE prefix=? AND key=?", (".".join(_namespace(actor, kind)), key)).fetchone()
    return json.loads(row[0]) if row else None


def validate_memory_versions(db, actor, snapshot, now=None):
    """Check current memory using the publisher's already-open SQLite transaction.

    This function never creates a connection, initializes tables, commits,
    changes TTLs or writes memory. Publication code validates snapshot hashes,
    scope and approved-note references separately in the same transaction.
    """
    _actor(actor)
    if not isinstance(snapshot, dict) or snapshot.get("actor") != actor or type(snapshot.get("enabled")) is not bool:
        raise MemoryConflict("Analyst memory snapshot is missing or belongs to another namespace.")
    if snapshot["enabled"] is False:
        return True
    now = time.time() if now is None else now
    if not _finite_time(now):
        raise MemoryConflict("Analyst memory time is invalid.")
    try:
        preferences = _preference_projection(_transaction_value(db, actor, "preferences", "profile"), now)
        policy = _policy_projection(_transaction_value(db, actor, "note-policy", "policy"))
        if (type(snapshot.get("preference_revision")) is not int
                or snapshot["preference_revision"] != preferences["revision"]
                or snapshot.get("preferences_status") != preferences["status"]
                or "preferences_expires_at" not in snapshot
                or snapshot["preferences_expires_at"] != preferences["expires_at"]
                or type(snapshot.get("note_policy_revision")) is not int
                or snapshot["note_policy_revision"] != policy["revision"]):
            raise MemoryConflict("Analyst memory changed or expired; create a fresh plan before approval.")
        if snapshot.get("report_style") != preferences["values"].get("report_style", "table_first"):
            raise MemoryConflict("Saved report style differs from the frozen memory context.")
        references = snapshot.get("note_refs", [])
        if (not isinstance(references, list) or len(references) > preferences["values"].get("history_limit", 3)
                or any(not isinstance(reference, dict) or not isinstance(reference.get("note_id"), str)
                       or not NOTE_PATTERN.fullmatch(reference["note_id"]) for reference in references)
                or any(reference["note_id"] in policy["excluded_note_ids"] for reference in references)):
            raise MemoryConflict("Frozen history contains an invalid or excluded note reference.")
    except MemoryConflict:
        raise
    except (sqlite3.Error, KeyError, TypeError, ValueError) as error:
        raise MemoryConflict("Analyst memory could not be revalidated for publication.") from error
    return True
