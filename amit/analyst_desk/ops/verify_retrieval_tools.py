"""Read-only development retrieval check through the deployed authenticated MCP.

Run inside the app container with a separately mounted frozen question file.
Only retrieval_status and search_filings are called; this script never creates
a research run, invokes the paid gateway, submits approval or publishes a note.
"""
import argparse
import asyncio
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desk.data import Corpus
from desk.retrieval import HybridRetriever, canonical_hash, decompose_query
from desk.workflow import Engine
from ops.evaluate_retrieval import load_labels, write_receipt


class VerificationFailure(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _status_check(status, source, retriever):
    manifest, config = retriever.manifest, retriever.config
    if (not isinstance(status, dict) or status.get("ready") is not True
            or status.get("mode") != "hybrid_rerank" or status.get("backend") != "chroma_cosine"
            or status.get("semantic_retrieval") is not True or status.get("table_aware") is not True):
        raise VerificationFailure("configured_retrieval_not_ready")
    for field, expected in {
        "source_fingerprint": source.fingerprint,
        "index_fingerprint": manifest["index_fingerprint"],
        "configuration_hash": manifest["configuration_hash"],
        "model_fingerprint": manifest["model_fingerprint"],
        "query_policy": config["query_policy"], "text_policy": config["text_policy"],
        "encoder": {key: config["encoder"][key] for key in ("id", "revision")},
        "reranker": {key: config["reranker"][key] for key in ("id", "revision")},
    }.items():
        if status.get(field) != expected:
            raise VerificationFailure("deployed_retrieval_identity_differs")


def _check_results(source, retriever, case, results):
    if not isinstance(results, list) or not 1 <= len(results) <= 5:
        raise VerificationFailure("empty_or_invalid_result_count")
    manifest, config = retriever.manifest, retriever.config
    scope_count = sum(row["ticker"] == case["ticker"] and row["year"] in case["years"] for row in retriever.rows)
    variants = decompose_query(case["question"], config["max_query_parts"])
    identifiers, prior_score = [], math.inf
    for hit in results:
        if not isinstance(hit, dict) or not isinstance(hit.get("id"), str) or hit["id"] in identifiers:
            raise VerificationFailure("invalid_or_duplicate_source_id")
        try:
            original = source.passage(hit["id"])
        except ValueError as error:
            raise VerificationFailure("unknown_source_id") from error
        if original["ticker"] != case["ticker"] or original["year"] not in case["years"]:
            raise VerificationFailure("result_outside_issuer_year_scope")
        if any(key not in hit or hit[key] != value for key, value in original.items()):
            raise VerificationFailure("canonical_evidence_changed")
        metadata = hit.get("retrieval")
        if not isinstance(metadata, dict):
            raise VerificationFailure("retrieval_metadata_missing")
        expected = {
            "mode": "hybrid_rerank", "backend": "chroma_cosine", "table_aware": True,
            "configuration_hash": manifest["configuration_hash"],
            "index_fingerprint": manifest["index_fingerprint"],
            "model_fingerprint": manifest["model_fingerprint"],
            "query_variants": variants, "scoped_passages": scope_count,
        }
        if any(metadata.get(key) != value for key, value in expected.items()):
            raise VerificationFailure("retrieval_metadata_differs")
        candidates = metadata.get("rerank_candidate_count")
        score, rerank_score = hit.get("retrieval_score"), metadata.get("rerank_score")
        if (type(candidates) is not int or not len(results) <= candidates <= config["rerank_candidates"]
                or not _finite(score) or not _finite(rerank_score)
                or not math.isclose(score, rerank_score, abs_tol=1e-12, rel_tol=0)
                or score > prior_score or not _finite(metadata.get("rrf_score")) or metadata["rrf_score"] <= 0):
            raise VerificationFailure("reranking_score_or_order_invalid")
        for field in ("bm25_score", "dense_score"):
            if metadata.get(field) is not None and not _finite(metadata[field]):
                raise VerificationFailure("retrieval_channel_score_invalid")
        if metadata.get("dense_score") is not None and not -1.00001 <= metadata["dense_score"] <= 1.00001:
            raise VerificationFailure("retrieval_channel_score_invalid")
        identifiers.append(hit["id"])
        prior_score = score
    return identifiers


def _aggregate(rows):
    if not rows:
        return {"query_count": 0, "errors": 0, "sampled_label_recall_at_5": None, "hit_at_5": None}
    return {"query_count": len(rows), "errors": sum(row["status"] != "completed" for row in rows),
            "sampled_label_recall_at_5": sum(row["sampled_label_recall_at_5"] for row in rows) / len(rows),
            "hit_at_5": sum(row["hit_at_5"] for row in rows) / len(rows)}


async def verify(queries_path, query_sha256):
    """Admit frozen inputs, then perform one status call and each labelled search."""
    source = Corpus()
    cases, labels_hash = load_labels(queries_path, source, expected_query_sha256=query_sha256)
    retriever = HybridRetriever(source)
    retriever.load_index()
    # No Engine constructor, Store, model gateway or workflow execution is used.
    reader = object.__new__(Engine)
    calls, searches, status, preflight_error = 0, 0, None, None
    async def call(tool, arguments):
        nonlocal calls
        calls += 1
        return await reader._wire_call("researcher", "filings-kb", tool, arguments)
    try:
        status = await call("retrieval_status", {})
        _status_check(status, source, retriever)
    except Exception as error:
        preflight_error = {"error_type": type(error).__name__,
                           "failure_code": error.code if isinstance(error, VerificationFailure) else "status_tool_failed"}
    rows = []
    for case in cases:
        relevant = {label["passage_id"] for label in case["relevant_passages"]}
        ids, failure = [], preflight_error
        start = time.perf_counter()
        if preflight_error is None:
            searches += 1
            try:
                results = await call("search_filings", {"query": case["question"], "ticker": case["ticker"],
                                                        "years": case["years"], "k": 5})
                ids = _check_results(source, retriever, case, results)
            except Exception as error:
                failure = {"error_type": type(error).__name__,
                           "failure_code": error.code if isinstance(error, VerificationFailure) else "search_tool_failed"}
        matched = relevant & set(ids)
        rows.append({"query_id": case["id"], "scenario_group_id": case["scenario_group_id"],
                     "company_year_group_id": case["company_year_group_id"], "ticker": case["ticker"],
                     "years": case["years"], "query_kind": case["query_kind"],
                     "status": "blocked" if preflight_error else "error" if failure else "completed",
                     "error_type": failure["error_type"] if failure else None,
                     "failure_code": failure["failure_code"] if failure else None,
                     "retrieved_passage_ids": ids, "labelled_relevant_passage_ids": sorted(relevant),
                     "matched_passage_ids": sorted(matched), "labelled_relevant_count": len(relevant),
                     "sampled_label_recall_at_5": len(matched) / len(relevant), "hit_at_5": int(bool(matched)),
                     "achievable_recall_at_5": min(5, len(relevant)) / len(relevant),
                     "elapsed_seconds": time.perf_counter() - start})
    summary = _aggregate(rows)
    for field in ("query_kind", "ticker", "scenario_group_id"):
        groups = defaultdict(list)
        for row in rows:
            groups[row[field]].append(row)
        summary["by_" + field] = {key: _aggregate(values) for key, values in sorted(groups.items())}
    manifest = retriever.manifest
    return {
        "status": "passed" if not summary["errors"] else "failed",
        "verification_kind": "operator_authenticated_development_retrieval",
        "source_fingerprint": source.fingerprint, "query_labels_sha256": labels_hash,
        "index_fingerprint": manifest["index_fingerprint"], "configuration_hash": canonical_hash(retriever.config),
        "model_fingerprint": manifest["model_fingerprint"],
        "mode": "hybrid_rerank", "backend": "chroma_cosine", "k": 5,
        "retrieval_status_check": "passed" if preflight_error is None else "failed",
        "preflight_error": preflight_error,
        "query_count": len(cases), "queries_attempted": searches,
        "queries_completed": sum(row["status"] == "completed" for row in rows),
        "label_count": sum(len(case["relevant_passages"]) for case in cases),
        "authenticated_tool_calls": calls, "summary": summary, "per_query": rows,
        "label_review_status": "source_derived_not_human_reviewed",
        "label_scope": "partial_relevant_passage_set",
        "metric_definition": "Labelled relevant original passage IDs in top five divided by the query's labelled set; macro-average over all frozen queries, including errors and preflight-blocked cases.",
        "generative_model_calls": 0, "external_provider_requests": 0,
        "local_model_inference": "Queries use local learned embeddings and cross-encoder reranking through the authenticated filing tool.",
        "research_runs_created": 0, "human_decisions_submitted": 0, "notes_published": 0,
        "limitations": [
            "Partial source-derived development labels have not received independent human relevance review and are not exhaustive relevance or final gold.",
            "Questions cover four declared development issuers, twelve company/year groups and repeated correlated topics; the other eight issuers remain outside this question set.",
            "A successful source-integrity check establishes the configured tool path, not research answer quality or economic risk interpretation.",
            "Chroma performs scoped cosine candidate retrieval; this deployed check is reported separately from the host NumPy exact-cosine comparison.",
            "Elapsed times include MCP overhead, local inference and cache warming; they are diagnostic rather than a controlled latency benchmark.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", required=True, type=Path)
    parser.add_argument("--query-sha256", required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.output is not None and arguments.output.resolve() == arguments.queries.resolve():
        parser.error("The result output must differ from the frozen question file")
    try:
        result = asyncio.run(verify(arguments.queries, arguments.query_sha256))
        if arguments.output is not None:
            write_receipt(arguments.output, result)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        raise SystemExit(0 if result["status"] == "passed" else 1)
    except Exception as error:
        print("Retrieval tool verification admission failed: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
