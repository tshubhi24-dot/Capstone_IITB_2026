"""Run C0 / C1 / C2 on golden cases and report (L13; experiment E1).

Each case runs as an analyst would use the system, without publishing:
  C0  fixed pipeline: one retrieval, one model call
  C1  single agent    plan gate auto-approved, stops at the note gate
  C2  team            same
Memory is forced off (AGENT_EVAL=1) so every run starts equal and held-out
cases can never benefit from earlier runs. Same model and tools for all.

Reported per configuration (evaluation protocol): task success, policy
violations, numbers verified, refusals, errors and timeouts, tokens and cost
per case, median and 95th-percentile latency.

    python scripts/run_eval.py --configs c0 c1 c2 --split dev
    python scripts/run_eval.py --configs c2 --split dev --cases d01 d14
    python scripts/run_eval.py --configs c1 c2 --split heldout --no-lessons    # E3 before
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["AGENT_EVAL"] = "1"            # memory off for every evaluation run

from dotenv import load_dotenv              # noqa: E402

load_dotenv(ROOT / ".env")

from analystdesk.evaluation import (  # noqa: E402
    PRICE_PER_M, RESULTS, evaluation_gate_failures, load_cases, run_one, summarise,
)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", default=["c0", "c1", "c2"], choices=["c0", "c1", "c2"])
    ap.add_argument("--split", default="dev", choices=["dev", "heldout"])
    ap.add_argument("--cases", nargs="*", help="only these case ids")
    ap.add_argument("--tag", default=time.strftime("%Y%m%d-%H%M%S"))
    ap.add_argument("--no-lessons", action="store_true", help="E3 'before playbook' run")
    ap.add_argument(
        "--min-success-rate",
        type=float,
        help="fail if task success is below this fraction (for example, 0.95)",
    )
    ap.add_argument(
        "--min-cases",
        type=int,
        default=1,
        help="fail if fewer than this many cases were evaluated",
    )
    args = ap.parse_args()
    if args.no_lessons:
        os.environ["AGENT_LESSONS"] = "0"
    cases = [c for c in load_cases(args.split) if not args.cases or c["id"] in args.cases]
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"eval_{args.split}_{args.tag}.json"
    all_rows: dict[str, list] = {}
    for config in args.configs:
        rows = []
        for case in cases:
            r = await run_one(config, case, args.tag)
            rows.append(r)
            print(f"{config} {case['id']:4} {'PASS' if r['success'] else 'fail'}  {r['seconds']:6.1f}s  "
                  f"tokens {r.get('tokens') or 0:6}  verified {r.get('verified', '-'):>6}  {r['reason'][:70]}",
                  flush=True)
            all_rows[config] = rows
            path.write_text(json.dumps({"split": args.split, "tag": args.tag, "price_per_m": PRICE_PER_M,
                                        "lessons": not args.no_lessons,
                                        "rows": all_rows,
                                        "summary": {c: summarise(rs) for c, rs in all_rows.items()}},
                                       indent=1), encoding="utf-8")
    summary = {c: summarise(rs) for c, rs in all_rows.items()}
    keys = ["cases", "success", "by_type", "policy_violations", "verified_share_mean", "errors", "timeouts",
            "tokens_mean", "cost_per_case_usd", "latency_median_s", "latency_p95_s"]
    print("\n" + f"{'':22}" + "".join(f"{c:>26}" for c in summary))
    for k in keys:
        print(f"{k:22}" + "".join(f"{str(summary[c][k]):>26}" for c in summary))
    print(f"\nsaved {path.relative_to(ROOT)}")
    if args.min_success_rate is not None:
        failures = [
            f"{config}: {failure}"
            for config, result in summary.items()
            for failure in evaluation_gate_failures(result, args.min_success_rate, args.min_cases)
        ]
        if failures:
            print("\nEvaluation gate failed:", file=sys.stderr)
            for failure in failures:
                print(f"- {failure}", file=sys.stderr)
            raise SystemExit(1)
        print(f"\nEvaluation gate passed: task success >= {args.min_success_rate:.1%}; no policy violations.")


if __name__ == "__main__":
    asyncio.run(main())
