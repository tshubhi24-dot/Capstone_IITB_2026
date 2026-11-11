"""Long-term memory (L9): analyst preferences, coverage list, past-note memory.

Stored in a LangGraph store (SQLite, data/memory/memory.sqlite), separate
from the run checkpointer: checkpoints are one run's working state, the
store is what the desk remembers across runs. See docs/memory_policy.md.

    ("preferences", analyst)  key=<id>     {"text", "added_at"}
    ("coverage", analyst)     key=<ticker> {"ticker", "notes", "last_note_id", "last_published"}
    ("notes", <ticker>)       key=note-<id> {"note_id", "title", "published_at", "approver",
                                             "figures": {"<metric>_<year>": {"value", "unit", "text"}}}
    ("watchlist", analyst)    key=tickers  {"tickers", "updated_at"}   local guardrail context
                                           sees it, and the hooks keep it out of every tool call
    ("suppressed", "notes")   key=note-<id> {"note_id", "at"}  past-note memories the analyst
                                           deleted, so a backfill does not restore them

Past-note figures are parsed from the published note's own [fact: ...] and
[calc: ...] tags — numbers code already verified — so memory never holds an
unverified number. Only published (analyst-approved) notes are remembered.
"""

from __future__ import annotations

import contextlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DB = Path(os.getenv("MEMORY_DB", ROOT / "data" / "memory" / "memory.sqlite"))

_FACT = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)M\s*\[fact:\s*([A-Za-z]+)/(\d{4})/([\d-]+)\s*\]")
_CALC = re.compile(r"(-?[\d.]+)%\s*\[calc:\s*([A-Za-z]+)/(\d{4})/([\d-]+)\s*/\s*[A-Za-z]+/\d{4}/[\d-]+\s*\]")
_CALC_IDS = re.compile(r"\[calc:\s*([A-Za-z]+/\d{4}/[\d-]+)\s*/\s*([A-Za-z]+/\d{4}/[\d-]+)\s*\]")
_METRIC = {
    "OperatingIncomeLoss": "operating_income",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest":
        "pretax_income",
}


def _metric(concept: str) -> str:
    return _METRIC.get(concept, "revenue" if "Revenue" in concept else concept)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextlib.asynccontextmanager
async def open_store():
    from langgraph.store.sqlite.aio import AsyncSqliteStore
    MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteStore.from_conn_string(str(MEMORY_DB)) as store:
        await store.setup()
        yield store


def figures_from_note(body: str) -> dict[str, dict]:
    """{ticker: {"<metric>_<year>": {"value", "unit", "text"}}} from a note's verified tags."""
    from .servers.edgar_server import get_fact
    out: dict[str, dict] = {}

    def ticker_of(concept, year, accn):
        r = get_fact(f"{concept}/{year}/{accn}")
        return r.ticker if r.ok else None

    for m in _FACT.finditer(body):
        t = ticker_of(m.group(2), m.group(3), m.group(4))
        if t:
            out.setdefault(t, {})[f"{_metric(m.group(2))}_{m.group(3)}"] = {
                "value": float(m.group(1).replace(",", "")), "unit": "$M", "text": m.group(0)}
    for m in _CALC.finditer(body):
        t = ticker_of(m.group(2), m.group(3), m.group(4))
        if t:
            out.setdefault(t, {})[f"margin_{m.group(3)}"] = {
                "value": float(m.group(1)), "unit": "%", "text": m.group(0)}
    return out


# ── preferences ───────────────────────────────────────────────────────────────

async def add_preference(analyst: str, text: str) -> str:
    key = uuid.uuid4().hex[:8]
    async with open_store() as s:
        await s.aput(("preferences", analyst), key, {"text": text.strip(), "added_at": _now()})
    return key


async def preferences(analyst: str) -> list[dict]:
    async with open_store() as s:
        items = await s.asearch(("preferences", analyst), limit=50)
    return [{"key": i.key, **i.value} for i in sorted(items, key=lambda i: i.value["added_at"])]


# ── private watchlist ─────────────────────────────────────────────────────────

async def watchlist(analyst: str) -> list[str]:
    async with open_store() as s:
        item = await s.aget(("watchlist", analyst), "tickers")
    return list(item.value["tickers"]) if item else []


async def set_watchlist(analyst: str, tickers: list[str]) -> list[str]:
    """Replace the analyst's watchlist; only covered tickers are kept. Empty clears it."""
    from .scope import COMPANIES
    covered = {c.ticker for c in COMPANIES}
    kept = sorted({t.strip().upper() for t in tickers} & covered)
    async with open_store() as s:
        if kept:
            await s.aput(("watchlist", analyst), "tickers", {"tickers": kept, "updated_at": _now()})
        else:
            await s.adelete(("watchlist", analyst), "tickers")
    return kept


# ── notes and coverage ────────────────────────────────────────────────────────

async def remember_published_note(note_id: int, title: str, body: str, tickers: list[str],
                                  approver: str, analyst: str, published_at: str | None = None) -> dict:
    """Called only after publish_note succeeded (i.e. after analyst approval).
    A note the analyst deleted from memory is not remembered again (returns {})."""
    published_at = published_at or _now()
    figures = figures_from_note(body)
    async with open_store() as s:
        if await s.aget(("suppressed", "notes"), f"note-{note_id}"):
            return {}
        for t in tickers:
            t = t.upper()
            await s.aput(("notes", t), f"note-{note_id}", {
                "note_id": note_id, "title": title, "published_at": published_at,
                "approver": approver, "figures": figures.get(t, {})})
            prev = await s.aget(("coverage", analyst), t)
            notes = (prev.value.get("notes", []) if prev else []) + [note_id]
            await s.aput(("coverage", analyst), t, {
                "ticker": t, "notes": sorted(set(notes)), "last_note_id": note_id,
                "last_published": published_at})
    return figures


async def last_note(ticker: str) -> dict | None:
    async with open_store() as s:
        items = await s.asearch(("notes", ticker.upper()), limit=100)
    from .servers.portal import inactive_note_ids
    inactive = inactive_note_ids()
    usable = [i.value for i in items if i.value["note_id"] not in inactive]
    if not usable:
        return None
    return max(usable, key=lambda v: (v["published_at"], v["note_id"]))


async def coverage(analyst: str) -> list[dict]:
    async with open_store() as s:
        items = await s.asearch(("coverage", analyst), limit=100)
    from .servers.portal import inactive_note_ids
    inactive = inactive_note_ids()
    out = []
    for item in items:
        value = item.value
        notes = [note_id for note_id in value.get("notes", []) if note_id not in inactive]
        if notes:
            async with open_store() as s:
                memories = await s.asearch(("notes", value["ticker"].upper()), limit=100)
            eligible = [entry.value for entry in memories if entry.value["note_id"] in notes]
            latest = max(eligible, key=lambda v: (v["published_at"], v["note_id"])) if eligible else None
            out.append({**value, "notes": notes, "last_note_id": max(notes),
                        "last_published": latest["published_at"] if latest else None})
    return sorted(out, key=lambda v: v["ticker"])


async def all_note_memories() -> list[dict]:
    async with open_store() as s:
        namespaces = await s.alist_namespaces(prefix=("notes",), limit=200)
        out = []
        for ns in namespaces:
            for i in await s.asearch(ns, limit=100):
                out.append({"ticker": ns[1], "key": i.key, **i.value})
    from .servers.portal import inactive_note_ids
    inactive = inactive_note_ids()
    return sorted((v for v in out if v["note_id"] not in inactive),
                  key=lambda v: (v["published_at"], v["note_id"]), reverse=True)


async def forget(namespace: tuple[str, ...], key: str) -> str:
    """Delete one memory item (policy: the analyst can delete anything stored).

    Deleting a past-note memory also takes the note off every coverage list and
    records it as deleted, so a later backfill or memory sync does not bring it
    back. Returns what was removed and what was not (shown to the analyst).
    """
    async with open_store() as s:
        await s.adelete(namespace, key)
        if namespace[0] != "notes":
            return f"Removed this {namespace[0].rstrip('s')} from memory; later runs no longer use it."
        note_id = int(key.split("-", 1)[1])
        await s.aput(("suppressed", "notes"), key, {"note_id": note_id, "at": _now()})
        for ns in await s.alist_namespaces(prefix=("coverage",), limit=200):
            item = await s.aget(ns, namespace[1])
            if item and note_id in item.value.get("notes", []):
                notes = [n for n in item.value["notes"] if n != note_id]
                if notes:
                    await s.aput(ns, namespace[1], {**item.value, "notes": notes, "last_note_id": max(notes)})
                else:
                    await s.adelete(ns, namespace[1])
    return (f"Removed note #{note_id} on {namespace[1]} from memory and coverage; later runs will not compare "
            "against it and a backfill will not restore it. The published note itself stays in the portal, "
            "and saved runs that already used it are not changed.")


async def suppressed_notes() -> set[int]:
    async with open_store() as s:
        return {i.value["note_id"] for i in await s.asearch(("suppressed", "notes"), limit=1000)}


# ── what changed (computed by code) ───────────────────────────────────────────

def what_changed(ticker: str, previous: dict, current: dict) -> list[str]:
    """Lines comparing the previous note's latest-year figures with the current ones.

    current: {"<metric>_<year>": {"value", "unit", "text"}} for this ticker.
    Values carry their verified source tags; margin moves are in percentage
    points ("pp"), computed here, not by the model.
    """
    prev_figs = previous.get("figures", {})
    lines = [f"Previous note on {ticker}: #{previous['note_id']} \"{previous['title']}\" "
             f"({previous['published_at'][:10]})."]
    for metric in ("margin", "revenue", "operating_income", "pretax_income"):
        p_keys = sorted(k for k in prev_figs if k.startswith(metric + "_"))
        c_keys = sorted(k for k in current if k.startswith(metric + "_"))
        if not p_keys or not c_keys:
            continue
        p, c = prev_figs[p_keys[-1]], current[c_keys[-1]]
        p_year, c_year = p_keys[-1].rsplit("_", 1)[1], c_keys[-1].rsplit("_", 1)[1]
        label = metric.replace("_", " ")
        if p_year == c_year and abs(p["value"] - c["value"]) < 1e-9:
            lines.append(f"{label} FY{c_year}: unchanged since the last note at {c['text']}.")
        elif p_year == c_year:
            # same fiscal year, different value: a different presentation, not a business change.
            # Code cannot tell a restatement from a recast or reclassification, so it does not say which.
            lines.append(f"{label} FY{c_year}: the last note reported {p['text']}; the value now "
                         f"reported is {c['text']}. The figure for the same year differs between the two "
                         f"notes (a later presentation, not a change in the business); this note uses "
                         f"the current value.")
        elif metric == "margin":
            # the move in percentage points, with a [diff] tag the checker verifies
            ids_p, ids_c = _CALC_IDS.findall(p["text"]), _CALC_IDS.findall(c["text"])
            move = (f"{c['value'] - p['value']:+.2f} pp [diff: {ids_c[0][0]} / {ids_c[0][1]} - "
                    f"{ids_p[0][0]} / {ids_p[0][1]}]") if ids_p and ids_c else "moved"
            lines.append(f"{label}: {p['text']} (FY{p_year}, last note) → {c['text']} (FY{c_year}), {move}.")
        else:
            lines.append(f"{label}: {p['text']} (FY{p_year}, last note) → {c['text']} (FY{c_year}).")
    return lines
