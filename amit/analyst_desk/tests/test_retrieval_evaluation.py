"""Metric integrity and source-boundary checks with invented test evidence."""
from copy import deepcopy
import json

import pytest

from desk.data import Corpus
from ops import evaluate_retrieval as evaluation


@pytest.fixture
def source(tmp_path):
    document = {"companies": [{"ticker": ticker} for ticker in sorted(evaluation.DEVELOPMENT_TICKERS)],
                "facts": [], "passages": []}
    for ticker in sorted(evaluation.DEVELOPMENT_TICKERS):
        for year in sorted(evaluation.YEARS):
            document["facts"].append({"id": f"{ticker}-{year}-fact", "ticker": ticker, "fiscal_year": year})
            for number in range(7):
                document["passages"].append({
                    "id": f"{ticker}-{year}-passage-{number}", "ticker": ticker,
                    "year": year, "item": "7", "source_url": "https://www.sec.gov/invented-test-source",
                    "text": f"Invented test passage {number} about operating risk and annual results.",
                    "table": [["Invented revenue", str(100 + number)]],
                })
    corpus_path, queries_path = tmp_path / "corpus.json", tmp_path / "queries.jsonl"
    corpus_path.write_text(json.dumps(document))
    corpus = Corpus(corpus_path)
    cases = []
    for ticker in sorted(evaluation.DEVELOPMENT_TICKERS):
        for year in sorted(evaluation.YEARS):
            for topic in range(3):
                relevant = []
                for number in (0, 1):
                    passage = corpus.passage(f"{ticker}-{year}-passage-{number}")
                    relevant.append({"passage_id": passage["id"], "item": passage["item"],
                                     "source_url": passage["source_url"],
                                     "evidence_sha256": evaluation.evidence_digest(passage),
                                     "relevance_basis": "Invented relevance for metric-integrity tests."})
                cases.append({
                    "id": f"retrieval-dev-{ticker.lower()}-{year}-{topic}", "split": "development",
                    "ticker": ticker, "years": [year], "scenario_group_id": f"{ticker}-{topic}",
                    "company_year_group_id": f"{ticker}-{year}", "query_kind": "financial_table" if topic == 0 else "narrative",
                    "question": f"Find the evidence for invented development case {len(cases)}.",
                    "source_corpus_sha256": corpus.fingerprint,
                    "annotation_status": "source_derived_not_human_reviewed",
                    "label_scope": "partial_relevant_passage_set", "relevant_passages": relevant,
                })
    def persist():
        queries_path.write_text("".join(json.dumps(case) + "\n" for case in cases))
        return evaluation.digest(queries_path.read_bytes())
    return {"corpus_path": corpus_path, "queries_path": queries_path, "corpus": corpus,
            "document": document, "cases": cases, "persist": persist}


def labels(source):
    return evaluation.load_labels(source["queries_path"], source["corpus"],
                                  expected_query_sha256=source["persist"]())[0]


def run(source, **kwargs):
    return evaluation.evaluate(source["corpus_path"], source["queries_path"],
                               expected_query_sha256=source["persist"](), **kwargs)


def test_paired_metrics_preserve_all_attempts_and_denominators(source, monkeypatch):
    def search(self, query, ticker, years, k, retrieval_mode):
        assert k == 5
        if retrieval_mode == "hybrid_rerank" and "case 0." in query:
            raise RuntimeError("Private failure text must not enter a public receipt")
        numbers = [0] if retrieval_mode == "bm25" else [0, 1]
        return [self.passage(f"{ticker}-{years[0]}-passage-{number}") for number in numbers]
    monkeypatch.setattr(Corpus, "search", search)
    result = run(source)
    assert result["status"] == "completed_with_errors"
    assert result["query_count"] == 36 and result["label_count"] == 72
    assert result["scenario_group_count"] == 12 and result["company_year_group_count"] == 12
    assert result["summaries"]["bm25"]["sampled_label_recall_at_5"] == .5
    assert result["summaries"]["hybrid"]["sampled_label_recall_at_5"] == 1
    assert result["summaries"]["hybrid_rerank"]["attempted"] == 36
    assert result["summaries"]["hybrid_rerank"]["errors"] == 1
    assert result["summaries"]["hybrid_rerank"]["sampled_label_recall_at_5"] == 35 / 36
    assert result["per_query"]["hybrid_rerank"][0]["sampled_label_recall_at_5"] == 0
    assert result["paired_comparisons"]["hybrid_minus_bm25"]["improved"] == 36
    assert result["paired_comparisons"]["hybrid_rerank_minus_bm25"]["regressed"] == 1
    assert result["summaries"]["bm25"]["hit_at_5"] == 1
    assert result["generative_model_calls"] == 0 and result["external_provider_requests"] == 0
    assert "Private failure text" not in json.dumps(result)


def test_empty_results_are_zero_recall_and_remain_in_denominator(source, monkeypatch):
    monkeypatch.setattr(Corpus, "search", lambda *args, **kwargs: [])
    result = run(source, modes=("bm25",))
    assert result["status"] == "completed"
    assert result["summaries"]["bm25"]["attempted"] == 36
    assert result["summaries"]["bm25"]["hit_at_5"] == 0
    assert result["summaries"]["bm25"]["sampled_label_recall_at_5"] == 0


def test_more_than_five_relevant_passages_retain_actual_recall_ceiling(source, monkeypatch):
    case = source["cases"][0]
    for number in range(2, 7):
        passage = source["corpus"].passage(f"{case['ticker']}-{case['years'][0]}-passage-{number}")
        case["relevant_passages"].append({"passage_id": passage["id"], "item": passage["item"],
                                         "source_url": passage["source_url"],
                                         "evidence_sha256": evaluation.evidence_digest(passage),
                                         "relevance_basis": "Additional genuinely labelled fixture passage."})
    monkeypatch.setattr(Corpus, "search", lambda self, query, ticker, years, **kw:
                        [self.passage(f"{ticker}-{years[0]}-passage-{number}") for number in range(5)])
    result = run(source, modes=("bm25",))
    row = result["per_query"]["bm25"][0]
    assert row["labelled_relevant_count"] == 7
    assert row["sampled_label_recall_at_5"] == row["achievable_recall_at_5"] == 5 / 7


@pytest.mark.parametrize("mutation,match", [
    (lambda cases: cases[0].update(ticker="GOOGL"), "development issuers"),
    (lambda cases: cases[0].update(split="held_out"), "development issuers"),
    (lambda cases: cases[0].update(years=[2022]), "fiscal-year"),
    (lambda cases: cases[0].update(years=[True]), "fiscal-year"),
    (lambda cases: cases[0].update(years=[[2023]]), "fiscal-year"),
    (lambda cases: cases[0].update(years=[2023, 2023]), "fiscal-year"),
    (lambda cases: cases[0].update(source_corpus_sha256="0" * 64), "source hash"),
    (lambda cases: cases[0].update(annotation_status="human_reviewed"), "review status"),
    (lambda cases: cases[0].update(label_scope="complete_gold"), "partial"),
    (lambda cases: cases[0].update(query_kind="numeric_truth"), "question kind"),
    (lambda cases: cases[0].update(question="tiny"), "substantive"),
    (lambda cases: cases[0].update(relevant_passages=[]), "nonempty"),
    (lambda cases: cases[0].update(id=cases[1]["id"]), "Duplicate query"),
    (lambda cases: cases[0].update(scenario_group_id=""), "groups"),
    (lambda cases: cases[0]["relevant_passages"].append(deepcopy(cases[0]["relevant_passages"][0])), "Duplicate relevant"),
    (lambda cases: cases[0]["relevant_passages"][0].update(evidence_sha256="0" * 64), "provenance"),
    (lambda cases: cases[0]["relevant_passages"][0].update(source_url="https://www.example.com"), "provenance"),
    (lambda cases: cases[0]["relevant_passages"][0].update(relevance_basis=""), "explanation"),
])
def test_label_tampering_fails_before_search(source, monkeypatch, mutation, match):
    mutation(source["cases"])
    monkeypatch.setattr(Corpus, "search", lambda *args, **kwargs: pytest.fail("Search ran before admission"))
    with pytest.raises(ValueError, match=match):
        run(source)


def test_hash_must_be_frozen_and_checked_before_search(source, monkeypatch):
    source["persist"]()
    monkeypatch.setattr(Corpus, "search", lambda *args, **kwargs: pytest.fail("Search ran before hash check"))
    with pytest.raises(ValueError, match="frozen query hash"):
        evaluation.evaluate(source["corpus_path"], source["queries_path"], expected_query_sha256="0" * 64)
    with pytest.raises(ValueError, match="explicit frozen"):
        evaluation.evaluate(source["corpus_path"], source["queries_path"], expected_query_sha256=None)


def test_minimum_query_count_cannot_be_met_with_empty_template(source):
    del source["cases"][29:]
    with pytest.raises(ValueError, match="thirty"):
        labels(source)


def test_relevant_evidence_cannot_cross_company_or_year(source):
    source["cases"][0]["relevant_passages"][0]["passage_id"] = "MSFT-2025-passage-0"
    with pytest.raises(ValueError, match="outside"):
        labels(source)


def test_actual_table_cells_are_part_of_label_content_hash(source):
    passage = source["corpus"].passage(source["cases"][0]["relevant_passages"][0]["passage_id"])
    before = evaluation.evidence_digest(passage)
    passage["table"][0][1] = "999999"
    assert evaluation.evidence_digest(passage) != before


def test_financial_table_labels_cannot_point_to_plain_narrative(source):
    passage_id = source["cases"][0]["relevant_passages"][0]["passage_id"]
    passage = source["corpus"]._passages[passage_id]
    del passage["table"]
    source["cases"][0]["relevant_passages"][0]["evidence_sha256"] = evaluation.evidence_digest(passage)
    with pytest.raises(ValueError, match="retained table"):
        labels(source)


@pytest.mark.parametrize("kind", ["duplicate", "outside_scope", "too_many", "unknown"])
def test_invalid_search_results_count_as_errors_not_dropped_cases(source, monkeypatch, kind):
    def search(self, query, ticker, years, **kwargs):
        passage = self.passage(f"{ticker}-{years[0]}-passage-0")
        if kind == "duplicate":
            return [passage, passage]
        if kind == "outside_scope":
            other = next(value for value in evaluation.DEVELOPMENT_TICKERS if value != ticker)
            return [self.passage(f"{other}-{years[0]}-passage-0")]
        if kind == "too_many":
            return [self.passage(f"{ticker}-{years[0]}-passage-{number}") for number in range(6)]
        return [{"id": "missing"}]
    monkeypatch.setattr(Corpus, "search", search)
    result = run(source, modes=("bm25",))
    assert result["status"] == "completed_with_errors"
    assert result["summaries"]["bm25"]["errors"] == 36
    assert result["summaries"]["bm25"]["sampled_label_recall_at_5"] == 0


def test_receipt_write_does_not_change_queries_or_sources(source, monkeypatch, tmp_path):
    monkeypatch.setattr(Corpus, "search", lambda *args, **kwargs: [])
    source["persist"]()
    original = {key: source[key].read_bytes() for key in ("queries_path", "corpus_path")}
    result = run(source, modes=("bm25",))
    target = tmp_path / "result.json"
    evaluation.write_receipt(target, result)
    assert json.loads(target.read_bytes()) == result
    assert all(source[key].read_bytes() == value for key, value in original.items())
    assert not list(tmp_path.glob(".retrieval-eval-*"))


def test_committed_query_pack_matches_its_frozen_hash_and_dev_partition():
    raw = evaluation.DEFAULT_QUERIES.read_bytes()
    assert evaluation.digest(raw) == evaluation.FROZEN_QUERY_SHA256
    cases = [json.loads(line) for line in raw.splitlines()]
    assert len(cases) == 36
    assert {case["ticker"] for case in cases} == evaluation.DEVELOPMENT_TICKERS
    assert len({case["company_year_group_id"] for case in cases}) == 12
    assert len({case["scenario_group_id"] for case in cases}) == 12
    assert sum(case["query_kind"] == "financial_table" for case in cases) == 12
    assert sum(len(case["relevant_passages"]) for case in cases) == 42
    assert all(case["label_scope"] == "partial_relevant_passage_set" for case in cases)
