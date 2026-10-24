"""Retrieval evaluation — Recall@5 over labelled queries (L4–L6 minimum bar).

Each labelled query lists one or more targets: a company, fiscal year,
section, and evidence strings. A target counts as found when any of the top-5
passages comes from that company/year/section and contains one of its
evidence strings. Recall@5 for a query is the share of its targets found;
the reported figure is the mean over queries.

Labels point at evidence text, not passage IDs, because passage IDs change
whenever chunking changes — and the E4 ablation compares two chunkings.

Configurations form a ladder, each adding one step:
    bm25            keyword search only
    vector          embedding search only
    hybrid          BM25 + vectors merged with RRF
    hybrid+rerank   ... then cross-encoder reranking
    +decompose      ... with one filtered sub-query per company/year
    +rewrite        ... and company/year words stripped from each sub-query

Usage:
    python scripts/eval_retrieval.py                 # both passage sets
    python scripts/eval_retrieval.py --variant table # table-aware only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analystdesk.ingest import load_passages          # noqa: E402
from analystdesk.query import search_decomposed       # noqa: E402
from analystdesk.retrieve import HybridRetriever      # noqa: E402

QUERIES = ROOT / "data" / "evaluation" / "retrieval_queries.jsonl"
RESULTS_DIR = ROOT / "data" / "evaluation" / "results"
REPORT = ROOT / "docs" / "retrieval_eval.md"
TOP_K = 5

CONFIGS = [
    ("bm25", dict(mode="bm25", rerank=False), None),
    ("vector", dict(mode="vector", rerank=False), None),
    ("hybrid", dict(mode="hybrid", rerank=False), None),
    ("hybrid+rerank", dict(mode="hybrid", rerank=True), None),
    ("+decompose (filters only)", dict(mode="hybrid", rerank=True), dict(rewrite=False)),
    ("+decompose +rewrite", dict(mode="hybrid", rerank=True), dict(rewrite=True)),
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def target_found(target: dict, hits: list[dict]) -> bool:
    evidence = [_norm(e) for e in target["evidence"]]
    for h in hits:
        if h["company"] != target["company"] or h["fiscal_year"] != target["fiscal_year"]:
            continue
        if target.get("item") and h["item"] != target["item"]:
            continue
        text = _norm(h["text"])
        if any(e in text for e in evidence):
            return True
    return False


def evaluate(retriever, queries: list[dict], search_kwargs: dict, decompose: dict | None) -> dict:
    per_query, started = [], time.perf_counter()
    for q in queries:
        if decompose is not None:
            hits = search_decomposed(retriever, q["query"], top_k=TOP_K, **decompose, **search_kwargs)
        else:
            hits = retriever.search(q["query"], top_k=TOP_K, **search_kwargs)
        found = [target_found(t, hits) for t in q["targets"]]
        per_query.append({
            "qid": q["qid"],
            "type": q["type"],
            "recall": sum(found) / len(found),
            "hits": [h["passage_id"] for h in hits],
        })
    elapsed = time.perf_counter() - started

    def mean(rows):
        return round(sum(r["recall"] for r in rows) / len(rows), 3) if rows else None

    return {
        "recall@5": mean(per_query),
        "by_type": {t: mean([r for r in per_query if r["type"] == t])
                    for t in sorted({r["type"] for r in per_query})},
        "seconds_per_query": round(elapsed / len(queries), 3),
        "per_query": per_query,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", choices=["table", "plain", "both"], default="both")
    args = parser.parse_args()

    queries = [json.loads(l) for l in QUERIES.read_text(encoding="utf-8").splitlines() if l.strip()]
    variants = ["table", "plain"] if args.variant == "both" else [args.variant]

    results: dict[str, dict] = {}
    for variant in variants:
        passages = load_passages(table_aware=(variant == "table"))
        print(f"\n== {variant}: {len(passages)} passages, {len(queries)} queries")
        # Same collection prefix as the app's get_retriever(), so the
        # table-aware index is built once and shared
        prefix = "analyst_desk" if variant == "table" else "analyst_desk_plain"
        retriever = HybridRetriever(passages, collection_prefix=prefix)
        for name, kwargs, decompose in CONFIGS:
            r = evaluate(retriever, queries, kwargs, decompose)
            results[f"{variant}/{name}"] = r
            print(f"  {name:26} Recall@5 {r['recall@5']:.3f}  {r['by_type']}  "
                  f"{r['seconds_per_query']}s/query")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (RESULTS_DIR / f"retrieval_{stamp}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_report(results, queries)
    print(f"\nReport: {REPORT.relative_to(ROOT)}")


def write_report(results: dict, queries: list[dict]) -> None:
    types = sorted({q["type"] for q in queries})
    counts = ", ".join(f"{sum(q['type'] == t for q in queries)} {t}" for t in types)
    lines = [
        "# Retrieval evaluation (Recall@5)",
        "",
        f"Generated by `scripts/eval_retrieval.py` over {len(queries)} labelled queries "
        f"in `data/evaluation/retrieval_queries.jsonl` ({counts}).",
        "",
        "| Passages | Configuration | Recall@5 | " + " | ".join(types) + " | s/query |",
        "|---|---|---|" + "---|" * len(types) + "---|",
    ]
    for key, r in results.items():
        variant, name = key.split("/", 1)
        lines.append(
            f"| {variant} | {name} | {r['recall@5']:.3f} | "
            + " | ".join(f"{r['by_type'].get(t, 0):.3f}" for t in types)
            + f" | {r['seconds_per_query']} |"
        )
    lines += [
        "",
        "Interpretation, label rules and the first-run (v1) results: "
        "see [viva_notes.md](viva_notes.md), section 3.8.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
