"""Audit existing evaluation JSON and generate reproducible, provenance-linked results.

This is an OFFLINE, read-only analysis of recorded per-case scores. It verifies
case coverage and recorded scoring consistency, but does not run any LLM, replay
tool calls, or independently establish that the saved scores are true. Never
present it as a new agent evaluation.

Usage:
  python scripts/report.py audit --input data/evaluation/results/eval_dev_postcleanup-dev_<tag>.json \
      --cases data/evaluation/development \
      --configs c0 c1 c2 --min-cases 44 \
      --out-json data/evaluation/results/postcleanup_dev_audit.json \
      --out-md docs_notfor_submission/role6_development_evidence.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[3]
RATE_RE = re.compile(r"^(\d+)/(\d+)$")
VALID_TYPES = {"numeric", "comparison", "risk_change", "refusal"}


def sha256(path: Path) -> str:
    if path.is_dir():
        h = hashlib.sha256()
        for f in sorted(path.glob("*.jsonl")):
            h.update(f.name.encode("utf-8"))
            h.update(b"\0")
            h.update(f.read_bytes())
            h.update(b"\0")
        return h.hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def read_gold(path: Path, split: str) -> dict[str, dict]:
    paths = sorted(path.glob("*.jsonl")) if path.is_dir() else [path]
    if not paths or any(not f.is_file() for f in paths):
        raise ValueError(f"gold case file(s) missing: {path}")
    cases: dict[str, dict] = {}
    for f in paths:
        for line_num, raw in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            case = json.loads(raw)
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError(f"gold {f.name}:{line_num} has no valid ID")
            if case_id in cases:
                raise ValueError(f"duplicate gold case {case_id}")
            if case.get("split") != split or case.get("type") not in VALID_TYPES:
                raise ValueError(f"gold case {case_id} has an invalid split/type")
            cases[case_id] = case
    if not cases:
        raise ValueError("gold file contains no cases")
    return cases


def validate_result(path: Path, gold_path: Path, configs: list[str], min_cases: int) -> dict:
    if not 1 <= min_cases:
        raise ValueError("min-cases must be positive")
    if not configs or len(set(configs)) != len(configs) or not set(configs) <= {"c0", "c1", "c2"}:
        raise ValueError("configs must be unique members of c0, c1, c2")
    raw = json.loads(path.read_text(encoding="utf-8"))
    split = raw.get("split")
    if split not in {"dev", "heldout"}:
        raise ValueError(f"invalid result split: {split}")
    gold = read_gold(gold_path, split)
    if len(gold) < min_cases:
        raise ValueError(f"gold contains {len(gold)} cases, need at least {min_cases}")
    group = raw.get("rows")
    if not isinstance(group, dict):
        raise ValueError("results.rows must be a dictionary")
    missing_configs = set(configs) - set(group)
    if missing_configs:
        raise ValueError(f"missing result configurations: {sorted(missing_configs)}")
    report = {}
    for config in configs:
        rows = group[config]
        if not isinstance(rows, list):
            raise ValueError(f"{config} result rows must be a list")
        ids = []
        verified, total = 0, 0
        substantive_shares = []
        zero_number_rows = 0
        cases_with_numeric_checks = 0
        for i, row in enumerate(rows, 1):
            cid = row.get("id")
            if cid not in gold:
                raise ValueError(f"{config} row {i} has unexpected case ID {cid!r}")
            ids.append(cid)
            if row.get("config") != config or row.get("type") != gold[cid]["type"]:
                raise ValueError(f"{config}/{cid} config or type differs from gold")
            if not isinstance(row.get("success"), bool) or not isinstance(row.get("policy_violation"), bool):
                raise ValueError(f"{config}/{cid} has non-boolean success/policy result")
            if not isinstance(row.get("seconds"), (int, float)) or not math.isfinite(row["seconds"]) or row["seconds"] < 0:
                raise ValueError(f"{config}/{cid} has invalid duration")
            if row.get("tokens") is None:
                if not row.get("error"):
                    raise ValueError(f"{config}/{cid} has no token count and no recorded error")
            elif not isinstance(row["tokens"], int) or row["tokens"] < 0:
                raise ValueError(f"{config}/{cid} has invalid token count")
            if row.get("error") and row["success"]:
                raise ValueError(f"{config}/{cid} cannot succeed with an error")
            share = row.get("verified_share")
            counts = row.get("verified")
            if counts is not None:
                m = RATE_RE.fullmatch(str(counts))
                if not m:
                    raise ValueError(f"{config}/{cid} has invalid verified counts")
                a, b = map(int, m.groups())
                if b < 0 or not 0 <= a <= b:
                    raise ValueError(f"{config}/{cid} has invalid verified numerator/denominator")
                expected_share = (100 * a / b) if b else 100.0  # historic checker: 0/0 = 100%
                if not isinstance(share, (int, float)) or abs(expected_share - share) > 0.051:
                    raise ValueError(f"{config}/{cid} verified percentage disagrees with counts")
                if b:
                    substantive_shares.append(share)
                    cases_with_numeric_checks += 1
                else:
                    zero_number_rows += 1
                verified += a
                total += b
            elif share is not None:
                raise ValueError(f"{config}/{cid} has verified percentage without supporting counts")
        dups = [cid for cid, n in Counter(ids).items() if n > 1]
        if dups:
            raise ValueError(f"{config} contains duplicate result IDs: {sorted(dups)}")
        missing = set(gold) - set(ids)
        if missing:
            raise ValueError(f"{config} missing {len(missing)} gold cases: {sorted(missing)}")
        if len(rows) < min_cases:
            raise ValueError(f"{config} evaluated only {len(rows)} cases; need {min_cases}")
        shares = [r["verified_share"] for r in rows if r.get("verified_share") is not None]
        seconds = sorted(r["seconds"] for r in rows)
        successes = sum(r["success"] for r in rows)
        failures = len(rows) - successes
        errors = sum(bool(r.get("error")) for r in rows)
        policy = sum(r["policy_violation"] for r in rows)
        tokens = [r["tokens"] for r in rows if r["tokens"] is not None]
        report[config] = {
            "cases": len(rows),
            "success": successes,
            "failures": failures,
            "success_rate_pct": round(100 * successes / len(rows), 1),
            "policy_violations": policy,
            "errors": errors,
            "timeouts": sum(r.get("error") == "timeout" for r in rows),
            "verified_numbers": verified,
            "total_numbers": total,
            "cases_with_numeric_checks": cases_with_numeric_checks,
            "verified_share_pooled_pct": round(100 * verified / total, 1) if total else None,
            "zero_number_cases": zero_number_rows,
            "verified_share_mean_with_numbers_only_pct": round(sum(substantive_shares) / len(substantive_shares), 1) if substantive_shares else None,
            "verified_share_case_mean_pct": round(sum(shares) / len(shares), 1) if shares else None,
            "tokens_mean": round(sum(tokens) / len(rows)),
            "tokens_recorded_cases": len(tokens),
            "tokens_unreported_cases": len(rows) - len(tokens),
            "latency_median_s": round(median(seconds), 1),
            "latency_p95_s": seconds[min(len(seconds) - 1, round(0.95 * (len(seconds) - 1)))],
            "by_type": {
                kind: {"success": sum(r["success"] for r in rows if r["type"] == kind),
                       "cases": sum(r["type"] == kind for r in rows)}
                for kind in sorted({r["type"] for r in rows})
            },
        }
        # Validate the committed aggregate summaries, but compute our pooled
        # verified share separately (the old aggregate never provided it).
        saved = raw.get("summary", {}).get(config)
        if saved is not None:
            for key in ("cases", "success", "policy_violations", "errors", "timeouts", "tokens_mean", "latency_median_s", "latency_p95_s"):
                if saved.get(key) != report[config][key]:
                    raise ValueError(f"{config} saved summary field {key} disagrees with rows")
            if saved.get("verified_share_mean") != report[config]["verified_share_case_mean_pct"]:
                raise ValueError(f"{config} saved mean verification share disagrees with rows")
    return {
        "evaluation_type": "audit_of_recorded_development_results" if split == "dev" else "audit_of_recorded_heldout_results",
        "not_an_agent_rerun": True,
        "not_an_independent_scoring_replay": True,
        "split": split,
        "results_source": reference(path),
        "results_sha256": sha256(path),
        "gold_source": reference(gold_path),
        "gold_sha256": sha256(gold_path),
        "configurations": report,
    }


def markdown_report(report: dict) -> str:
    rows = [
        "# Role 6 — Evaluation evidence audit",
        "",
        f"**Split:** {report['split']}  ",
        f"**Recorded result:** `{report['results_source']}`  ",
        f"**SHA-256:** `{report['results_sha256']}`  ",
        f"**Gold cases:** `{report['gold_source']}`  ",
        f"**Gold SHA-256:** `{report['gold_sha256']}`",
        "",
        "This is a reproducible offline audit of **pre-existing saved results**, not a new LLM or tool run. "
        "It verifies case coverage, score types, numeric consistency and aggregates. "
        "It cannot independently verify the model outputs because the saved scores do not include full response artifacts.",
        "",
        "| Metric | " + " | ".join(report["configurations"]) + " |",
        "|---|" + "---:|" * len(report["configurations"]),
    ]
    cfg = report["configurations"]
    for label, k in [
        ("Cases", "cases"), ("Task successes", "success"), ("Task success (%)", "success_rate_pct"),
        ("Policy violations", "policy_violations"), ("Errors", "errors"), ("Timeouts", "timeouts"),
        ("Verified numbers (count)", "verified_numbers"), ("All counted numbers", "total_numbers"),
        ("Verified share, pooled (%)", "verified_share_pooled_pct"),
        ("Notes with 0 counted numbers", "zero_number_cases"),
        ("Case-mean share, numeric-content notes only (%)", "verified_share_mean_with_numbers_only_pct"),
        ("Verified share, average per scored case (%)", "verified_share_case_mean_pct"),
        ("Recorded-token contribution per evaluated case (incomplete if counts are missing)", "tokens_mean"),
        ("Latency median (seconds)", "latency_median_s"),
        ("Latency p95 (seconds)", "latency_p95_s"),
    ]:
        rows.append(f"| {label} | " + " | ".join(str(v[k]) for v in cfg.values()) + " |")
    rows += [
        "",
        "## What these results establish",
        "",
        "- **Development data only** if the split is `dev`; no held-out generalisation claim is justified.",
        "- Pooled verified share counts *all verified numbers / all counted numbers*. It matches the definition "
        "of the Prometheus verified-share alert; the original case mean weights short and long notes equally "
        "and treats 0/0 as 100%. The extra nonempty-case mean excludes 0/0 notes.",
        "- The 98% threshold is an **operational alert**, not a guarantee that an individual output is safe to publish.",
        "- This file is not a substitute for a live Docker smoke test, GitHub Actions logs, manual labels, "
        "red-team results or three genuine held-out runs.",
        "",
    ]
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--configs", nargs="+", choices=["c0", "c1", "c2"], required=True)
    ap.add_argument("--min-cases", type=int, required=True)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    args = ap.parse_args(argv)
    try:
        report = validate_result(args.input, args.cases, args.configs, args.min_cases)
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(f"Evaluation audit failed: {exc}", file=sys.stderr)
        return 1
    for config, v in report["configurations"].items():
        print(f"{config}: {v['success']}/{v['cases']} passed; "
              f"numbers {v['verified_numbers']}/{v['total_numbers']} = "
              f"{v['verified_share_pooled_pct']}% verified (pooled)")
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.out_json}")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(markdown_report(report), encoding="utf-8")
        print(f"wrote {args.out_md}")
    return 0


