"""Audit three (or more) distinct held-out runs and report the observed spread.

No mock or synthetic runs are generated; input files must come from the live
agent evaluator and contain complete independently prepared gold-case results.

Example:
  python scripts/eval_three_runs.py --runs run_a.json run_b.json run_c.json \
      --gold data/evaluation/heldout --configs c0 c1 c2 --out docs/heldout_report.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

from audit_eval_results import validate_result


def evaluate(runs: list[Path], gold: Path, configs: list[str], min_cases: int = 40) -> dict:
    if len(runs) < 3:
        raise ValueError("at least three independently executed held-out runs are required")
    if len(set(p.resolve() for p in runs)) != len(runs):
        raise ValueError("a run file was supplied more than once")
    gathered = []
    seen_tags = set()
    seen_hashes = set()
    for path in runs:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("split") != "heldout":
            raise ValueError(f"{path.name} is not a held-out run")
        tag = data.get("tag")
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError(f"{path.name} lacks a unique live-run tag")
        if tag in seen_tags:
            raise ValueError(f"duplicate live-run tag {tag}")
        seen_tags.add(tag)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen_hashes:
            raise ValueError("identical result file provided multiple times")
        seen_hashes.add(digest)
        audited = validate_result(path, gold, configs, min_cases)
        gathered.append(audited)
    keys = ("success_rate_pct", "verified_share_pooled_pct", "policy_violations", "errors", "timeouts",
            "tokens_mean", "latency_median_s", "latency_p95_s")
    aggregate = {}
    for conf in configs:
        stats = {}
        for key in keys:
            vals = [v["configurations"][conf][key] for v in gathered]
            if any(v is None for v in vals):
                raise ValueError(f"{conf}/{key} lacks numbers in one run")
            stats[key] = {"runs": vals, "min": min(vals), "median": statistics.median(vals), "max": max(vals)}
        aggregate[conf] = stats
    return {"split": "heldout", "run_count": len(runs),
            "provenance": [{"tag": t, "source": g["results_source"], "sha256": g["results_sha256"]}
                           for t, g in zip([json.loads(p.read_text())["tag"] for p in runs], gathered)],
            "gold_sha256": gathered[0]["gold_sha256"], "configurations": aggregate,
            "limitations": "Audits saved model scores; does not replay or independently score raw model outputs."}


def markdown(result: dict) -> str:
    lines = ["# Held-out evaluation: repeated run report", "",
             f"{result['run_count']} distinct recorded live-run tags; each configuration covers the same gold cases.",
             "These are score-file audits, not independent replays of raw model outputs.", "",
             "| Metric | " + " | ".join(result["configurations"]) + " |",
             "|---|" + "---:|" * len(result["configurations"])]
    labels = {"success_rate_pct": "Task success (%)", "verified_share_pooled_pct": "Pooled verified share (%)",
              "policy_violations": "Policy violations", "errors": "Errors", "timeouts": "Timeouts",
              "tokens_mean": "Mean tokens", "latency_median_s": "Median latency (s)",
              "latency_p95_s": "p95 latency (s)"}
    for key, label in labels.items():
        cells = []
        for v in result["configurations"].values():
            s = v[key]
            cells.append(f"{s['median']:g} [{s['min']:g}, {s['max']:g}]")
        lines.append("| " + label + " | " + " | ".join(cells) + " |")
    lines += ["", "Values: median across runs [minimum, maximum].", "", "## Run provenance", ""]
    for x in result["provenance"]:
        lines.append(f"- `{x['tag']}`: `{x['source']}` (SHA-256 `{x['sha256']}`)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", nargs="+", required=True, type=Path)
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument("--configs", nargs="+", required=True, choices=["c0", "c1", "c2"])
    ap.add_argument("--min-cases", default=40, type=int)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        report = evaluate(args.runs, args.gold, args.configs, args.min_cases)
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Held-out evaluation report failed: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown(report), encoding="utf-8")
    args.out.with_suffix(".json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Verified {report['run_count']} distinct held-out runs; wrote {args.out} and {args.out.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
