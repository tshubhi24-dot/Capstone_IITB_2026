"""Write the per-case result tables for submission, straight from the result files.

    python scripts/results_tables.py

  submission/heldout_results.md   held-out E1: every case × C0/C1/C2 × run, and the summary
                                  with mean and range over the runs
  submission/redteam_results.md   E2: every attack, defences off vs on, and the false blocks

Tables only: what each case asked, what was expected, and what happened.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "data" / "evaluation" / "results"
OUT = ROOT / "submission"
CONFIGS = ("c0", "c1", "c2")
MARK = {True: "✅", False: "❌"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pooled(rows: list[dict]) -> str:
    v = t = 0
    for r in rows:
        if r.get("verified") and "/" in str(r["verified"]):
            a, b = map(int, r["verified"].split("/"))
            v, t = v + a, t + b
    return f"{100 * v / t:.1f}%" if t else "—"


def _range(values: list[float], fmt: str = "{:.1f}") -> str:
    if not values:
        return "—"
    mean = statistics.mean(values)
    return fmt.format(mean) + (f" ({fmt.format(min(values))}–{fmt.format(max(values))})" if len(values) > 1 else "")


def heldout() -> str | None:
    runs = sorted(RESULTS.glob("eval_heldout_e1-heldout-v2-run*.json"))
    if not runs:
        return None
    data = [_load(p) for p in runs]
    cases = [json.loads(line) for f in sorted((ROOT / "data" / "evaluation" / "heldout").glob("*.jsonl"))
             for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines = ["# Held-out results (E1)", "",
             f"24 held-out cases × C0, C1, C2 × {len(data)} runs. Commit: "
             f"`{next((d['system']['commit'] for d in data if (d.get('system') or {}).get('commit')), 'n/a')}`. "
             "✅ pass · ❌ fail (one mark per run).", "",
             "## Summary (mean, range over runs)", "",
             "| Metric | " + " | ".join(c.upper() for c in CONFIGS) + " |", "|---|---|---|---|"]

    def per_run(config, fn):
        return [fn(d["rows"][config], d["summary"][config]) for d in data if config in d["rows"]]
    rows = [
        ("Task success (of 24)", lambda r, s: s["success"], "{:.1f}"),
        ("Numbers verified, pooled %", lambda r, s: float(_pooled(r).rstrip("%")) if _pooled(r) != "—" else 0, "{:.1f}"),
        ("Policy violations", lambda r, s: s["policy_violations"], "{:.0f}"),
        ("Errors / timeouts", lambda r, s: s["errors"], "{:.0f}"),
        ("Cost per case, $", lambda r, s: s["cost_per_case_usd"], "{:.4f}"),
        ("Median latency, s", lambda r, s: s["latency_median_s"], "{:.1f}"),
        ("p95 latency, s", lambda r, s: s["latency_p95_s"], "{:.1f}"),
    ]
    for name, fn, fmt in rows:
        lines.append(f"| {name} | " + " | ".join(_range(per_run(c, fn), fmt) for c in CONFIGS) + " |")

    lines += ["", "## By type (successes, summed over runs)", "",
              "| Type | Cases × runs | " + " | ".join(c.upper() for c in CONFIGS) + " |", "|---|---|---|---|---|"]
    for t in ("numeric", "comparison", "risk_change", "refusal"):
        n = sum(1 for c in cases if c["type"] == t) * len(data)
        got = [sum(r["success"] for d in data for r in d["rows"].get(c, []) if r["type"] == t) for c in CONFIGS]
        lines.append(f"| {t} | {n} | " + " | ".join(str(g) for g in got) + " |")

    lines += ["", "## Every case", "",
              "| Case | Type | Request | Expected | " + " | ".join(c.upper() for c in CONFIGS) + " |",
              "|---|---|---|---|---|---|---|"]
    for case in cases:
        exp = case["expect"]
        expected = (", ".join(f["text"] for f in exp["figures"]) if "figures" in exp
                    else f"Item 1A cited for {exp['risk_change']['years']}" if "risk_change" in exp
                    else f"declined ({exp.get('refusal_reason', '')})")
        cells = []
        for c in CONFIGS:
            marks = "".join(MARK[r["success"]] for d in data for r in d["rows"].get(c, []) if r["id"] == case["id"])
            cells.append(marks or "—")
        lines.append(f"| {case['id']} | {case['type']} | {case['request']} | {expected} | " + " | ".join(cells) + " |")

    fails = [(c, r["id"], r["reason"]) for d in data for c in CONFIGS for r in d["rows"].get(c, []) if not r["success"]]
    if fails:
        lines += ["", "## Why cases failed", "", "| Config | Case | Reason |", "|---|---|---|"]
        seen = set()
        for c, cid, reason in fails:
            if (c, cid, reason[:60]) not in seen:
                seen.add((c, cid, reason[:60]))
                lines.append(f"| {c.upper()} | {cid} | {reason[:110]} |")
    return "\n".join(lines) + "\n"


def redteam() -> str | None:
    files = {mode: sorted(RESULTS.glob(f"redteam_e2-defences-{mode}*.json")) for mode in ("off", "on")}
    if not any(files.values()):
        return None
    data = {mode: _load(fs[-1]) for mode, fs in files.items() if fs}
    attacks = [json.loads(line) for f in sorted((ROOT / "data" / "evaluation" / "redteam").glob("*.jsonl"))
               for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    config = next(iter(next(iter(data.values()))["attacks"]))
    lines = ["# Red-team results (E2)", "",
             f"{len(attacks)} attacks on {config.upper()}, defences off vs on. ❌ = the attack got through · "
             "🛡️ = stopped.", "", "## By category", "",
             "| Category | Attacks | Got through, defences off | Got through, defences on |", "|---|---|---|---|"]
    cats = sorted({a["category"] for a in attacks})
    for cat in cats + ["all"]:
        n = sum(1 for a in attacks if cat in ("all", a["category"]))
        got = []
        for mode in ("off", "on"):
            rows = data.get(mode, {}).get("attacks", {}).get(config, [])
            got.append(str(sum(r["success"] for r in rows if cat in ("all", r["category"]))) if rows else "—")
        label = "**All**" if cat == "all" else cat.replace("_", " ")
        lines.append(f"| {label} | {n} | {got[0]} | {got[1]} |")
    lines += ["", "## Clean cases (what the defences cost)", "",
              "| | Defences off | Defences on |", "|---|---|---|"]
    for name, key in (("Task success", "success"), ("False blocks", "false_blocks")):
        vals = []
        for mode in ("off", "on"):
            s = (data.get(mode, {}).get("summary", {}).get(config) or {}).get("clean") or {}
            vals.append(f"{s.get(key, '—')}/{s.get('cases', '—')}")
        lines.append(f"| {name} | {vals[0]} | {vals[1]} |")
    lines += ["", "## Every attack", "",
              "| Attack | Category | Request | Defences off | Defences on | What stopped it (defences on) |",
              "|---|---|---|---|---|---|"]
    by_mode = {mode: {r["id"]: r for r in d["attacks"].get(config, [])} for mode, d in data.items()}
    for a in attacks:
        cells = []
        for mode in ("off", "on"):
            r = by_mode.get(mode, {}).get(a["id"])
            cells.append("—" if r is None else ("⚠️ error" if r.get("error") else ("❌" if r["success"] else "🛡️")))
        r_on = by_mode.get("on", {}).get(a["id"]) or {}
        why = "; ".join(r_on.get("reasons") or r_on.get("blocked_by") or [])[:100] or "model did not comply"
        lines.append(f"| {a['id']} | {a['category'].replace('_', ' ')} | {a['request'][:90]} | {cells[0]} | {cells[1]} | {why} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    for name, build in (("heldout_results.md", heldout), ("redteam_results.md", redteam)):
        text = build()
        if text:
            (OUT / name).write_text(text, encoding="utf-8")
            print(f"wrote submission/{name}")
        else:
            print(f"no results yet for {name}")


if __name__ == "__main__":
    main()
