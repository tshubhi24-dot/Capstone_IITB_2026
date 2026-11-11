"""Audit three (or more) distinct held-out runs and report the observed spread.

No mock or synthetic runs are generated; input files must come from the live
agent evaluator and contain complete independently prepared gold-case results.

Example:
  python scripts/report.py repeats --runs run_a.json run_b.json run_c.json \
      --gold data/evaluation/heldout --configs c0 c1 c2 --out docs_notfor_submission/heldout_report.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analystdesk.evaluation.workflows.audit_eval_results import validate_result


def evaluate(runs: list[Path], gold: Path, configs: list[str], min_cases: int = 40) -> dict:
    if len(runs) < 3:
        raise ValueError("at least three independently executed held-out runs are required")
    if len(set(p.resolve() for p in runs)) != len(runs):
        raise ValueError("a run file was supplied more than once")
    gathered = []
    raw_runs = []
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
        raw_runs.append(data)
    playbooks = [data.get("playbook") for data in raw_runs]
    if any(not isinstance(playbook, dict) or not playbook.get("frozen")
           or not playbook.get("version") for playbook in playbooks):
        raise ValueError("every run must record a frozen playbook version")
    if any(playbook != playbooks[0] for playbook in playbooks[1:]):
        raise ValueError("playbook snapshot differs across repeats")
    keys = ("success_rate_pct", "verified_share_pooled_pct", "policy_violations", "errors", "timeouts",
            "tokens_mean", "tokens_recorded_cases", "tokens_unreported_cases",
            "cases_with_numeric_checks", "verified_numbers", "total_numbers",
            "latency_median_s", "latency_p95_s")
    aggregate = {}
    diagnostics = []

    def spread(values: list[float | int]) -> dict:
        return {"runs": values, "min": min(values), "median": statistics.median(values), "max": max(values)}

    for conf in configs:
        stats = {}
        for key in keys:
            vals = [v["configurations"][conf][key] for v in gathered]
            if any(v is None for v in vals):
                raise ValueError(f"{conf}/{key} lacks numbers in one run")
            stats[key] = {"runs": vals, "min": min(vals), "median": statistics.median(vals), "max": max(vals)}
        stats["false_blocks"] = spread([
            sum(1 for row in data["rows"][conf] if row["type"] != "refusal" and row.get("blocks"))
            for data in raw_runs
        ])

        prices = [data.get("price_per_m") for data in raw_runs]
        if all(isinstance(price, (int, float)) and math.isfinite(price) and price >= 0 for price in prices):
            costs = [
                round(sum(row["tokens"] for row in data["rows"][conf] if row["tokens"] is not None)
                      / len(data["rows"][conf])
                      * data["price_per_m"] / 1_000_000, 4)
                for data in raw_runs
            ]
            stats["estimated_cost_per_case_usd"] = spread(costs)
        else:
            stats["estimated_cost_per_case_usd"] = None

        case_types = sorted(gathered[0]["configurations"][conf]["by_type"])
        stats["by_type"] = {}
        for kind in case_types:
            runs_by_type = [audit["configurations"][conf]["by_type"][kind] for audit in gathered]
            case_counts = {entry["cases"] for entry in runs_by_type}
            if len(case_counts) != 1:
                raise ValueError(f"{conf}/{kind} case counts differ across repeats")
            successes = [entry["success"] for entry in runs_by_type]
            stats["by_type"][kind] = {
                "cases": case_counts.pop(),
                "success_runs": successes,
                "success_median": statistics.median(successes),
                "success_min": min(successes),
                "success_max": max(successes),
            }
        aggregate[conf] = stats

    for data in raw_runs:
        run_errors = {}
        for conf, rows in data["rows"].items():
            categories = Counter()
            affected = []
            for row in rows:
                error = row.get("error")
                if not error:
                    continue
                status = re.search(r"Error code:\s*(\d+)", str(error))
                category = f"{str(error).split(':', 1)[0]} ({status.group(1)})" if status else str(error).split(":", 1)[0]
                categories[category] += 1
                affected.append(row["id"])
            if affected:
                run_errors[conf] = {"cases": len(affected), "by_error": dict(sorted(categories.items())),
                                    "affected_case_ids": affected}
        if run_errors:
            diagnostics.append({"tag": data["tag"], "errors": run_errors})

    redacted_url_count = sum(
        str(value).count("/keys/[REDACTED]")
        for data in raw_runs
        for rows in data["rows"].values()
        for row in rows
        for value in (row.get("reason", ""), row.get("error", ""))
    )
    return {"split": "heldout", "run_count": len(runs),
            "provenance": [{"tag": t, "source": g["results_source"], "sha256": g["results_sha256"]}
                           for t, g in zip([json.loads(p.read_text())["tag"] for p in runs], gathered)],
            "playbook": playbooks[0],
            "redacted_provider_url_count": redacted_url_count,
            "gold_sha256": gathered[0]["gold_sha256"], "configurations": aggregate,
            "run_diagnostics": diagnostics,
            "limitations": [
                "Audits saved model scores; does not replay or independently score raw model outputs.",
                "The risk-change scorer checks Item 1A citation coverage for both years, not semantic support for the interpretation.",
                "A run with provider errors is retained as recorded and is not a complete successful repeat.",
                "Per-case token and cost contributions divide recorded totals by all rows; unavailable token counts are omitted, so these metrics are lower-bound contributions, not provider billing records.",
            ]}


def markdown(result: dict) -> str:
    lines = ["# Held-out evaluation: repeated run report", "",
             f"{result['run_count']} distinct recorded live-run tags; each configuration covers the same gold cases.",
             "These are score-file audits, not independent replays of raw model outputs.", "",
             "Values are medians across runs [minimum, maximum], except case-type rows, which list each run's success count.",
             "| Metric | " + " | ".join(result["configurations"]) + " |",
             "|---|" + "---:|" * len(result["configurations"])]
    labels = {"success_rate_pct": "Task success (%)", "verified_share_pooled_pct": "Pooled verified share (%)",
              "policy_violations": "Policy violations", "errors": "Errors", "timeouts": "Timeouts",
              "tokens_mean": "Recorded-token contribution per case",
              "tokens_recorded_cases": "Rows with token counts",
              "tokens_unreported_cases": "Rows without token counts",
              "cases_with_numeric_checks": "Cases with numeric checks",
              "verified_numbers": "Verified numeric items",
              "total_numbers": "Numeric items assessed",
              "latency_median_s": "Median latency (s)",
              "latency_p95_s": "p95 latency (s)", "false_blocks": "False blocks",
              "estimated_cost_per_case_usd": "Recorded-token cost contribution per case (USD)"}
    for key, label in labels.items():
        cells = []
        for v in result["configurations"].values():
            s = v[key]
            cells.append("not available" if s is None else
                         f"{s['median']:g} [{s['min']:g}, {s['max']:g}]")
        lines.append("| " + label + " | " + " | ".join(cells) + " |")
    lines += ["", "## Success by case type", "",
              "Each cell lists the three success counts, followed by median [minimum, maximum]; denominators are fixed across runs.",
              "", "| Case type | " + " | ".join(result["configurations"]) + " |",
              "|---|" + "---:|" * len(result["configurations"])]
    case_types = sorted(next(iter(result["configurations"].values()))["by_type"])
    for kind in case_types:
        cells = []
        for config in result["configurations"].values():
            item = config["by_type"][kind]
            counts = ", ".join(f"{n}/{item['cases']}" for n in item["success_runs"])
            median = f"{item['success_median']:g}/{item['cases']}"
            cells.append(f"{counts}; median {median} [{item['success_min']}/{item['cases']}, {item['success_max']}/{item['cases']}]")
        lines.append("| " + kind + " | " + " | ".join(cells) + " |")
    lines += ["", "## Execution errors", ""]
    if result["run_diagnostics"]:
        for run in result["run_diagnostics"]:
            for config, detail in run["errors"].items():
                breakdown = ", ".join(f"{count} {name}" for name, count in detail["by_error"].items())
                lines.append(
                    f"- `{run['tag']}` / {config}: {detail['cases']} failed case(s) "
                    f"({breakdown}); IDs: {', '.join(detail['affected_case_ids'])}."
                )
                if detail["cases"] > 0:
                    lines.append(
                        f"  This configuration's task-success score is retained but incomplete; "
                        f"token-count and cost metrics exclude unavailable token counts."
                    )
    else:
        lines.append("- No provider or runner errors were recorded.")
    lines += ["", "## Limitations", ""]
    lines.extend(f"- {limitation}" for limitation in result["limitations"])
    if result["redacted_provider_url_count"]:
        lines.append(
            f"- Sanitization: {result['redacted_provider_url_count']} provider credential-bearing URL(s) "
            "were redacted from saved reason/error strings; case outcomes and score fields were preserved."
        )
    lines += ["", "## Run provenance", ""]
    lines.append(
        f"- Frozen playbook: `{result['playbook']['version']}` "
        f"({result['playbook']['lessons']} approved lessons)."
    )
    for x in result["provenance"]:
        lines.append(f"- `{x['tag']}`: `{x['source']}` (SHA-256 `{x['sha256']}`)")
    lines.append(f"- Held-out cases SHA-256: `{result['gold_sha256']}`")
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


