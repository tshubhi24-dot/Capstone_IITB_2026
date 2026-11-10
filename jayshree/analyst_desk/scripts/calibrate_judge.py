"""Calibrate the judge against human labels with Cohen's kappa (L13).

The compliance critic's judge (a different model family) decides whether a
cited passage supports a claim. Before trusting it, compare it with people:

  1. sample   python scripts/calibrate_judge.py sample [--n 30]
              -> data/evaluation/judge_labels.csv: claim, passage(s), and an
                 empty `human` column. The judge's verdict is NOT shown.
  2. label    a person fills `human` with yes / no for every row
              (ideally role 5, not the person who built the critic)
  3. score    python scripts/calibrate_judge.py score
              -> runs the judge on the same rows, prints agreement and
                 Cohen's kappa, saves data/evaluation/results/judge_calibration.json

Kappa corrects raw agreement for agreement expected by chance:
    kappa = (p_observed - p_chance) / (1 - p_chance)
Rough reading: < 0.4 poor, 0.4-0.6 moderate, 0.6-0.8 substantial, > 0.8 strong.
"""

from __future__ import annotations

import asyncio
import csv
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv     # noqa: E402

load_dotenv(ROOT / ".env")

LABELS = ROOT / "data" / "evaluation" / "judge_labels.csv"
OUT = ROOT / "data" / "evaluation" / "results" / "judge_calibration.json"


async def sample(n: int) -> None:
    from analystdesk.agent.checks import PASSAGE_ID
    from analystdesk.agent.runtime import get_run, list_runs, passage_text
    rows = []
    for r in await list_runs(limit=200):
        v = (await get_run(r["run_id"]))["values"]
        body = (v.get("draft") or {}).get("body", "")
        for line in body.splitlines():
            pids = PASSAGE_ID.findall(line)
            claim = re.sub(r"\[(fact|calc|growth|diff):[^\]]*\]", "", line).strip(" -*#")
            if pids and len(claim) > 30:
                rows.append({"run_id": r["run_id"], "claim": claim[:500], "passage_ids": " ".join(pids[:2]),
                             "passages": "\n---\n".join((passage_text(p) or "")[:900] for p in pids[:2]),
                             "human": ""})
    random.Random(42).shuffle(rows)
    seen, picked = set(), []
    for row in rows:
        if row["claim"] not in seen:
            seen.add(row["claim"])
            picked.append(row)
        if len(picked) >= n:
            break
    with LABELS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(picked[0]))
        w.writeheader()
        w.writerows(picked)
    print(f"Wrote {len(picked)} rows to {LABELS.relative_to(ROOT)}. Fill the 'human' column with yes/no.")


def cohen_kappa(a: list[bool], b: list[bool]) -> float | None:
    """None when kappa is undefined: both raters gave one label to every row (chance
    agreement is 1), so agreement says nothing about the judge. Reported as such."""
    n = len(a)
    p_obs = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    p_chance = pa * pb + (1 - pa) * (1 - pb)
    return None if p_chance == 1 else (p_obs - p_chance) / (1 - p_chance)


async def score() -> None:
    from analystdesk.agent.runtime import passage_text
    from analystdesk.agent.team import make_judge, make_judge_llm
    from analystdesk.llm_config import LLM_CONFIG
    rows = list(csv.DictReader(LABELS.open(encoding="utf-8")))
    labelled = [r for r in rows if r["human"].strip().lower() in ("yes", "no")]
    if len(labelled) < 20:
        sys.exit(f"Only {len(labelled)} rows labelled; label at least 20 (yes/no) first.")
    critic = make_judge(make_judge_llm(), passage_text)
    human, judge, unavailable = [], [], 0
    for r in labelled:
        # one claim at a time, with the same passage(s) the person labelled it against
        cites = " ".join(f"[{p}]" for p in r["passage_ids"].split())
        verdict = await critic(f"{r['claim']} {cites}")
        if verdict.get("reviewed") != 1:   # no valid verdict: incomplete, not a "no"
            unavailable += 1
            continue
        human.append(r["human"].strip().lower() == "yes")
        judge.append(verdict.get("supported") == 1)
    if len(human) < 20:
        sys.exit(f"Only {len(human)} rows got a judge verdict ({unavailable} unavailable); need at least 20.")
    agree = sum(h == j for h, j in zip(human, judge)) / len(human)
    kappa = cohen_kappa(human, judge)
    result = {"judge_model": LLM_CONFIG.model("judge"), "n": len(human), "judge_unavailable": unavailable,
              "agreement": round(agree, 3),
              "cohen_kappa": round(kappa, 3) if kappa is not None else None,
              "kappa_note": None if kappa is not None else "undefined: every row got the same label",
              "confusion": {"both_yes": sum(h and j for h, j in zip(human, judge)),
                            "both_no": sum(not h and not j for h, j in zip(human, judge)),
                            "human_yes_judge_no": sum(h and not j for h, j in zip(human, judge)),
                            "human_no_judge_yes": sum(not h and j for h, j in zip(human, judge))}}
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sample"
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 30
    asyncio.run(sample(n) if cmd == "sample" else score())
