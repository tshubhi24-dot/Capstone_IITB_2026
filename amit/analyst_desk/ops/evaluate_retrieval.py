"""Offline paired retrieval comparison on frozen public development labels.

This evaluator does not call a language model, create labels from results, access
protected cases, or use a model verdict as truth. Every attempted query remains
in the denominator, including empty searches, invalid results and errors.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desk.data import Corpus

MODES = ("bm25", "hybrid", "hybrid_rerank")
DEVELOPMENT_TICKERS = frozenset({"MSFT", "AAPL", "ABBV", "AMGN"})
YEARS = frozenset({2023, 2024, 2025})
DEFAULT_QUERIES = ROOT / "evaluation/retrieval/development_queries.jsonl"
FROZEN_QUERY_SHA256 = "ab0e30ef73499e4adb8f1385e0f9af9f459e1504cc42c77be8a0107769d22d9a"
K = 5


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def evidence_digest(passage):
    """Hash the original evidence, including actual retained table cells."""
    proof = {key: passage[key] for key in ("id", "ticker", "year", "item", "source_url", "text")}
    if "table" in passage:
        proof["table"] = passage["table"]
    return digest(json.dumps(proof, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def load_labels(path, corpus, *, expected_query_sha256):
    """Validate all labels and provenance before performing the first search."""
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected_query_sha256)):
        raise ValueError("An explicit frozen query SHA256 is required")
    raw = Path(path).read_bytes()
    if digest(raw) != expected_query_sha256:
        raise ValueError("Query file differs from the frozen query hash")
    try:
        cases = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    except (ValueError, UnicodeError) as error:
        raise ValueError("Query labels must be UTF-8 JSONL records") from error
    if len(cases) < 30:
        raise ValueError("At least thirty development queries are required")
    identifiers, group_scopes = set(), {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Every query must be an object")
        identifier = case.get("id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"retrieval-dev-[a-z0-9_-]{1,100}", identifier):
            raise ValueError("Invalid public development query identifier")
        if identifier in identifiers:
            raise ValueError("Duplicate query identifier")
        identifiers.add(identifier)
        if (case.get("split") != "development" or not isinstance(case.get("ticker"), str)
                or case["ticker"] not in DEVELOPMENT_TICKERS):
            raise ValueError("Only declared public development issuers are eligible")
        years = case.get("years")
        if (not isinstance(years, list) or not years
                or any(type(year) is not int or year not in YEARS for year in years)
                or len(years) != len(set(years))):
            raise ValueError("Invalid development fiscal-year scope")
        if case.get("source_corpus_sha256") != corpus.fingerprint:
            raise ValueError("Label source hash differs from the frozen corpus")
        if case.get("annotation_status") != "source_derived_not_human_reviewed":
            raise ValueError("These development labels must retain their actual review status")
        if case.get("label_scope") != "partial_relevant_passage_set":
            raise ValueError("This harness expects an explicitly partial relevant passage set")
        if case.get("query_kind") not in {"narrative", "financial_table"}:
            raise ValueError("Unknown retrieval question kind")
        question = case.get("question")
        if not isinstance(question, str) or not 20 <= len(question) <= 1000 or not question.strip():
            raise ValueError("Every retrieval question must be substantive text")
        for field in ("scenario_group_id", "company_year_group_id"):
            if not isinstance(case.get(field), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", case[field]):
                raise ValueError("Every query requires bounded scenario and company/year groups")
        group = case["scenario_group_id"]
        if group in group_scopes and group_scopes[group] != case["ticker"]:
            raise ValueError("Related development query groups cannot cross issuer partitions")
        group_scopes[group] = case["ticker"]
        relevant = case.get("relevant_passages")
        if not isinstance(relevant, list) or not relevant:
            raise ValueError("Every query requires a nonempty relevant passage set")
        passage_ids = set()
        for label in relevant:
            if not isinstance(label, dict) or not isinstance(label.get("passage_id"), str):
                raise ValueError("Invalid relevant passage label")
            if label["passage_id"] in passage_ids:
                raise ValueError("Duplicate relevant passage would distort recall")
            passage_ids.add(label["passage_id"])
            passage = corpus.passage(label["passage_id"])
            if passage["ticker"] != case["ticker"] or passage["year"] not in years:
                raise ValueError("Relevant evidence falls outside the query's issuer/year scope")
            if (label.get("source_url") != passage["source_url"] or label.get("item") != passage["item"]
                    or label.get("evidence_sha256") != evidence_digest(passage)):
                raise ValueError("Relevant evidence provenance or content hash differs")
            if not isinstance(label.get("relevance_basis"), str) or not label["relevance_basis"].strip():
                raise ValueError("Every passage label requires a source-derived relevance explanation")
            if case["query_kind"] == "financial_table" and not passage.get("table"):
                raise ValueError("Financial-table relevance must refer to retained table evidence")
    return cases, digest(raw)


def _metrics(rows):
    count = len(rows)
    if not count:
        return {"attempted": 0, "errors": 0, "sampled_label_recall_at_5": None,
                "hit_at_5": None, "macro_achievable_recall_at_5": None}
    return {
        "attempted": count,
        "errors": sum(row["status"] == "error" for row in rows),
        "sampled_label_recall_at_5": sum(row["sampled_label_recall_at_5"] for row in rows) / count,
        "hit_at_5": sum(row["hit_at_5"] for row in rows) / count,
        "macro_achievable_recall_at_5": sum(row["achievable_recall_at_5"] for row in rows) / count,
    }


def _validate_results(corpus, case, hits):
    if not isinstance(hits, list) or len(hits) > K:
        raise ValueError("Search must return at most five passage records")
    identifiers = []
    for hit in hits:
        if not isinstance(hit, dict) or not isinstance(hit.get("id"), str) or hit["id"] in identifiers:
            raise ValueError("Search returned invalid or duplicate passage identifiers")
        original = corpus.passage(hit["id"])
        if original["ticker"] != case["ticker"] or original["year"] not in case["years"]:
            raise ValueError("Search result escaped its allowed issuer/year scope")
        identifiers.append(hit["id"])
    return identifiers


def evaluate(corpus_path, query_path=DEFAULT_QUERIES, *, expected_query_sha256=FROZEN_QUERY_SHA256,
             modes=MODES):
    """Return paired per-query records without changing labels or the corpus."""
    if not modes or len(set(modes)) != len(modes) or not set(modes) <= set(MODES):
        raise ValueError("Select distinct supported retrieval modes")
    corpus = Corpus(corpus_path)
    cases, query_hash = load_labels(query_path, corpus, expected_query_sha256=expected_query_sha256)
    results, summaries = {}, {}
    for mode in modes:
        rows = []
        for case in cases:
            relevant = {label["passage_id"] for label in case["relevant_passages"]}
            start = time.perf_counter()
            error_type = None
            try:
                hits = corpus.search(case["question"], case["ticker"], case["years"],
                                     k=K, retrieval_mode=mode)
                retrieved = _validate_results(corpus, case, hits)
            except Exception as error:
                # Retain the attempt and safe error class; no provider/private error text.
                error_type = type(error).__name__
                retrieved = []
            matched = relevant & set(retrieved)
            rows.append({
                "query_id": case["id"], "scenario_group_id": case["scenario_group_id"],
                "company_year_group_id": case["company_year_group_id"], "ticker": case["ticker"],
                "years": case["years"], "query_kind": case["query_kind"],
                "status": "error" if error_type else "completed", "error_type": error_type,
                "retrieved_passage_ids": retrieved, "labelled_relevant_passage_ids": sorted(relevant),
                "matched_passage_ids": sorted(matched), "labelled_relevant_count": len(relevant),
                "sampled_label_recall_at_5": len(matched) / len(relevant), "hit_at_5": int(bool(matched)),
                "achievable_recall_at_5": min(K, len(relevant)) / len(relevant),
                "elapsed_seconds": time.perf_counter() - start,
            })
        results[mode] = rows
        summary = _metrics(rows)
        for field in ("query_kind", "ticker", "scenario_group_id"):
            groups = defaultdict(list)
            for row in rows:
                groups[row[field]].append(row)
            summary["by_" + field] = {group: _metrics(values) for group, values in sorted(groups.items())}
        summary["total_elapsed_seconds"] = sum(row["elapsed_seconds"] for row in rows)
        summaries[mode] = summary
    paired = {}
    if "bm25" in modes:
        for mode in modes:
            if mode == "bm25":
                continue
            differences = [after["sampled_label_recall_at_5"] - before["sampled_label_recall_at_5"]
                           for before, after in zip(results["bm25"], results[mode])]
            paired[mode + "_minus_bm25"] = {
                "query_count": len(differences), "improved": sum(value > 0 for value in differences),
                "unchanged": sum(value == 0 for value in differences),
                "regressed": sum(value < 0 for value in differences),
                "mean_sampled_label_recall_difference": sum(differences) / len(differences),
            }
    return {
        "status": "completed_with_errors" if any(value["errors"] for value in summaries.values()) else "completed",
        "evaluation_kind": "public_source_derived_development_comparison",
        "source_corpus_sha256": corpus.fingerprint, "query_labels_sha256": query_hash,
        "k": K, "query_count": len(cases),
        "label_count": sum(len(case["relevant_passages"]) for case in cases),
        "company_year_group_count": len({case["company_year_group_id"] for case in cases}),
        "scenario_group_count": len({case["scenario_group_id"] for case in cases}),
        "query_kind_counts": dict(sorted(Counter(case["query_kind"] for case in cases).items())),
        "tickers": sorted({case["ticker"] for case in cases}), "modes": list(modes),
        "label_review_status": "source_derived_not_human_reviewed",
        "canonical_evidence_unit": "original_cached_passage_id; no inferred duplicate relevance labels",
        "label_scope": "partial_relevant_passage_set",
        "metric_definition": "Per-query labelled relevant passage IDs in top five divided by that query's labelled set; macro-average over every attempted query.",
        "limitations": [
            "Partial source-derived labels are development checks, not exhaustive relevance, human labels or independent gold.",
            "Repeated topics across fiscal years are grouped and correlated; the thirty-six queries are not independent samples.",
            "BM25, hybrid and reranking use the same table-aware passage representation and exact issuer/year scope.",
            "A hit establishes labelled evidence retrieval, not answer correctness, risk interpretation or full-capstone success.",
            "Unlabelled relevant evidence may exist; no pass/fail claim against the provisional eighty-five-percent final target is made.",
            "Model/index initialization and warming vary by arm; elapsed time is diagnostic and is not a controlled latency benchmark.",
        ],
        "summaries": summaries, "paired_comparisons": paired, "per_query": results,
        "generative_model_calls": 0, "external_provider_requests": 0,
        "local_model_inference": "Hybrid embeds the query; hybrid_rerank also scores candidates with the local cross-encoder.",
    }


def write_receipt(path, receipt):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".retrieval-eval-", dir=path.parent, delete=False) as handle:
            stage = Path(handle.name)
            handle.write((json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(stage, path)
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--queries", default=DEFAULT_QUERIES, type=Path)
    parser.add_argument("--expected-query-sha256", default=FROZEN_QUERY_SHA256)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    arguments = parser.parse_args()
    if arguments.output.resolve() in {arguments.corpus.resolve(), arguments.queries.resolve()}:
        parser.error("The result output must differ from source and label files")
    result = evaluate(arguments.corpus, arguments.queries,
                      expected_query_sha256=arguments.expected_query_sha256, modes=tuple(arguments.modes))
    write_receipt(arguments.output, result)
    print(json.dumps({"status": result["status"], "query_count": result["query_count"],
                      "source_corpus_sha256": result["source_corpus_sha256"],
                      "query_labels_sha256": result["query_labels_sha256"],
                      "summaries": {mode: {key: value for key, value in summary.items() if not key.startswith("by_")}
                                    for mode, summary in result["summaries"].items()}}, indent=2))
    sys.exit(1 if result["status"] == "completed_with_errors" else 0)
