"""Memory on vs off (L9 evidence): the same request, run twice to the note gate.

Scores each draft in code:
  previous_note  mentions the previous note (e.g. "#1")
  what_changed   includes the code-computed comparison with the previous note
  peer_table     has a Markdown table (tests the preference "include a peer table")
  verified       numbers verified by the checker
Nothing is published: both runs stop at the analyst's note gate.

    python scripts/run.py memory ["request"]
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv                       # noqa: E402

load_dotenv(ROOT / ".env")

from analystdesk.agent.runtime import run_until_gate  # noqa: E402

REQUEST = ("What changed in Microsoft's and Alphabet's operating margins since our last note? "
           "Cover fiscal 2022-2024.")
OUT = ROOT / "data" / "evaluation" / "results"


def score(body: str, check: dict) -> dict:
    return {
        "previous_note": bool(re.search(r"#\d+", body)),
        # the code-computed comparison lines, wherever the writer placed them
        "what_changed": "Previous note on" in body,
        "peer_table": bool(re.search(r"^\s*\|.+\|\s*$", body, re.M)),
        "verified": f"{check.get('verified', 0)}/{check.get('total', 0)}",
    }


async def run(memory_on: bool, request: str) -> dict:
    from langgraph.types import Command
    rid = f"mem{'on' if memory_on else 'off'}-{int(time.time())}"
    t = time.time()
    r = await run_until_gate(rid, {"request": request, "analyst": "analyst", "memory_on": memory_on},
                             transport="inprocess")
    r = await run_until_gate(rid, Command(resume={"action": "approve", "confirm_years": True}),
                             transport="inprocess")
    v = r["values"]
    body = v.get("draft", {}).get("body", "")
    return {"run_id": rid, "memory_on": memory_on, "seconds": round(time.time() - t),
            "tokens": v.get("tokens", 0), "tool_calls": v.get("tool_calls", 0),
            "memory_used": (v.get("memory") or {}).get("preferences", []),
            **score(body, v.get("check", {}))}


async def main(request: str) -> None:
    results = [await run(True, request), await run(False, request)]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"memory_compare_{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps({"request": request, "results": results}, indent=2), encoding="utf-8")
    print(f"{'':12}{'memory ON':>14}{'memory OFF':>14}")
    for k in ("previous_note", "what_changed", "peer_table", "verified", "tool_calls", "tokens", "seconds"):
        print(f"{k:12}{str(results[0][k]):>14}{str(results[1][k]):>14}")
    print(f"\nruns: {results[0]['run_id']}, {results[1]['run_id']} (open them in the app)\nsaved: {path.name}")


async def rescore(path: Path) -> None:
    """Re-score saved runs (no model calls), e.g. after changing score()."""
    from analystdesk.agent.runtime import get_run
    data = json.loads(path.read_text(encoding="utf-8"))
    for r in data["results"]:
        v = (await get_run(r["run_id"]))["values"]
        r.update(score(v.get("draft", {}).get("body", ""), v.get("check", {})))
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    res = data["results"]
    for k in ("previous_note", "what_changed", "peer_table", "verified"):
        print(f"{k:14}{str(res[0][k]):>12}{str(res[1][k]):>12}")


