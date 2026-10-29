"""Reflection step (L12): turn development-run failures into pending lessons.

Reads an evaluation results file (scripts/run_eval.py) for the DEV split,
collects what went wrong in each agent run — failed scoring, critic issues
left at the note gate, critic rejections that forced revisions — and asks
the model to write ONE short lesson per distinct problem:
    "When <situation>, <what to do instead>", with tags saying when it applies.
Lessons are stored as PENDING: a person must approve each one in the app
(Research tab → select C1 or C2 → 📘 Playbook) before any run can use it.

    python scripts/reflect.py data/evaluation/results/eval_dev_<tag>.json
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv            # noqa: E402

load_dotenv(ROOT / ".env")

from pydantic import BaseModel, Field     # noqa: E402

from analystdesk import lessons           # noqa: E402

REFLECT = """ROLE: You are a senior equity research editor running a post-mortem.
CONTEXT: An AI research desk drafted a note for the REQUEST below. Code checks and a reviewer
flagged the PROBLEMS listed. Numbers in notes are inserted by code from placeholders; quoted
numbers must appear, with unit, in the cited filing passage; no investment advice is allowed.
TASK: Write at most 2 short, reusable lessons that would prevent these problems next time.
CONSTRAINTS: Each lesson must state WHEN it applies (a situation, not this exact case) and WHAT
to do instead. General enough to help on unseen questions; specific enough to act on. Do not
mention case ids. No lesson if the problems are not worth one.
FORMAT: lessons: [{when, do, applies_to}] where applies_to is 1-4 lowercase tags from:
numeric, comparison, risk_change, refusal, bank, tech, margin, growth, risk, citation, quote,
fiscal-year, general, or a ticker.
EXAMPLE: {"when": "comparing companies with different fiscal year ends",
"do": "state each company's period end next to its figures", "applies_to": ["comparison", "fiscal-year"]}"""


class Lesson(BaseModel):
    when: str
    do: str
    applies_to: list[str] = Field(default_factory=list)


class Lessons(BaseModel):
    lessons: list[Lesson] = Field(default_factory=list)


async def problems_of(row: dict) -> list[str]:
    """What went wrong in one agent run (from its score and saved trace)."""
    from analystdesk.agent.runtime import get_run
    probs = []
    if not row["success"]:
        probs.append(f"Scoring: {row['reason']}")
    if row.get("run_id"):
        v = (await get_run(row["run_id"]))["values"]
        for e in v.get("trace", []):
            if e.get("node") in ("check", "critic") and e.get("issues"):
                probs += [f"Critic (revision {i}): {iss}" for i, iss in enumerate(e["issues"][:4])]
    return list(dict.fromkeys(probs))[:10]


async def main(path: Path) -> None:
    from langchain_core.messages import HumanMessage, SystemMessage
    from analystdesk.agent.runtime import make_llm
    from analystdesk.evaluation import load_cases
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["split"] != "dev":
        sys.exit("Lessons may only be learned from DEVELOPMENT runs.")
    cases = {c["id"]: c for c in load_cases("dev")}
    llm = make_llm().with_structured_output(Lessons)
    added = 0
    for config, rows in data["rows"].items():
        if config == "c0":
            continue   # C0 has no agent to learn
        for row in rows:
            probs = await problems_of(row)
            if not probs:
                continue
            out: Lessons = await llm.ainvoke([
                SystemMessage(REFLECT),
                HumanMessage(f"REQUEST: {cases[row['id']]['request']}\nPROBLEMS:\n- " + "\n- ".join(probs))])
            for les in out.lessons[:2]:
                key = await lessons.add_pending({**les.model_dump(), "source_case": row["id"],
                                                 "source_config": config, "source_issue": probs[0][:300]})
                if key:
                    added += 1
                    print(f"pending {key}  [{row['id']}/{config}]  When {les.when}: {les.do}  {les.applies_to}")
    print(f"\n{added} pending lessons. Review them in the app: Research tab (C1/C2) → 📘 Playbook.")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
