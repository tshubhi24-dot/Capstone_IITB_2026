"""Authenticated operator-path verification using invented, frozen test sources."""
import asyncio
from copy import deepcopy
import json

import numpy as np
import pytest

from desk.data import Corpus
from desk.retrieval import canonical_hash, decompose_query, load_config, write_index
from desk.workflow import Engine
from ops import evaluate_retrieval as evaluation
from ops import verify_retrieval_tools as verification


@pytest.fixture
def deployed(tmp_path, monkeypatch):
    document = {"companies": [{"ticker": ticker} for ticker in sorted(evaluation.DEVELOPMENT_TICKERS)],
                "facts": [], "passages": []}
    for ticker in sorted(evaluation.DEVELOPMENT_TICKERS):
        for year in (2023, 2024, 2025):
            document["facts"].append({"id": f"{ticker}-{year}-fact", "ticker": ticker, "fiscal_year": year})
            for number in range(5):
                document["passages"].append({
                    "id": f"{ticker}-{year}-p{number}", "ticker": ticker, "year": year, "item": "7",
                    "source_url": "https://www.sec.gov/Archives/invented-test-source.htm",
                    "source_kind": "sec_edgar", "text": f"Invented public table narrative {number}.",
                    "table": [["Invented revenue", str(number + 100)]],
                })
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps(document))
    monkeypatch.setenv("CORPUS_PATH", str(corpus_path))
    source = Corpus(corpus_path)
    rows = sorted(source._passages.values(), key=lambda row: row["id"])
    vectors = np.zeros((len(rows), 384), dtype=np.float32)
    vectors[:, 0] = 1
    artifact = tmp_path / "retrieval"
    config = load_config()
    manifest = write_index(artifact, source.fingerprint, rows, vectors, config)
    monkeypatch.setenv("RETRIEVAL_ARTIFACTS", str(artifact))
    cases = []
    for ticker in sorted(evaluation.DEVELOPMENT_TICKERS):
        for year in (2023, 2024, 2025):
            for topic in range(3):
                labels = []
                for number in (0, 1):
                    passage = source.passage(f"{ticker}-{year}-p{number}")
                    labels.append({"passage_id": passage["id"], "item": passage["item"],
                                   "source_url": passage["source_url"],
                                   "evidence_sha256": evaluation.evidence_digest(passage),
                                   "relevance_basis": "Invented relevance for operator verification tests."})
                cases.append({
                    "id": f"retrieval-dev-{ticker.lower()}-{year}-{topic}", "ticker": ticker, "years": [year],
                    "split": "development", "scenario_group_id": f"{ticker}-{topic}",
                    "company_year_group_id": f"{ticker}-{year}",
                    "query_kind": "financial_table" if topic == 0 else "narrative",
                    "question": f"Find the source evidence for invented development question {len(cases)}.",
                    "source_corpus_sha256": source.fingerprint, "relevant_passages": labels,
                    "annotation_status": "source_derived_not_human_reviewed",
                    "label_scope": "partial_relevant_passage_set",
                })
    path = tmp_path / "queries.jsonl"
    path.write_text("".join(json.dumps(case) + "\n" for case in cases))
    question_map = {case["question"]: case for case in cases}
    status = {"ready": True, "mode": "hybrid_rerank", "backend": "chroma_cosine",
              "semantic_retrieval": True, "table_aware": True,
              "source_fingerprint": source.fingerprint, "index_fingerprint": manifest["index_fingerprint"],
              "configuration_hash": canonical_hash(config), "model_fingerprint": manifest["model_fingerprint"],
              "query_policy": config["query_policy"], "text_policy": config["text_policy"],
              **{role: {key: config[role][key] for key in ("id", "revision")} for role in ("encoder", "reranker")}}
    calls, mutations = [], {"status": None, "results": None, "failure_question": None, "status_error": False}
    async def wire(self, role, server, tool, arguments):
        assert role == "researcher" and server == "filings-kb"
        calls.append((role, server, tool, deepcopy(arguments)))
        if tool == "retrieval_status":
            assert arguments == {}
            if mutations["status_error"]:
                raise RuntimeError("A private token or provider error must not enter the public receipt")
            value = deepcopy(status)
            if mutations["status"]:
                mutations["status"](value)
            return value
        assert tool == "search_filings" and arguments["k"] == 5
        case = question_map[arguments["query"]]
        assert arguments["ticker"] == case["ticker"] and arguments["years"] == case["years"]
        if case["question"] == mutations["failure_question"]:
            raise RuntimeError("A private token or provider error must not enter the public receipt")
        results = []
        for number in range(3):
            passage = source.passage(f"{case['ticker']}-{case['years'][0]}-p{number}")
            score = 3. - number
            results.append({**passage, "retrieval_score": score, "retrieval": {
                "mode": "hybrid_rerank", "backend": "chroma_cosine", "table_aware": True,
                "configuration_hash": manifest["configuration_hash"],
                "index_fingerprint": manifest["index_fingerprint"], "model_fingerprint": manifest["model_fingerprint"],
                "query_variants": decompose_query(case["question"], config["max_query_parts"]),
                "scoped_passages": 5, "rerank_candidate_count": 3, "rerank_score": score,
                "rrf_score": .03, "bm25_score": 1., "dense_score": .3,
            }})
        if mutations["results"]:
            mutations["results"](results)
        return results
    monkeypatch.setattr(Engine, "_wire_call", wire)
    return {"queries": path, "sha256": evaluation.digest(path.read_bytes()), "source": source,
            "cases": cases, "calls": calls, "mutations": mutations}


def run(deployed):
    return asyncio.run(verification.verify(deployed["queries"], deployed["sha256"]))


def test_checks_deployed_status_and_all_queries_only_through_read_tools(deployed, monkeypatch):
    monkeypatch.setattr(Engine, "__init__", lambda *args, **kwargs: pytest.fail("Must not construct a workflow"))
    result = run(deployed)
    assert result["status"] == "passed"
    assert result["authenticated_tool_calls"] == 37
    assert result["query_count"] == result["queries_attempted"] == result["queries_completed"] == 36
    assert result["label_count"] == 72
    assert result["summary"]["sampled_label_recall_at_5"] == result["summary"]["hit_at_5"] == 1
    assert result["summary"]["errors"] == 0
    assert deployed["calls"][0][2] == "retrieval_status"
    assert all(call[2] == "search_filings" for call in deployed["calls"][1:])
    assert result["generative_model_calls"] == result["external_provider_requests"] == 0
    assert result["research_runs_created"] == result["human_decisions_submitted"] == result["notes_published"] == 0
    assert result["label_scope"] == "partial_relevant_passage_set"
    assert result["label_review_status"] == "source_derived_not_human_reviewed"


def test_tool_failure_remains_in_denominator_and_does_not_suppress_later_queries(deployed):
    deployed["mutations"]["failure_question"] = deployed["cases"][0]["question"]
    result = run(deployed)
    assert result["status"] == "failed" and result["authenticated_tool_calls"] == 37
    assert result["queries_attempted"] == 36 and result["queries_completed"] == 35
    assert result["summary"]["query_count"] == 36 and result["summary"]["errors"] == 1
    assert result["summary"]["sampled_label_recall_at_5"] == result["summary"]["hit_at_5"] == 35 / 36
    assert result["per_query"][0]["failure_code"] == "search_tool_failed"
    assert result["per_query"][0]["retrieved_passage_ids"] == []
    assert "private token" not in json.dumps(result)


@pytest.mark.parametrize("field,value", [
    ("ready", False), ("mode", "bm25"), ("mode", "hybrid"), ("backend", "numpy_exact_cosine"),
    ("source_fingerprint", "0" * 64), ("index_fingerprint", "0" * 64),
    ("configuration_hash", "0" * 64), ("model_fingerprint", "0" * 64),
    ("table_aware", False), ("encoder", {"id": "other"}), ("reranker", {"id": "other"}),
])
def test_status_mismatch_stops_before_search_and_keeps_all_cases_blocked(deployed, field, value):
    deployed["mutations"]["status"] = lambda status: status.update({field: value})
    result = run(deployed)
    assert result["status"] == "failed" and result["authenticated_tool_calls"] == 1
    assert result["retrieval_status_check"] == "failed"
    assert result["queries_attempted"] == result["queries_completed"] == 0
    assert result["summary"]["query_count"] == result["summary"]["errors"] == 36
    assert result["summary"]["sampled_label_recall_at_5"] == 0
    assert all(row["status"] == "blocked" for row in result["per_query"])


def test_status_transport_failure_has_no_sensitive_error_output(deployed):
    deployed["mutations"]["status_error"] = True
    result = run(deployed)
    assert result["status"] == "failed" and result["authenticated_tool_calls"] == 1
    assert result["preflight_error"] == {"error_type": "RuntimeError", "failure_code": "status_tool_failed"}
    assert "private token" not in json.dumps(result)


@pytest.mark.parametrize("mutation,code", [
    (lambda results: results[0].update(text="Changed evidence"), "canonical_evidence_changed"),
    (lambda results: results[0]["table"][0].__setitem__(1, "999999"), "canonical_evidence_changed"),
    (lambda results: results[0].update(source_url="https://public.example.com"), "canonical_evidence_changed"),
    (lambda results: results[0].pop("table"), "canonical_evidence_changed"),
    (lambda results: results[1].update(id=results[0]["id"]), "invalid_or_duplicate_source_id"),
    (lambda results: results[0].update(id="unknown"), "unknown_source_id"),
    (lambda results: results[0].update(id="MSFT-2025-p0"), "result_outside_issuer_year_scope"),
    (lambda results: results[0].pop("retrieval"), "retrieval_metadata_missing"),
    (lambda results: results[0]["retrieval"].update(mode="bm25"), "retrieval_metadata_differs"),
    (lambda results: results[0]["retrieval"].update(backend="numpy_exact_cosine"), "retrieval_metadata_differs"),
    (lambda results: results[0]["retrieval"].update(index_fingerprint="0" * 64), "retrieval_metadata_differs"),
    (lambda results: results[0]["retrieval"].update(model_fingerprint="0" * 64), "retrieval_metadata_differs"),
    (lambda results: results[0]["retrieval"].update(configuration_hash="0" * 64), "retrieval_metadata_differs"),
    (lambda results: results[0]["retrieval"].update(scoped_passages=99), "retrieval_metadata_differs"),
    (lambda results: results[0]["retrieval"].update(query_variants=["Invented query"]), "retrieval_metadata_differs"),
    (lambda results: results[0]["retrieval"].update(rerank_score=None), "reranking_score_or_order_invalid"),
    (lambda results: results[0]["retrieval"].update(rerank_candidate_count=100), "reranking_score_or_order_invalid"),
    (lambda results: results[0].update(retrieval_score=float("nan")), "reranking_score_or_order_invalid"),
    (lambda results: results[0].update(retrieval_score=2.5), "reranking_score_or_order_invalid"),
    (lambda results: results.reverse(), "reranking_score_or_order_invalid"),
    (lambda results: results[0]["retrieval"].update(rrf_score=0), "reranking_score_or_order_invalid"),
    (lambda results: results[0]["retrieval"].update(dense_score=float("nan")), "retrieval_channel_score_invalid"),
    (lambda results: results[0]["retrieval"].update(dense_score=2), "retrieval_channel_score_invalid"),
    (lambda results: results.clear(), "empty_or_invalid_result_count"),
    (lambda results: results.extend(deepcopy(results)), "empty_or_invalid_result_count"),
])
def test_invalid_deployed_evidence_is_a_recorded_failure(deployed, mutation, code):
    deployed["mutations"]["results"] = mutation
    result = run(deployed)
    assert result["status"] == "failed" and result["authenticated_tool_calls"] == 37
    assert result["queries_attempted"] == 36 and result["summary"]["query_count"] == 36
    assert result["per_query"][0]["failure_code"] == code
    assert result["per_query"][0]["sampled_label_recall_at_5"] == 0


def test_unretrieved_prepared_labels_count_as_misses_without_inventing_failure(deployed):
    # All returned evidence remains canonical and valid, but these IDs omit p0/p1.
    original = deployed["source"]
    def replace(results):
        for index, hit in enumerate(results):
            passage = original.passage(f"{hit['ticker']}-{hit['year']}-p{index + 2}")
            hit.update(passage)
    deployed["mutations"]["results"] = replace
    result = run(deployed)
    assert result["status"] == "passed" and result["queries_completed"] == 36
    assert result["summary"]["sampled_label_recall_at_5"] == result["summary"]["hit_at_5"] == 0
    assert result["summary"]["errors"] == 0


def test_changed_question_hash_is_rejected_before_any_tool_call(deployed):
    with pytest.raises(ValueError, match="frozen query hash"):
        asyncio.run(verification.verify(deployed["queries"], "0" * 64))
    assert deployed["calls"] == []


def test_operator_verification_preserves_source_query_and_index_files(deployed):
    before_queries = deployed["queries"].read_bytes()
    before_source = deployed["source"].path.read_bytes()
    result = run(deployed)
    assert result["status"] == "passed"
    assert deployed["queries"].read_bytes() == before_queries
    assert deployed["source"].path.read_bytes() == before_source
