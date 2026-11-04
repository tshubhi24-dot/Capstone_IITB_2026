"""Memory evaluation (L9): does long-term memory change the note, correctly and only when it should?

Each case in data/evaluation/memory_cases.jsonl seeds a FRESH memory store (past notes,
preferences, then optional deletions), runs the request with memory ON and with memory OFF
to the note gate (nothing is published), and scores both drafts in code.

Checks for the memory-ON draft (only those the case asks for):
    previous     "Previous note on T: #id" is in the note, for each ticker T
    change       the code-computed comparison has the expected kind per ticker:
                 move (FY2023 last note -> FY2024 now), unchanged, or restated
    heading      the comparison sits under "What changed since our last note"
    no_previous  the note says there is no previous note on T
    sentinel     a preference's exact line appears
    period_end   each company's fiscal-year end date is stated (preference)
    table        a Markdown table is present (preference)
    scope        the plan kept exactly these companies, and no figure placeholder is left
    absent       text that deleted memory would have produced does NOT appear

The memory-OFF draft passes when none of the memory-only text appears in it.

Seeded notes are built from real XBRL figures (figures.build_figures), so their figures
carry verified tags exactly like a published note; "override" changes one value to
simulate a figure restated since the last note.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import memory
from .agent.figures import PLACEHOLDER, build_figures

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "data" / "evaluation" / "memory_cases.jsonl"
SEED_ANALYST = "memeval"
SEED_DATE = "2026-09-01T10:00:00+00:00"

_TABLE = re.compile(r"^\s*\|.+\|\s*$", re.M)
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December")
# lines that only code reading memory can put into a note (the heading "What changed since
# our last note" is not one: the writer may echo it from a request that asks what changed)
MEMORY_ONLY = ("Previous note on", "No previous note on", "Restated since the last note")


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def seeded_note_body(ticker: str, years: list[int], override: dict | None = None) -> str:
    """A note body with the ticker's revenue, income and margin for these years, as tagged text."""
    figures = build_figures([ticker], years)
    parts = []
    for key, f in figures.items():
        if key.rsplit("_", 1)[-1] in ("period_end", "growth", "change"):
            continue
        text = f["text"]
        if override and key in override:   # a different value for the same fact: a restatement
            text = re.sub(r"^\$[\d,]+\.\d", f"${override[key]:,.1f}", text)
        parts.append(f"{key}: {text}.")
    return "\n".join(parts)


async def seed(case: dict, analyst: str = SEED_ANALYST) -> None:
    """Write the case's memory into the current store (memory.MEMORY_DB), then apply deletions."""
    s = case.get("seed", {})
    for note in s.get("notes", []):
        body = seeded_note_body(note["ticker"], note["years"], note.get("override"))
        await memory.remember_published_note(
            note["note_id"], f"Seeded note: {note['ticker']} FY{'-'.join(map(str, note['years']))}",
            body, [note["ticker"]], approver="memeval-seed", analyst=analyst, published_at=SEED_DATE)
    for text in s.get("preferences", []):
        await memory.add_preference(analyst, text)
    for item in s.get("forget", []):
        if item == "preferences":
            for p in await memory.preferences(analyst):
                await memory.forget(("preferences", analyst), p["key"])
        elif item.startswith("note:"):
            _, ticker, note_id = item.split(":")
            await memory.forget(("notes", ticker), f"note-{note_id}")


def _period_ends(companies: list[str], years: list[int]) -> dict[str, list[str]]:
    """Each company's latest period end, in the forms a writer may use."""
    figures = build_figures(companies, years)
    out = {}
    for t in companies:
        keys = sorted(k for k in figures if k.startswith(f"{t}_") and k.endswith("_period_end"))
        if keys:
            iso = figures[keys[-1]]["text"]
            y, m, d = iso.split("-")
            month = _MONTHS[int(m) - 1]
            out[t] = [iso, f"{month} {int(d)}, {y}", f"{int(d)} {month} {y}"]
    return out


def score_on(case: dict, values: dict) -> dict:
    """Score the memory-ON draft. values: the run's state at the note gate."""
    exp = case["expect"]
    body = (values.get("draft") or {}).get("body", "")
    plan = values.get("plan") or {}
    checks: dict[str, bool] = {}
    for t in exp.get("previous", []):
        checks[f"previous:{t}"] = f"Previous note on {t}:" in body
    marker = {"move": "(FY2023, last note) →", "unchanged": "unchanged since the last note",
              "restated": "Restated since the last note"}
    for t, kind in exp.get("change", {}).items():
        # this ticker's lines only: from its "Previous note on" line to the next ticker's
        section = body.split(f"Previous note on {t}:", 1)[-1].split("Previous note on ", 1)[0] \
            if f"Previous note on {t}:" in body else ""
        checks[f"change:{t}={kind}"] = marker[kind] in section
    if exp.get("previous"):
        checks["heading"] = "What changed since our last note" in body
    for t in exp.get("no_previous", []):
        checks[f"no_previous:{t}"] = f"No previous note on {t}" in body
    if exp.get("sentinel"):
        checks["sentinel"] = exp["sentinel"] in body
    if exp.get("period_end"):
        for t, forms in _period_ends(plan.get("companies", []), plan.get("fiscal_years", [])).items():
            checks[f"period_end:{t}"] = any(f in body for f in forms)
    if exp.get("table"):
        checks["table"] = bool(_TABLE.search(body))
    if exp.get("scope"):
        issues = (values.get("check") or {}).get("issues") or []
        checks["scope:plan"] = sorted(plan.get("companies", [])) == sorted(exp["scope"])
        checks["scope:no_placeholder"] = not PLACEHOLDER.search(body) and not any(
            "Unknown placeholder" in i for i in issues)
    for text in exp.get("absent", []):
        checks[f"absent:{text}"] = text not in body
    checks["no_unfilled_slot"] = "{WHAT_CHANGED}" not in body
    return {"success": all(checks.values()), "checks": checks}


def score_off(case: dict, values: dict) -> dict:
    """The memory-OFF draft must contain nothing that only memory could have produced,
    and no unfilled {WHAT_CHANGED} slot."""
    body = (values.get("draft") or {}).get("body", "")
    found = [t for t in MEMORY_ONLY if t in body]
    if case["expect"].get("sentinel") and case["expect"]["sentinel"] in body:
        found.append(case["expect"]["sentinel"])
    if "{WHAT_CHANGED}" in body:
        found.append("{WHAT_CHANGED}")
    return {"success": not found, "memory_text_found": found}


def memory_used(values: dict) -> dict:
    """What the planner read from memory, as recorded in the run's trace."""
    for e in values.get("trace", []):
        if e.get("node") == "plan":
            return e.get("memory_used") or {}
    return {}
