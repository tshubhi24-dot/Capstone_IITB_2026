"""Experiment E2: do the defences work? (L15)

Runs the red-team suite (data/evaluation/redteam/*.jsonl, written by Role 5)
and clean cases, with the defences on or off as an experiment file says:

    python scripts/run_redteam.py --experiment e2_defences_on
    python scripts/run_redteam.py --experiment e2_defences_off
    python scripts/run_redteam.py --experiment e2_defences_on --attacks rt01 rt02 --no-clean

Reported per configuration:
    attack success   attacks that got through (redteam.attack_outcome)
    false blocks     clean, in-scope cases a guardrail stopped something in
    clean success    task success on the clean cases (what the defences cost)
Every attack run stops at the note gate; nothing is published. Memory is off.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["AGENT_EVAL"] = "1"            # memory off, as for every evaluation run

from dotenv import load_dotenv              # noqa: E402

load_dotenv(ROOT / ".env")

from analystdesk import experiments  # noqa: E402
from analystdesk.evaluation import RESULTS, load_cases, run_one, summarise  # noqa: E402
from analystdesk.redteam import load_attacks, run_attack  # noqa: E402


def attack_summary(rows: list[dict]) -> dict:
    by_cat = Counter(r["category"] for r in rows)
    hit = Counter(r["category"] for r in rows if r["success"])
    return {"attacks": len(rows), "succeeded": sum(r["success"] for r in rows),
            "attack_success_pct": round(100 * sum(r["success"] for r in rows) / len(rows), 1) if rows else None,
            "errors": sum(1 for r in rows if r.get("error")),
            "by_category": {c: f"{hit[c]}/{n}" for c, n in sorted(by_cat.items())}}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", required=True, help="e2_defences_on or e2_defences_off (experiments/)")
    ap.add_argument("--configs", nargs="+", choices=["c1", "c2"])
    ap.add_argument("--attacks", nargs="*", help="only these attack ids")
    ap.add_argument("--no-clean", action="store_true", help="skip the clean cases (no false-block figure)")
    ap.add_argument("--tag")
    args = ap.parse_args()
    exp = experiments.load(args.experiment)
    if exp["runner"] != "redteam":
        ap.error(f"{exp['file']} is an eval experiment: use scripts/run_eval.py")
    experiments.apply(exp)
    configs = args.configs or exp["configs"]
    tag = args.tag or f"{Path(exp['file']).stem}-{time.strftime('%Y%m%d-%H%M%S')}"

    attacks = [a for a in load_attacks() if not args.attacks or a["id"] in args.attacks]
    if not attacks:
        ap.error("no attacks found in data/evaluation/redteam/ (Role 5 writes them; see its README)")
    clean = [] if args.no_clean else [c for c in load_cases(exp["split"]) if c["type"] != "refusal"]

    path = RESULTS / f"redteam_{tag}.json"
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = {"experiment": {"file": exp["file"], "name": exp["name"], "env": exp["env"]}, "tag": tag,
           "attacks": {}, "clean": {}, "summary": {}}
    for config in configs:
        rows = []
        for a in attacks:
            r = await run_attack(a, config, tag)
            rows.append(r)
            print(f"{config} {a['id']:6} {a['category']:22} {'GOT THROUGH' if r['success'] else 'stopped    '} "
                  f"{r['seconds']:6.1f}s  {'; '.join(r['reasons'] or r['blocked_by'])[:90]}", flush=True)
        clean_rows = []
        for case in clean:
            r = await run_one(config, case, tag)
            clean_rows.append(r)
            print(f"{config} {case['id']:6} clean {'PASS' if r['success'] else 'fail'}  "
                  f"{'blocked: ' + '; '.join(r['blocks'])[:80] if r.get('blocks') else ''}", flush=True)
        out["attacks"][config], out["clean"][config] = rows, clean_rows
        out["summary"][config] = {**attack_summary(rows),
                                  "clean": summarise(clean_rows) if clean_rows else None}
        path.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"\n{exp['name']}")
    for config, s in out["summary"].items():
        c = s["clean"] or {}
        print(f"{config}: attacks got through {s['succeeded']}/{s['attacks']} ({s['attack_success_pct']}%)  "
              f"by category {s['by_category']}  |  clean cases: false blocks {c.get('false_blocks', '-')}"
              f"/{c.get('cases', '-')}, task success {c.get('success', '-')}/{c.get('cases', '-')}")
    print(f"\nsaved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
