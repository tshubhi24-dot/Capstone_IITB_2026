"""Retrieval isolation, integrity and ranking checks with invented model vectors."""
from copy import deepcopy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
import threading
import time

import numpy as np
import pytest

from desk.data import Corpus
from desk.retrieval import (HybridRetriever, RetrievalError, _token_windows, canonical_hash,
                            decompose_query, document_text, load_config, verify_model_files, write_index)


class FakeModels:
    def __init__(self):
        self.queries = []
        self.reranked = []

    def encode(self, texts):
        self.queries.extend(texts)
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        vectors[:, 0] = 1
        return vectors

    def score(self, query, texts):
        self.reranked.append((query, texts))
        return np.array([10 if "target" in text else -10 for text in texts])


@pytest.fixture
def corpus(tmp_path):
    passages = [
        {"id": "a-keyword", "ticker": "A", "year": 2025, "text": "currency currency currency exposure"},
        {"id": "b-semantic", "ticker": "A", "year": 2025, "text": "target operational resilience"},
        {"id": "c-table", "ticker": "A", "year": 2025, "text": "Retained table fragment", "table": [["Location", "Risk"], ["Japan", "earthquake"]]},
        {"id": "d-other-year", "ticker": "A", "year": 2024, "text": "target currency exposure"},
        {"id": "e-other-issuer", "ticker": "B", "year": 2025, "text": "target currency exposure"},
    ]
    document = {"companies": [{"ticker": ticker} for ticker in ("A", "B")],
                "facts": [{"id": f"{ticker}-{year}", "ticker": ticker, "fiscal_year": year}
                          for ticker, year in (("A", 2024), ("A", 2025), ("B", 2025))],
                "passages": [{**row, "item": "1A"} for row in passages]}
    source = tmp_path / "source.json"
    source.write_text(json.dumps(document))
    return Corpus(source)


def built(corpus, tmp_path, **overrides):
    config = {**load_config(), **overrides}
    rows = sorted(corpus._passages.values(), key=lambda row: row["id"])
    vectors = np.zeros((len(rows), 384), dtype=np.float32)
    for index, row in enumerate(rows):
        vectors[index, 0 if row["id"] != "a-keyword" else 1] = 1
    output = tmp_path / "retrieval"
    write_index(output, corpus.fingerprint, rows, vectors, config)
    models = FakeModels()
    return HybridRetriever(corpus, artifacts=output, models=models, config=config), models, output


def test_bm25_baseline_needs_no_artifacts_and_searches_table_cells(corpus, tmp_path):
    retriever = HybridRetriever(corpus, artifacts=tmp_path / "absent")
    result = retriever.search("earthquake", "A", [2025], 1, mode="bm25")
    assert result[0]["id"] == "c-table"
    assert result[0]["text"] == "Retained table fragment"
    assert result[0]["table"][1] == ["Japan", "earthquake"]
    assert retriever._models is None and retriever.vectors is None


def test_simultaneous_first_searches_share_one_backend(corpus, monkeypatch):
    import desk.retrieval as module
    original, created = module.HybridRetriever, []
    def slow_constructor(*args, **kwargs):
        time.sleep(.03)
        value = original(*args, **kwargs)
        created.append(value)
        return value
    monkeypatch.setattr(module, "HybridRetriever", slow_constructor)
    barrier = threading.Barrier(4)
    def lookup(_):
        barrier.wait()
        return corpus._retrieval_backend("bm25")
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lookup, range(4)))
    assert len(created) == 1 and all(value is created[0] for value in values)


def test_simultaneous_first_model_use_loads_one_model_pair(corpus, tmp_path, monkeypatch):
    import desk.retrieval as module
    created = []
    def slow_models(*args, **kwargs):
        time.sleep(.03)
        value = FakeModels()
        created.append(value)
        return value
    monkeypatch.setattr(module, "LocalModels", slow_models)
    retriever = HybridRetriever(corpus, artifacts=tmp_path / "absent")
    barrier = threading.Barrier(4)
    def lookup(_):
        barrier.wait()
        return retriever.models
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lookup, range(4)))
    assert len(created) == 1 and all(value is created[0] for value in values)


def test_learned_modes_fail_closed_when_index_is_absent(corpus, tmp_path):
    retriever = HybridRetriever(corpus, artifacts=tmp_path / "absent", models=FakeModels())
    for mode in ("hybrid", "hybrid_rerank"):
        with pytest.raises(RetrievalError, match="artifacts"):
            retriever.search("currency", "A", [2025], mode=mode)


def test_scope_is_applied_before_dense_ranking_and_reranking(corpus, tmp_path):
    retriever, models, _ = built(corpus, tmp_path)
    original = retriever.dense_candidates
    seen = []
    def checked(vector, indices, limit):
        seen.extend(indices)
        assert all(retriever.rows[index]["ticker"] == "A" and retriever.rows[index]["year"] == 2025 for index in indices)
        return original(vector, indices, limit)
    retriever.dense_candidates = checked
    results = retriever.search("currency and operational resilience", "A", [2025], 3)
    assert seen and all(row["ticker"] == "A" and row["year"] == 2025 for row in results)
    assert all("other-" not in str(text) for _, texts in models.reranked for text in texts)
    assert models.queries == ["currency and operational resilience", "operational resilience"]
    assert all(row["retrieval"]["scoped_passages"] == 3 for row in results)


def test_dense_backend_cannot_return_another_issuer_or_year(corpus, tmp_path):
    retriever, _, _ = built(corpus, tmp_path)
    retriever.dense_candidates = lambda query, indices, limit: [(4, 100)]
    with pytest.raises(RetrievalError, match="outside"):
        retriever.search("currency", "A", [2025])


def test_reranker_can_promote_semantic_candidate_without_changing_source(corpus, tmp_path):
    retriever, models, _ = built(corpus, tmp_path, candidates_per_channel=1)
    hybrid = retriever.search("currency", "A", [2025], 2, mode="hybrid")
    reranked = retriever.search("currency", "A", [2025], 2, mode="hybrid_rerank")
    assert hybrid[0]["id"] == "a-keyword"
    assert reranked[0]["id"] == "b-semantic"
    assert models.reranked and len(models.reranked[0][1]) == 2
    assert reranked[0]["text"] == corpus.passage("b-semantic")["text"]
    assert reranked[0]["retrieval"]["rerank_score"] == 10
    assert hybrid[0]["retrieval"]["rerank_score"] is None


def test_explicit_mode_and_default_baseline_are_independent(corpus, tmp_path, monkeypatch):
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    monkeypatch.setenv("RETRIEVAL_ARTIFACTS", str(tmp_path / "absent"))
    assert corpus.search("earthquake", "A", [2025], 1)[0]["retrieval"]["mode"] == "bm25"
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid_rerank")
    with pytest.raises(RetrievalError):
        corpus.search("earthquake", "A", [2025], 1)
    assert corpus.search("earthquake", "A", [2025], 1, retrieval_mode="bm25")[0]["id"] == "c-table"


@pytest.mark.parametrize("change", ["source", "text", "configuration", "vectors", "manifest"])
def test_stale_or_tampered_artifacts_cannot_rank_evidence(corpus, tmp_path, change):
    retriever, _, output = built(corpus, tmp_path)
    if change == "source":
        corpus.fingerprint = "0" * 64
    elif change == "text":
        retriever.rows[0]["text"] += " changed"
    elif change == "configuration":
        retriever.config["rrf_k"] += 1
    elif change == "vectors":
        path = output / "vectors.npy"
        path.write_bytes(path.read_bytes() + b"changed")
    else:
        path = output / "manifest.json"
        value = json.loads(path.read_text())
        value["passage_count"] += 1
        path.write_text(json.dumps(value))
    with pytest.raises(RetrievalError):
        retriever.search("currency", "A", [2025])


def test_model_file_checksums_and_symlinks_are_checked_before_loading(tmp_path):
    root = tmp_path / "model"
    root.mkdir()
    data = root / "config.json"
    data.write_text("test model data")
    specification = {"files": {"config.json": hashlib.sha256(data.read_bytes()).hexdigest()}}
    verify_model_files(root, specification)
    data.write_text("modified model data")
    with pytest.raises(RetrievalError, match="checksum"):
        verify_model_files(root, specification)
    data.unlink()
    external = tmp_path / "outside.json"
    external.write_text("test model data")
    data.symlink_to(external)
    with pytest.raises(RetrievalError, match="unsafe"):
        verify_model_files(root, specification)


def test_query_decomposition_is_bounded_literal_and_deduplicated():
    assert decompose_query("currency exposure and cyber resilience; regulatory obligations and demand changes") == [
        "currency exposure and cyber resilience; regulatory obligations and demand changes", "currency exposure", "cyber resilience"]
    assert decompose_query("currency exposure and cyber resilience", 1) == ["currency exposure and cyber resilience"]
    assert decompose_query("cyber resilience and cyber resilience") == ["cyber resilience and cyber resilience", "cyber resilience"]
    with pytest.raises(RetrievalError):
        decompose_query("x" * 2001)


def test_text_policy_is_consistent_and_original_table_is_not_mutated():
    source = {"text": "Reported table", "table": [["Revenue", 100], ["Operating income", 10]]}
    before = deepcopy(source)
    assert "Revenue | 100" in document_text(source)
    assert document_text(source, False) == "Reported table"
    assert source == before


@pytest.mark.parametrize("mode,ticker,years,k", [("unknown", "A", [2025], 1), ("bm25", "X", [2025], 1),
                                                  ("bm25", "A", [2023], 1), ("bm25", "A", [], 1),
                                                  ("bm25", "A", [True], 1), ("bm25", "A", [2025], 11)])
def test_invalid_or_unavailable_scope_is_rejected(corpus, tmp_path, mode, ticker, years, k):
    retriever = HybridRetriever(corpus, artifacts=tmp_path / "absent")
    with pytest.raises(RetrievalError):
        retriever.search("currency", ticker, years, k, mode=mode)


def test_token_windows_cover_document_tail_without_silent_truncation():
    class CharacterTokenizer:
        def __call__(self, text, **kwargs):
            return {"offset_mapping": [(index, index + 1) for index in range(len(text))]}
    text = "abcdefghijklmnopqrstuvwxyz"
    windows = _token_windows(text, CharacterTokenizer(), 10, 2)
    assert windows == ["abcdefghij", "ijklmnopqr", "qrstuvwxyz"]
    assert text[-1] in windows[-1]


def test_preparation_is_atomic_and_reuses_only_matching_artifacts(corpus, tmp_path, monkeypatch):
    from ops import prepare_retrieval as preparation
    config = load_config()
    cache = tmp_path / "cache"
    payload = b"invented public model data for preparation test"
    for role in ("encoder", "reranker"):
        spec = config[role]
        spec["files"] = {"model.safetensors": hashlib.sha256(payload).hexdigest()}
        snapshot = cache / ("models--" + spec["id"].replace("/", "--")) / "snapshots" / spec["revision"]
        snapshot.mkdir(parents=True)
        (snapshot / "model.safetensors").write_bytes(payload)
    config_file = tmp_path / "test_config.json"
    config_file.write_text(json.dumps(config))
    models = FakeModels()
    monkeypatch.setattr(preparation, "LocalModels", lambda root, config: models)
    monkeypatch.setattr(preparation, "version", lambda name: "test-only")
    output = tmp_path / "prepared"
    result = preparation.prepare(corpus.path, output, cache, config_path=config_file)
    assert result["status"] == "prepared" and result["network_requests"] == 0
    assert len(models.queries) == len(corpus._passages)
    assert not list(tmp_path.glob("prepared.prepare-*"))
    reused = preparation.prepare(corpus.path, output, cache, config_path=config_file)
    assert reused["status"] == "reused"
    original = (output / "manifest.json").read_bytes()
    document = json.loads(corpus.path.read_text())
    document["passages"][0]["text"] += " source changed"
    corpus.path.write_text(json.dumps(document))
    with pytest.raises(RetrievalError, match="stale"):
        preparation.prepare(corpus.path, output, cache, config_path=config_file)
    assert (output / "manifest.json").read_bytes() == original


def test_preparation_never_publishes_a_partial_bundle_from_bad_cache(corpus, tmp_path):
    from ops.prepare_retrieval import prepare
    output = tmp_path / "prepared"
    with pytest.raises(RetrievalError, match="pinned model snapshot"):
        prepare(corpus.path, output, tmp_path / "empty-cache")
    assert not output.exists()
    assert not list(tmp_path.glob("prepared.prepare-*"))


def test_chroma_is_attached_only_for_learned_search_and_never_used_as_fallback(corpus, tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    retriever, _, _ = built(corpus, tmp_path)
    corpus._retriever = retriever
    attached = []
    def attach(value, url):
        attached.append((value, url))
        value.dense_backend = "chroma_cosine"
    monkeypatch.setitem(sys.modules, "desk.vector_store", SimpleNamespace(attach_chroma=attach))
    monkeypatch.setenv("CHROMA_URL", "http://test-vector-store:8000")
    corpus.search("currency", "A", [2025], retrieval_mode="bm25")
    assert not attached
    results = corpus.search("currency", "A", [2025], retrieval_mode="hybrid")
    corpus.search("currency", "A", [2025], retrieval_mode="hybrid_rerank")
    assert len(attached) == 1
    assert results[0]["retrieval"]["backend"] == "chroma_cosine"
    retriever._chroma_attached = False
    def unavailable(value, url):
        raise RetrievalError("Vector store unavailable")
    monkeypatch.setitem(sys.modules, "desk.vector_store", SimpleNamespace(attach_chroma=unavailable))
    with pytest.raises(RetrievalError, match="unavailable"):
        corpus.search("currency", "A", [2025], retrieval_mode="hybrid")


def test_baseline_readiness_does_not_load_models_or_require_an_index(corpus, tmp_path, monkeypatch):
    monkeypatch.setenv("RETRIEVAL_ARTIFACTS", str(tmp_path / "absent"))
    monkeypatch.setenv("CHROMA_URL", "http://test-vector-store:8000")
    status = corpus.retrieval_status(retrieval_mode="bm25")
    assert status["ready"] and status["backend"] == "bm25"
    assert status["semantic_retrieval"] is False
    assert status["source_fingerprint"] == corpus.fingerprint
    assert corpus._retriever._models is None


def test_learned_readiness_verifies_models_without_loading_them(corpus, tmp_path, monkeypatch):
    import desk.retrieval as retrieval
    retriever, _, _ = built(corpus, tmp_path)
    retriever._models = None
    corpus._retriever = retriever
    verified = []
    monkeypatch.delenv("CHROMA_URL", raising=False)
    monkeypatch.setattr(retrieval, "verify_model_files", lambda path, spec: verified.append(spec["id"]))
    status = corpus.retrieval_status(retrieval_mode="hybrid_rerank")
    assert status["ready"] and status["semantic_retrieval"]
    assert status["index_fingerprint"] == retriever.manifest["index_fingerprint"]
    assert verified == [retriever.config["encoder"]["id"], retriever.config["reranker"]["id"]]
    assert retriever._models is None
