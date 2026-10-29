"""Reflexion playbook (L12): lessons learned from development runs.

Lifecycle of a lesson:
    pending   written by the reflection step (scripts/reflect.py) from a
              failure on a DEVELOPMENT case: a critic rejection, an unverified
              number, a missing citation, a wrong refusal...
    approved  a person accepted it in the app (Research tab, C1/C2 → Playbook)
    rejected  a person rejected it, with a reason (kept as evidence)

Rules (brief, L12):
  * lessons come only from development cases, never held-out ones;
  * every lesson is reviewed by a person before it can be used;
  * only lessons relevant to the current request are retrieved (top 3);
  * the playbook is frozen before the held-out run: once frozen, no lesson
    can be approved, rejected or added until it is unfrozen on purpose.

Lessons live in the same LangGraph store as memory, in namespace
("lessons", <status>), so they persist across runs and can be inspected.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from .memory import open_store

STATUSES = ("pending", "approved", "rejected")
_WORD = re.compile(r"[a-z]{3,}")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "when", "what", "how", "its", "are",
         "was", "were", "has", "have", "into", "than", "then", "their", "between", "compare"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def is_frozen() -> bool:
    async with open_store() as s:
        item = await s.aget(("lessons", "meta"), "playbook")
    return bool(item and item.value.get("frozen"))


async def set_frozen(frozen: bool, who: str) -> None:
    async with open_store() as s:
        await s.aput(("lessons", "meta"), "playbook", {"frozen": frozen, "by": who, "at": _now()})


async def add_pending(lesson: dict) -> str | None:
    """lesson: {"when", "do", "applies_to": [tags], "source_case", "source_issue"}."""
    if await is_frozen():
        return None
    key = uuid.uuid4().hex[:8]
    async with open_store() as s:
        await s.aput(("lessons", "pending"), key, {**lesson, "created_at": _now()})
    return key


async def list_lessons(status: str) -> list[dict]:
    async with open_store() as s:
        items = await s.asearch(("lessons", status), limit=200)
    return sorted(({"key": i.key, **i.value} for i in items), key=lambda v: v["created_at"])


async def review(key: str, approve: bool, reviewer: str, reason: str = "") -> bool:
    """Move a pending lesson to approved or rejected. False if frozen or not found."""
    if await is_frozen():
        return False
    async with open_store() as s:
        item = await s.aget(("lessons", "pending"), key)
        if item is None:
            return False
        status = "approved" if approve else "rejected"
        await s.aput(("lessons", status), key,
                     {**item.value, "reviewed_by": reviewer, "reviewed_at": _now(), "review_reason": reason})
        await s.adelete(("lessons", "pending"), key)
    return True


def _terms(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


async def relevant(request: str, case_type: str | None = None, k: int = 3) -> list[dict]:
    """Approved lessons most relevant to this request (tag and word overlap)."""
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
