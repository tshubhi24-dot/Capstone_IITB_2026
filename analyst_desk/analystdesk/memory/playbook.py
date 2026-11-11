"""Reflexion playbook (L12): lessons learned from development runs.

Lifecycle of a lesson:
    pending   written by the reflection step (scripts/run.py reflect) from a
              failure on a DEVELOPMENT case: a critic rejection, an unverified
              number, a missing citation, a wrong refusal...
    approved  a person accepted it in the app (Research tab, C1/C2 â†’ Playbook)
    rejected  a person rejected it, with a reason (kept as evidence)

Rules (brief, L12):
  * lessons come only from development cases, never held-out ones;
  * every lesson is reviewed by a person before it can be used;
  * only lessons relevant to the current request are retrieved (top 3);
  * the playbook is frozen before the held-out run: once frozen, no lesson
    can be approved, rejected or added until it is unfrozen on purpose, and
    runs use a snapshot taken at the freeze, identified by a version hash.
  * exact normalized duplicates share one review status and retain their sources;
    conflicting legacy decisions return the lesson to pending review.

Lessons live in the same LangGraph store as memory, in namespace
("lessons", <status>), so they persist across runs and can be inspected.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid

from analystdesk.memory.store import open_store, _now

STATUSES = ("pending", "approved", "rejected")
_WORD = re.compile(r"[a-z]{3,}")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "when", "what", "how", "its", "are",
         "was", "were", "has", "have", "into", "than", "then", "their", "between", "compare"}




def _normalized_text(value: str) -> str:
    return " ".join(value.split()).casefold().rstrip(" .!?")


def _fingerprint(lesson: dict) -> tuple[str, str, tuple[str, ...]]:
    tags = tuple(sorted({_normalized_text(tag) for tag in lesson.get("applies_to", [])}))
    return _normalized_text(lesson.get("when", "")), _normalized_text(lesson.get("do", "")), tags


def _source_cases(lesson: dict) -> list[dict]:
    sources = list(lesson.get("source_cases", []))
    if lesson.get("source_case") or lesson.get("source_config") or lesson.get("source_issue"):
        sources.append({
            "source_case": lesson.get("source_case", ""),
            "source_config": lesson.get("source_config", ""),
            "source_issue": lesson.get("source_issue", ""),
        })
    unique = {}
    for source in sources:
        normalized = {
            "source_case": source.get("source_case", ""),
            "source_config": source.get("source_config", ""),
            "source_issue": source.get("source_issue", ""),
        }
        key = tuple(normalized.values())
        unique[key] = normalized
    return list(unique.values())


def _review_history(lesson: dict, status: str) -> list[dict]:
    history = list(lesson.get("review_history", []))
    if status in ("approved", "rejected") and lesson.get("reviewed_at"):
        entry = {
            "status": status,
            "reviewed_by": lesson.get("reviewed_by", ""),
            "reviewed_at": lesson["reviewed_at"],
            "review_reason": lesson.get("review_reason", ""),
        }
        if entry not in history:
            history.append(entry)
    return history


async def _all_lessons(store) -> list[tuple[str, str, dict]]:
    rows = []
    for status in STATUSES:
        items = await store.asearch(("lessons", status), limit=1000)
        rows.extend((status, item.key, dict(item.value)) for item in items)
    return rows


async def _deduplicate(store) -> None:
    groups: dict[tuple[str, str, tuple[str, ...]], list[tuple[str, str, dict]]] = {}
    for row in await _all_lessons(store):
        groups.setdefault(_fingerprint(row[2]), []).append(row)

    for entries in groups.values():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda row: (row[2].get("created_at", ""), row[1]))
        statuses = {row[0] for row in entries}
        target_status = statuses.pop() if len(statuses) == 1 else "pending"
        canonical_key = next(
            (key for status, key, _ in entries if status == "pending"),
            entries[0][1],
        )
        canonical = dict(entries[0][2])
        sources = []
        history = []
        for status, _, value in entries:
            sources.extend(_source_cases(value))
            for item in _review_history(value, status):
                if item not in history:
                    history.append(item)
        canonical["source_cases"] = _source_cases({"source_cases": sources})
        canonical["review_history"] = history
        canonical["created_at"] = min(
            (value.get("created_at", "") for _, _, value in entries), default=""
        )
        if target_status == "pending":
            canonical.pop("reviewed_by", None)
            canonical.pop("reviewed_at", None)
            canonical.pop("review_reason", None)
        else:
            latest_review = max(
                (item for item in history if item["status"] == target_status),
                key=lambda item: item["reviewed_at"],
                default=None,
            )
            if latest_review:
                canonical.update({
                    "reviewed_by": latest_review["reviewed_by"],
                    "reviewed_at": latest_review["reviewed_at"],
                    "review_reason": latest_review["review_reason"],
                })
        for status, key, _ in entries:
            await store.adelete(("lessons", status), key)
        await store.aput(("lessons", target_status), canonical_key, canonical)


async def is_frozen() -> bool:
    async with open_store() as s:
        item = await s.aget(("lessons", "meta"), "playbook")
    return bool(item and item.value.get("frozen"))


async def set_frozen(frozen: bool, who: str) -> None:
    """Freezing takes a snapshot of the approved lessons with a version hash. A frozen
    playbook's runs read only that snapshot, so the lessons cannot change during an
    evaluation even if the store does; results record the version they used."""
    meta = {"frozen": frozen, "by": who, "at": _now()}
    if frozen:
        snapshot = await list_lessons("approved")
        meta["lessons"] = snapshot
        meta["version"] = hashlib.sha256(
            json.dumps([[les["key"], les["when"], les["do"], sorted(les.get("applies_to", []))]
                        for les in snapshot], sort_keys=True).encode()).hexdigest()[:12]
    async with open_store() as s:
        await s.aput(("lessons", "meta"), "playbook", meta)


async def frozen_playbook() -> dict | None:
    """{"version", "lessons", "by", "at"} of the frozen snapshot, or None when not frozen."""
    async with open_store() as s:
        item = await s.aget(("lessons", "meta"), "playbook")
    if not (item and item.value.get("frozen")):
        return None
    return {k: item.value.get(k) for k in ("version", "lessons", "by", "at")}


async def add_pending(lesson: dict) -> str | None:
    """lesson: {"when", "do", "applies_to": [tags], "source_case", "source_issue"}."""
    if await is_frozen():
        return None
    async with open_store() as s:
        await _deduplicate(s)
        fingerprint = _fingerprint(lesson)
        for status, key, value in await _all_lessons(s):
            if _fingerprint(value) == fingerprint:
                sources = _source_cases(value) + _source_cases(lesson)
                value["source_cases"] = _source_cases({"source_cases": sources})
                await s.aput(("lessons", status), key, value)
                return None
        key = uuid.uuid4().hex[:8]
        await s.aput(("lessons", "pending"), key, {**lesson, "created_at": _now()})
    return key


async def list_lessons(status: str) -> list[dict]:
    async with open_store() as s:
        await _deduplicate(s)
        items = await s.asearch(("lessons", status), limit=200)
    return sorted(({"key": i.key, **i.value} for i in items), key=lambda v: v["created_at"])


async def review(key: str, approve: bool, reviewer: str, reason: str = "") -> bool:
    """Move a pending lesson to approved or rejected. False if frozen or not found."""
    if await is_frozen():
        return False
    async with open_store() as s:
        await _deduplicate(s)
        item = await s.aget(("lessons", "pending"), key)
        if item is None:
            return False
        fingerprint = _fingerprint(item.value)
        status = "approved" if approve else "rejected"
        value = dict(item.value)
        history = _review_history(value, "pending")
        history.append({
            "status": status,
            "reviewed_by": reviewer,
            "reviewed_at": _now(),
            "review_reason": reason,
        })
        value.update({
            "reviewed_by": reviewer,
            "reviewed_at": history[-1]["reviewed_at"],
            "review_reason": reason,
            "review_history": history,
        })
        for existing_status, existing_key, existing_value in await _all_lessons(s):
            if _fingerprint(existing_value) == fingerprint:
                await s.adelete(("lessons", existing_status), existing_key)
        await s.aput(("lessons", status), key, value)
    return True


def _terms(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


async def relevant(request: str, case_type: str | None = None, k: int = 3) -> list[dict]:
    """Approved lessons most relevant to this request (tag and word overlap).
    From the frozen snapshot when the playbook is frozen."""
    frozen = await frozen_playbook()
    if frozen and frozen.get("lessons") is not None:
        lessons = frozen["lessons"]
    else:   # not frozen, or frozen before snapshots existed
        lessons = await list_lessons("approved")
    req = _terms(request)
    scored = []
    for les in lessons:
        tags = {t.lower() for t in les.get("applies_to", [])}
        score = 3 * len(tags & (req | ({case_type} if case_type else set())))
        score += len(req & _terms(les["when"] + " " + les["do"]))
        if "general" in tags:
            score += 1
        if score > 0:
            scored.append((score, les))
    return [les for _, les in sorted(scored, key=lambda x: -x[0])[:k]]


def as_prompt(lessons: list[dict]) -> str:
    if not lessons:
        return ""
    return "\nLESSONS FROM REVIEWED PAST RUNS (apply when they fit):\n" + "\n".join(
        f"- When {les['when'].rstrip('.')}: {les['do']}" for les in lessons)
