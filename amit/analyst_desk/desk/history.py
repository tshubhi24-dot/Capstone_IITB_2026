"""Bounded local approved-note context, separate from current SEC evidence.

Prior note bodies are used only for local lexical matching. Frozen references
contain code-owned labels and provenance, never arbitrary historical prose.
"""
import json
import math
import re

from rank_bm25 import BM25Okapi

from .store import canonical_hash

MAX_CANDIDATES = 50
MAX_REFERENCES = 3
MAX_CONTEXT_BYTES = 24000
SNAPSHOT_FIELDS = {"enabled", "actor", "preference_revision", "preferences_expires_at",
                   "preferences_status", "note_policy_revision", "source_fingerprint",
                   "report_style", "selection_scope", "note_refs", "fingerprint"}
REFERENCE_FIELDS = {"note_id", "run_id", "payload_hash", "source_fingerprint", "scope", "title",
                    "created_at", "archive_only", "current_source", "citation"}


def validate_scope(actor, tickers, years, limit, *, maximum=MAX_REFERENCES):
    if not isinstance(actor, str) or not 1 <= len(actor) <= 80:
        raise ValueError("A bounded analyst namespace is required")
    if (not isinstance(tickers, list) or not 1 <= len(tickers) <= 12
            or any(not isinstance(ticker, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker) for ticker in tickers)
            or len(tickers) != len(set(tickers))):
        raise ValueError("Approved-history search requires a bounded issuer scope")
    if (not isinstance(years, list) or not 1 <= len(years) <= 3
            or any(type(year) is not int or not 1900 <= year <= 2100 for year in years)
            or len(years) != len(set(years))):
        raise ValueError("Approved-history search requires a bounded fiscal-year scope")
    if type(limit) is not int or not 1 <= limit <= maximum:
        raise ValueError("Approved-history result count is outside its bound")


def note_scope(payload):
    """Use the actual published financial rows, never a title's claimed scope."""
    metrics = payload.get("metrics")
    if not isinstance(metrics, list) or not 1 <= len(metrics) <= 12:
        raise ValueError("An approved historical research note needs financial scope")
    pairs = set()
    for row in metrics:
        if (not isinstance(row, dict) or not isinstance(row.get("ticker"), str)
                or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", row["ticker"])
                or type(row.get("year")) is not int or not 1900 <= row["year"] <= 2100):
            raise ValueError("Historical financial scope is invalid")
        pairs.add((row["ticker"], row["year"]))
    if len(pairs) != len(metrics) or len({ticker for ticker, _ in pairs}) > 4 or len({year for _, year in pairs}) > 3:
        raise ValueError("Historical financial scope exceeds its distinct company/year bounds")
    return {"tickers": sorted({ticker for ticker, _ in pairs}), "years": sorted({year for _, year in pairs})}


def note_reference(note, current_source_fingerprint):
    payload = note["payload"]
    scope = note_scope(payload)
    source = payload.get("source_fingerprint")
    if not isinstance(source, str) or not re.fullmatch(r"[0-9a-f]{64}", source):
        raise ValueError("Historical source identity is unavailable")
    current = source == current_source_fingerprint
    return {"note_id": note["id"], "run_id": note["run_id"], "payload_hash": note["payload_hash"],
            "source_fingerprint": source, "scope": scope,
            "title": " / ".join(scope["tickers"]) + " approved research note",
            "created_at": note["created_at"], "archive_only": not current, "current_source": current,
            "citation": "note:" + note["id"] + "@" + note["payload_hash"]}


def _tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def search_approved_notes(store, memory, query, tickers, years, k=3, *, actor="local-analyst",
                          current_source_fingerprint):
    validate_scope(actor, tickers, years, k)
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 3000:
        raise ValueError("Approved-history search requires a bounded query")
    policy = memory.get_note_policy(actor)
    candidates = store.approved_note_candidates(actor, tickers, years, limit=MAX_CANDIDATES,
                                                excluded_note_ids=policy["excluded_note_ids"])
    if not candidates:
        return []
    query_tokens = _tokens(query)
    # The complete scoring corpus, as well as the returned context, is bounded.
    per_note_bytes = MAX_CONTEXT_BYTES // len(candidates)
    documents, references = [], []
    for candidate in candidates:
        try:
            reference = note_reference(candidate, current_source_fingerprint)
        except ValueError:
            continue
        payload = candidate["payload"]
        topic = reference["title"] + " " + str(payload.get("body", ""))
        bounded = topic.encode("utf-8")[:per_note_bytes].decode("utf-8", errors="ignore")
        documents.append(_tokens(bounded) or ["empty"])
        references.append(reference)
    if not references:
        return []
    scores = BM25Okapi(documents).get_scores(query_tokens)
    eligible = [index for index, words in enumerate(documents) if set(words) & set(query_tokens)]
    ordered = sorted(eligible, key=lambda index: (-float(scores[index]), -references[index]["created_at"],
                                                 references[index]["note_id"]))
    selected = []
    for index in ordered:
        proposed = selected + [references[index]]
        if len(json.dumps(proposed, ensure_ascii=False).encode("utf-8")) > MAX_CONTEXT_BYTES:
            break
        selected = proposed
        if len(selected) >= k:
            break
    return selected


def freeze_memory_context(store, memory, query, tickers, years, *, actor="local-analyst",
                          current_source_fingerprint, enabled=True, k=3):
    validate_scope(actor, tickers, years, k)
    if type(enabled) is not bool:
        raise ValueError("Memory enablement must be explicit")
    snapshot = {"enabled": enabled, "actor": actor, "preference_revision": None,
                "preferences_expires_at": None, "preferences_status": "disabled",
                "note_policy_revision": None, "source_fingerprint": current_source_fingerprint,
                "report_style": "table_first", "selection_scope": {"tickers": sorted(tickers), "years": sorted(years)},
                "note_refs": []}
    if enabled:
        profile = memory.get_preferences(actor)
        policy = memory.get_note_policy(actor)
        style = profile["values"].get("report_style", "table_first")
        if style not in {"table_first", "summary_first"}:
            raise ValueError("Unsupported saved report style")
        history_limit = min(k, profile["values"].get("history_limit", k))
        references = (search_approved_notes(store, memory, query, tickers, years, history_limit, actor=actor,
                                           current_source_fingerprint=current_source_fingerprint)
                      if history_limit else [])
        snapshot.update(preference_revision=profile["revision"], preferences_expires_at=profile["expires_at"],
                        preferences_status=profile["status"], note_policy_revision=policy["revision"], report_style=style,
                        note_refs=references)
    snapshot["fingerprint"] = canonical_hash(snapshot)
    store.validate_memory_snapshot(snapshot, source_fingerprint=current_source_fingerprint, actor=actor)
    return snapshot


def validate_snapshot_structure(snapshot, *, actor=None, source_fingerprint=None):
    if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_FIELDS:
        raise ValueError("The frozen memory context has unsupported fields")
    recorded = snapshot.get("fingerprint")
    unsigned = {key: value for key, value in snapshot.items() if key != "fingerprint"}
    if not isinstance(recorded, str) or canonical_hash(unsigned) != recorded:
        raise ValueError("The frozen memory context fingerprint changed")
    if type(snapshot["enabled"]) is not bool or not isinstance(snapshot["actor"], str) or not 1 <= len(snapshot["actor"]) <= 80:
        raise ValueError("The memory namespace is invalid")
    if actor is not None and snapshot["actor"] != actor:
        raise ValueError("The memory context belongs to a different analyst")
    if (not isinstance(snapshot["source_fingerprint"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", snapshot["source_fingerprint"])
            or source_fingerprint is not None and snapshot["source_fingerprint"] != source_fingerprint):
        raise ValueError("The memory context source snapshot changed")
    if snapshot["report_style"] not in {"table_first", "summary_first"}:
        raise ValueError("The memory context has an unsupported report style")
    scope = snapshot["selection_scope"]
    if not isinstance(scope, dict) or set(scope) != {"tickers", "years"}:
        raise ValueError("The frozen memory selection scope is invalid")
    validate_scope(snapshot["actor"], scope["tickers"], scope["years"], 1)
    if scope["tickers"] != sorted(scope["tickers"]) or scope["years"] != sorted(scope["years"]):
        raise ValueError("The frozen memory selection scope is not canonical")
    refs = snapshot["note_refs"]
    if not isinstance(refs, list) or len(refs) > MAX_REFERENCES or len(json.dumps(snapshot).encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise ValueError("The memory context exceeds its bounded reference budget")
    if not snapshot["enabled"]:
        expected = {"preference_revision": None, "preferences_expires_at": None, "preferences_status": "disabled",
                    "note_policy_revision": None, "report_style": "table_first", "note_refs": []}
        if any(snapshot[key] != value for key, value in expected.items()):
            raise ValueError("Disabled memory cannot contain saved context")
    else:
        if (type(snapshot["preference_revision"]) is not int or snapshot["preference_revision"] < 0
                or type(snapshot["note_policy_revision"]) is not int or snapshot["note_policy_revision"] < 0
                or snapshot["preferences_status"] not in {"active", "absent", "expired"}):
            raise ValueError("The memory revision or status is invalid")
        expires = snapshot["preferences_expires_at"]
        if expires is not None and (isinstance(expires, bool) or not isinstance(expires, (int, float)) or not math.isfinite(expires)):
            raise ValueError("The memory preference expiry is invalid")
    seen = set()
    for reference in refs:
        if not isinstance(reference, dict) or set(reference) != REFERENCE_FIELDS:
            raise ValueError("Historical note references must contain metadata only")
        for field in ("note_id", "run_id"):
            if not isinstance(reference[field], str) or not re.fullmatch(r"[0-9a-f]{32}", reference[field]):
                raise ValueError("A historical note identifier is invalid")
        if reference["note_id"] in seen:
            raise ValueError("Historical note references must be unique")
        seen.add(reference["note_id"])
        if (not isinstance(reference["payload_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", reference["payload_hash"])
                or not isinstance(reference["source_fingerprint"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", reference["source_fingerprint"])):
            raise ValueError("Historical note provenance is invalid")
        if (type(reference["current_source"]) is not bool or type(reference["archive_only"]) is not bool
                or reference["current_source"] != (reference["source_fingerprint"] == snapshot["source_fingerprint"])
                or reference["archive_only"] == reference["current_source"]
                or reference["citation"] != "note:" + reference["note_id"] + "@" + reference["payload_hash"]):
            raise ValueError("Historical note citation or archive status changed")
        ref_scope = reference["scope"]
        if not isinstance(ref_scope, dict) or set(ref_scope) != {"tickers", "years"}:
            raise ValueError("Historical note scope is invalid")
        validate_scope(snapshot["actor"], ref_scope["tickers"], ref_scope["years"], 1)
        if (len(ref_scope["tickers"]) > 4 or not set(ref_scope["tickers"]) & set(scope["tickers"])
                or not set(ref_scope["years"]) & set(scope["years"])):
            raise ValueError("Historical note is outside the frozen selection scope")
        if reference["title"] != " / ".join(ref_scope["tickers"]) + " approved research note":
            raise ValueError("Historical note title must be a code-owned scope label")
        created = reference["created_at"]
        if isinstance(created, bool) or not isinstance(created, (int, float)) or not math.isfinite(created) or created < 0:
            raise ValueError("Historical note creation time is invalid")
    return True


def render_memory_history(snapshot):
    """Exact code-owned prose; do not treat it as a financial claim section."""
    validate_snapshot_structure(snapshot)
    if not snapshot["enabled"]:
        return "Analyst memory is off for this research."
    if not snapshot["note_refs"]:
        return "No relevant approved note was selected from local analyst memory."
    lines = ["Earlier approved research is local historical context; current SEC evidence supports this note's claims."]
    for ref in snapshot["note_refs"]:
        status = "archived source snapshot; historical context only" if ref["archive_only"] else "same source snapshot; historical context only"
        lines.append("- " + ref["title"] + ": " + status + ". [" + ref["citation"] + "]")
    return "\n".join(lines)
