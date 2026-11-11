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

    python scripts/run.py eval --configs c0 c1 c2 --split dev
    python scripts/run.py eval --configs c2 --split dev --cases d01 d14
    python scripts/run.py eval --experiment e4_critic_off             # an experiment file
    python scripts/run.py eval --experiment e1_c0_c1_c2 --split dev   # ...on another split
    python scripts/run.py eval --configs c1 c2 --split heldout --no-lessons    # E3 before
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["AGENT_EVAL"] = "1"            # memory off for every evaluation run

from dotenv import load_dotenv              # noqa: E402

load_dotenv(ROOT / ".env")

from analystdesk.evaluation import experiments as experiments  # noqa: E402
from analystdesk.evaluation.scoring import PRICE_PER_M
from analystdesk.evaluation.scoring import RESULTS
from analystdesk.evaluation.scoring import evaluation_gate_failures
from analystdesk.evaluation.scoring import evaluator_path
from analystdesk.evaluation.scoring import load_cases
from analystdesk.evaluation.scoring import run_one
from analystdesk.evaluation.scoring import summarise


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", help="an experiments/*.toml file or its name; sets configs, split, switches")
    ap.add_argument("--configs", nargs="+", choices=["c0", "c1", "c2"])
    ap.add_argument("--split", choices=["dev", "heldout"])
    ap.add_argument("--heldout-dir", type=Path,
                    help="evaluator-controlled held-out directory outside the application repository")
    ap.add_argument("--results-dir", type=Path,
                    help="evaluator-controlled results directory (required for external held-out cases)")
    ap.add_argument("--cases", nargs="*", help="only these case ids")
    ap.add_argument("--tag")
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
    experiment = None
    if args.experiment:
        experiment = experiments.load(args.experiment)
        if experiment["runner"] != "eval":
            ap.error(f"{experiment['file']} is a {experiment['runner']} experiment: use scripts/run.py redteam")
        experiments.apply(experiment)
    args.configs = args.configs or (experiment["configs"] if experiment else ["c0", "c1", "c2"])
    args.split = args.split or (experiment["split"] if experiment else "dev")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    args.tag = args.tag or (f"{Path(experiment['file']).stem}-{stamp}" if experiment else stamp)
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.tag):
        ap.error("--tag must contain only letters, digits, '-' or '_'")
    if args.no_lessons:
        os.environ["AGENT_LESSONS"] = "0"
    if args.heldout_dir and args.split != "heldout":
        ap.error("--heldout-dir requires --split heldout")
    if args.heldout_dir and not args.results_dir:
        ap.error("--heldout-dir requires an external --results-dir")
    try:
        results_dir = evaluator_path(args.results_dir) if args.heldout_dir else (args.results_dir or RESULTS)
    except ValueError as exc:
        ap.error(str(exc))
    from analystdesk.memory.playbook import frozen_playbook
    frozen = await frozen_playbook()
    requires_lessons = bool(experiment and experiment["env"].get("AGENT_LESSONS") == "1")
    if requires_lessons:
        if os.getenv("AGENT_LESSONS", "1") == "0":
            ap.error("the after-playbook experiment requires lessons; remove --no-lessons")
        if not frozen:
            ap.error("approve lessons and freeze the playbook before the after-playbook experiment")
        if not isinstance(frozen.get("version"), str) or not frozen["version"].strip():
            ap.error("the after-playbook experiment requires a versioned snapshot; freeze the playbook again")
        if not isinstance(frozen.get("lessons"), list) or not frozen["lessons"]:
            ap.error("the after-playbook experiment requires at least one approved, frozen lesson")
    if args.split == "heldout" and os.getenv("AGENT_LESSONS", "1") != "0" and not frozen:
        ap.error("freeze the playbook before a held-out run (Research tab -> Playbook -> Freeze)")
    playbook = ({"frozen": True, "version": frozen.get("version"), "lessons": len(frozen.get("lessons") or [])}
                if frozen else {"frozen": False})
    all_cases = load_cases(args.split, heldout_dir=args.heldout_dir)
    if args.cases:
        known = {c["id"] for c in all_cases}
        missing = set(args.cases) - known
        if missing:
            ap.error(f"unknown case IDs for {args.split}: {', '.join(sorted(missing))}")
    cases = [c for c in all_cases if not args.cases or c["id"] in args.cases]
    if len(cases) < args.min_cases:
        ap.error(f"selected {len(cases)} cases, but --min-cases requires {args.min_cases}")
    # what produced these results: code revision, config version, models, reply cap
    from analystdesk.config.llm_config import LLM_CONFIG
    import subprocess
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "analystdesk", "config", "scripts"], cwd=ROOT,
                           capture_output=True, text=True)
    system = {"commit": commit.stdout.strip() or None, "uncommitted_changes": bool(dirty.stdout.strip()),
              "llm_config_version": LLM_CONFIG.version, "models": dict(LLM_CONFIG.models),
              "max_output_tokens": LLM_CONFIG.max_output_tokens}
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / f"eval_{args.split}_{args.tag}.json"
    try:
        with path.open("x", encoding="utf-8") as file:
            json.dump({"split": args.split, "tag": args.tag, "rows": {}}, file)
    except FileExistsError:
        ap.error(f"result file already exists: {path}; choose a new --tag")
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
            snapshot = json.dumps({"split": args.split, "tag": args.tag, "price_per_m": PRICE_PER_M,
                                   "system": system,
                                   "case_source": ("external-evaluator" if args.heldout_dir else
                                                   "repository-exposed" if args.split == "heldout" else "development"),
                                   "lessons": os.getenv("AGENT_LESSONS", "1") != "0",
                                   "playbook": playbook,
                                   "experiment": {"file": experiment["file"], "name": experiment["name"],
                                                  "env": experiment["env"]} if experiment else None,
                                   "rows": all_rows,
                                   "summary": {c: summarise(rs) for c, rs in all_rows.items()}},
                                  indent=1)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(snapshot, encoding="utf-8")
            temporary.replace(path)   # maintain a valid checkpoint if interrupted mid-run
    summary = {c: summarise(rs) for c, rs in all_rows.items()}
    keys = ["cases", "success", "by_type", "policy_violations", "false_blocks", "verified_share_mean", "errors",
            "timeouts",
            "tokens_mean", "cost_per_case_usd", "latency_median_s", "latency_p95_s"]
    print("\n" + f"{'':22}" + "".join(f"{c:>26}" for c in summary))
    for k in keys:
        print(f"{k:22}" + "".join(f"{str(summary[c][k]):>26}" for c in summary))
    print(f"\nsaved {path}")
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


