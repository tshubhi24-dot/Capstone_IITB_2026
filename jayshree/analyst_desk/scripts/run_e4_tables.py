"""E4 (table-aware vs plain passages), measured on the answers, not only on retrieval.

Recall@5 showed table-aware parsing does not make passages easier to FIND. Its claimed value
is that a found table is USABLE: each number keeps its row and column label. This runs the
labelled questions whose answers sit in 10-K tables (data/evaluation/retrieval_queries.jsonl:
the "table" queries and the numeric "comparison" queries) through C0 and C1, once with
table-aware passages and once with plain passages (PASSAGES_VARIANT), and scores in code:

    stated     every expected figure is in the answer (same unit, within rounding)
    grounded   for every expected figure, the answer cites a passage that contains it
    verified   share of the answer's numbers the checker can verify (checks.check_note)

Memory off, plan auto-approved, runs stop at the note gate (nothing published).

    python scripts/run_e4_tables.py                       # both variants, C0 and C1
    python scripts/run_e4_tables.py --configs c0 --variant plain
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

QUERIES = ROOT / "data" / "evaluation" / "retrieval_queries.jsonl"
RESULTS = ROOT / "data" / "evaluation" / "results"
REPORT = ROOT / "docs" / "e4_tables.md"
PASSAGE_ID = re.compile(r"\b([A-Z]{1,5}_\d{4}_item(?:1a|7)_\d{3})\b")


def load_questions() -> list[dict]:
    qs = [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines() if line.strip()]
    # table look-ups, and comparisons whose evidence is a number
    return [q for q in qs if q["type"] == "table" or (
        q["type"] == "comparison" and all(any(c.isdigit() for c in t["evidence"][0]) for t in q["targets"]))]


def expected_figure(evidence: list[str]) -> str:
    """The evidence as a figure evaluation.figure_present understands: '201,183' -> '$201,183M';
    '46.2' -> '46.2%' (a ratio stated in a table)."""
    first = evidence[0]
    return f"${first}M" if "," in first else f"{first}%"


def score(q: dict, text: str, passage_text) -> dict:
    from analystdesk.agent.checks import check_note
    from analystdesk.evaluation import figure_present
    cited = set(PASSAGE_ID.findall(text))
    stated = grounded = 0
    for t in q["targets"]:
        if figure_present(expected_figure(t["evidence"]), text):
            stated += 1
        if any(any(e in (passage_text(pid) or "") for e in t["evidence"]) for pid in cited):
            grounded += 1
    r = check_note(text.replace("[fact_id:", "[fact:"), passage_text=passage_text) if text else None
    n = len(q["targets"])
    return {"stated": stated == n, "grounded": grounded == n, "cited": len(cited),
            "verified_share": r.verified_share if r else None}


async def run_variant(variant: str, configs: list[str], tag: str, ids: list[str] | None) -> list[dict]:
    from analystdesk.agent.runtime import passage_text
    from analystdesk.evaluation import TIMEOUT_S, run_agent, run_c0
    rows = []
    for q in load_questions():
        if ids and q["qid"] not in ids:
            continue
        case = {"id": q["qid"], "request": q["query"]}
        for config in configs:
            start = time.perf_counter()
            try:
                coro = run_c0(case) if config == "c0" else run_agent(case, config, f"e4{tag}-{variant}")
                out = await asyncio.wait_for(coro, timeout=TIMEOUT_S)
            except Exception as exc:   # noqa: BLE001 — failed runs are reported, not hidden
                out = {"text": "", "error": f"{type(exc).__name__}: {exc}"[:300]}
            row = {"qid": q["qid"], "type": q["type"], "variant": variant, "config": config,
                   "seconds": round(time.perf_counter() - start, 1), "tokens": out.get("tokens", 0),
                   "error": out.get("error"), "run_id": out.get("run_id"), "text": out.get("text", ""),
                   **score(q, out.get("text", ""), passage_text)}
            rows.append(row)
            print(f"{variant:5} {config} {q['qid']} stated={row['stated']!s:5} grounded={row['grounded']!s:5} "
                  f"verified={row['verified_share']} {row['seconds']}s {row['error'] or ''}", flush=True)
    return rows


def summarise(rows: list[dict]) -> dict:
    out = {}
    for key in sorted({(r["variant"], r["config"]) for r in rows}):
        rs = [r for r in rows if (r["variant"], r["config"]) == key]
        shares = [r["verified_share"] for r in rs if r["verified_share"] is not None]
        out[f"{key[0]}/{key[1]}"] = {
            "cases": len(rs),
            "stated": sum(r["stated"] for r in rs),
            "grounded": sum(r["grounded"] for r in rs),
            "verified_share_mean": round(statistics.mean(shares), 1) if shares else None,
            "errors": sum(1 for r in rs if r["error"]),
            "tokens_mean": round(statistics.mean(r["tokens"] or 0 for r in rs)),
            "latency_median_s": round(statistics.median(r["seconds"] for r in rs), 1),
        }
    return out


def write_report(data: dict, path: Path) -> None:
    s, rows = data["summary"], data["rows"]
    configs = sorted({k.split("/")[1] for k in s})
    lines = [
        "# E4: table-aware vs plain passages, measured on the answers",
        "",
        f"Generated by `scripts/run_e4_tables.py` from `{path.name}`. {s[next(iter(s))]['cases']} "
        "labelled questions whose answers sit in 10-K tables (the `table` queries and numeric "
        "`comparison` queries of `data/evaluation/retrieval_queries.jsonl`). Same model, retrieval "
        "pipeline and budget; only the passages differ (`PASSAGES_VARIANT`). Memory and lessons off; "
        "runs stop at the note gate. Scored in code.",
        "",
        "- **Stated:** every expected figure is in the answer (same unit, within rounding).",
        "- **Grounded:** for every expected figure, the answer cites a passage that contains it.",
        "- **Verified:** share of the answer's numbers the checker verifies (XBRL tags, or quotes found "
        "in the passage cited on the same line).",
        "",
        "| Configuration | Passages | Stated | Grounded | Verified (mean %) | Errors | Tokens | Latency (median s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in configs:
        for v in ("table", "plain"):
            r = s.get(f"{v}/{c}")
            if r:
                lines.append(f"| {c.upper()} | {v} | {r['stated']}/{r['cases']} | {r['grounded']}/{r['cases']} | "
                             f"{r['verified_share_mean']} | {r['errors']} | {r['tokens_mean']:,} | {r['latency_median_s']} |")
    lines += ["", "## Per question", "",
              "| Question | " + " | ".join(f"{c.upper()} table | {c.upper()} plain" for c in configs) + " |",
              "|---|" + "---|" * (2 * len(configs))]
    by_q = {}
    for r in rows:
        by_q.setdefault(r["qid"], {})[(r["config"], r["variant"])] = r
    for qid, cells in by_q.items():
        def cell(r):
            if not r:
                return "-"
            if r["error"]:
                return "error"
            return ("✅" if r["stated"] else "❌") + (" cited" if r["grounded"] else "")
        lines.append(f"| {qid} | " + " | ".join(f"{cell(cells.get((c, 'table')))} | {cell(cells.get((c, 'plain')))}"
                                                 for c in configs) + " |")
    lines += ["", "✅ figure stated, ❌ not stated; *cited*: the answer cites a passage containing the figure."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variant", choices=["table", "plain", "both"], default="both")
    ap.add_argument("--configs", nargs="+", default=["c0", "c1"], choices=["c0", "c1", "c2"])
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--tag", default=time.strftime("%Y%m%d-%H%M%S"))
    ap.add_argument("--worker-out", type=Path, help=argparse.SUPPRESS)
    ap.add_argument("--report", type=Path, help="rewrite docs/e4_tables.md from a saved result")
    a = ap.parse_args()
    if a.report:
        write_report(json.loads(a.report.read_text(encoding="utf-8")), a.report)
        return
    os.environ["AGENT_EVAL"] = "1"       # memory off
    os.environ["AGENT_LESSONS"] = "0"    # lessons off: only the passages differ
    if a.worker_out:   # one variant per process: the retriever and passages are cached per process
        rows = asyncio.run(run_variant(a.variant, a.configs, a.tag, a.cases))
        a.worker_out.write_text(json.dumps(rows), encoding="utf-8")
        return
    rows = []
    for variant in (["table", "plain"] if a.variant == "both" else [a.variant]):
        part = RESULTS / f"e4_tables_{a.tag}_{variant}.part.json"
        cmd = [sys.executable, __file__, "--variant", variant, "--configs", *a.configs,
               "--tag", a.tag, "--worker-out", str(part)] + (["--cases", *a.cases] if a.cases else [])
        subprocess.run(cmd, check=True, env={**os.environ, "PASSAGES_VARIANT": variant})
        rows += json.loads(part.read_text(encoding="utf-8"))
        part.unlink()
    data = {"tag": a.tag, "summary": summarise(rows), "rows": rows}
    path = RESULTS / f"e4_tables_{a.tag}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    write_report(data, path)
    print(json.dumps(data["summary"], indent=2))
    print(f"saved {path.relative_to(ROOT)}; report {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
