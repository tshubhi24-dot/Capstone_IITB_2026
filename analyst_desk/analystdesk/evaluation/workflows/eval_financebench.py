"""External retrieval check on FinanceBench's open sample (brief: Analyst Desk, L13).

FinanceBench (PatronusAI, CC BY-NC 4.0) has 150 questions about public filings,
each with the evidence text a correct answer rests on. It was written by
people outside this project, so it checks retrieval on questions we did not
choose. The file is downloaded at run time and not committed.

Only questions about a 10-K we cover (company and fiscal year) are used. For
each one the check reports:
    in_corpus   the evidence sentence appears in one of our passages for that
                company and year (we index Item 1A and Item 7 only, so evidence
                from the financial statements or Item 1 cannot be found)
    hit@5       the app's full search (hybrid + rerank + decomposition +
                rewrite) returns a passage containing that sentence in its top 5

    python scripts/run.py financebench
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from analystdesk.retrieval.ingest import load_passages        # noqa: E402
from analystdesk.retrieval.query import search_decomposed     # noqa: E402
from analystdesk.retrieval.retrieve import get_retriever      # noqa: E402
from analystdesk.servers.common import COVERED_YEARS  # noqa: E402

URL = "https://huggingface.co/datasets/PatronusAI/financebench/resolve/main/financebench_merged.jsonl"
CACHE = ROOT / "data" / "external" / "financebench_merged.jsonl"     # gitignored
OUT = ROOT / "data" / "evaluation" / "results" / "financebench_check.json"
# FinanceBench company names -> our tickers
TICKERS = {"Microsoft": "MSFT", "Alphabet": "GOOGL", "Apple": "AAPL", "Amazon": "AMZN", "Meta": "META",
           "Nvidia": "NVDA", "NVIDIA": "NVDA", "AMD": "AMD", "Oracle": "ORCL", "JPMorgan": "JPM",
           "Goldman Sachs": "GS", "Bank of America": "BAC", "Visa": "V", "Morgan Stanley": "MS",
           "Mastercard": "MA", "Wells Fargo": "WFC"}


def _norm(text: str) -> str:
    """Lower-case letters and digits only, so PDF and HTML extractions of one sentence compare equal."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _sentences(evidence: str) -> list[str]:
    """Evidence sentences long enough to identify a passage (tables and headers are skipped)."""
    parts = re.split(r"(?<=[.!?])\s+", evidence)
    return [n for p in parts if len(n := _norm(p)) >= 60 and len(re.findall(r"[a-z]{3,}", n)) >= 8]


def _contains(passages: list[dict], sentences: list[str]) -> bool:
    return any(s in _norm(p["text"]) for p in passages for s in sentences)


def main() -> None:
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_bytes(urllib.request.urlopen(URL, timeout=60).read())
    rows = [json.loads(line) for line in CACHE.read_text(encoding="utf-8").splitlines() if line.strip()]
    ours = [r for r in rows if r["doc_type"] == "10k" and r["company"] in TICKERS
            and r["doc_period"] in COVERED_YEARS]
    print(f"{len(rows)} FinanceBench questions; {len(ours)} about a 10-K we cover")

    passages = load_passages()
    retriever = get_retriever(passages)
    results = []
    for r in ours:
        ticker, year = TICKERS[r["company"]], r["doc_period"]
        sentences = [s for e in r["evidence"] for s in _sentences(e.get("evidence_text", ""))]
        own = [p for p in passages if p["company"] == ticker and p["fiscal_year"] == year]
        in_corpus = bool(sentences) and _contains(own, sentences)
        started = time.perf_counter()
        hits = search_decomposed(retriever, r["question"], top_k=5, rewrite=True, mode="hybrid", rerank=True)
        hit = in_corpus and _contains([h for h in hits if h["company"] == ticker], sentences)
        # ids and our own results only: FinanceBench's text stays in the downloaded file
        results.append({"id": r["financebench_id"], "ticker": ticker, "year": year,
                        "evidence_page": [e.get("evidence_page_num") for e in r["evidence"]],
                        "in_corpus": in_corpus, "hit@5": hit,
                        "top5": [h["passage_id"] for h in hits],
                        "seconds": round(time.perf_counter() - started, 2)})
        print(f"{r['financebench_id']:22} {ticker:5} FY{year}  in corpus {'yes' if in_corpus else 'no ':3}  "
              f"hit@5 {'yes' if hit else 'no '}  {r['question'][:70]}")
    findable = [x for x in results if x["in_corpus"]]
    summary = {"questions_total": len(rows), "in_coverage": len(results), "evidence_in_corpus": len(findable),
               "hit@5": sum(x["hit@5"] for x in findable),
               "recall@5_on_findable": round(sum(x["hit@5"] for x in findable) / len(findable), 3) if findable else None}
    OUT.write_text(json.dumps({"source": URL, "licence": "CC BY-NC 4.0", "summary": summary, "rows": results},
                              indent=1), encoding="utf-8")
    print(json.dumps(summary))
    print(f"saved {OUT.relative_to(ROOT)}")


