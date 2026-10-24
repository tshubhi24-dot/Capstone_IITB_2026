"""Chroma boundary checks with an in-memory fake; no models or network."""
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from desk.retrieval import RetrievalError
from desk import vector_store as store


class FakeCollection:
    def __init__(self, name, metadata):
        self.name, self.metadata = name, deepcopy(metadata)
        self.records = {}
        self.add_calls = 0
        self.query_calls = []
        self.mutate_result = None

    def count(self):
        return len(self.records)

    def add(self, *, ids, embeddings, metadatas):
        self.add_calls += 1
        for identifier, vector, metadata in zip(ids, embeddings, metadatas):
            assert identifier not in self.records
            self.records[identifier] = {"embedding": deepcopy(vector), "metadata": deepcopy(metadata)}

    def get(self, *, limit, offset, include):
        assert include == ["metadatas", "embeddings"]
        ids = list(self.records)[offset:offset + limit]
        return {"ids": ids, "metadatas": [deepcopy(self.records[key]["metadata"]) for key in ids],
                "embeddings": np.array([self.records[key]["embedding"] for key in ids])}

    def query(self, *, query_embeddings, n_results, where, include):
        assert include == ["distances", "metadatas"]
        self.query_calls.append({"query_embeddings": query_embeddings, "n_results": n_results, "where": where})
        rows = []
        for identifier, record in self.records.items():
            allowed = True
            for clause in where["$and"]:
                for field, condition in clause.items():
                    if "$eq" in condition:
                        allowed &= record["metadata"][field] == condition["$eq"]
                    if "$in" in condition:
                        allowed &= record["metadata"][field] in condition["$in"]
            if allowed:
                score = float(np.dot(record["embedding"], query_embeddings[0]))
                rows.append((identifier, 1 - score))
        rows.sort(key=lambda row: (row[1], row[0]))
        rows = rows[:n_results]
        result = {"ids": [[row[0] for row in rows]], "distances": [[row[1] for row in rows]],
                  "metadatas": [[deepcopy(self.records[row[0]]["metadata"]) for row in rows]]}
        if self.mutate_result:
            self.mutate_result(result)
        return result


class FakeClient:
    def __init__(self):
        self.collections = {}
        self.create_calls = 0

    def get_collection(self, *, name, embedding_function):
        assert embedding_function is None
        if name not in self.collections:
            from chromadb.errors import NotFoundError
            raise NotFoundError("Invented missing collection")
        return self.collections[name]

    def create_collection(self, *, name, metadata, embedding_function):
        assert embedding_function is None
        self.create_calls += 1
        assert name not in self.collections
        collection = FakeCollection(name, metadata)
        self.collections[name] = collection
        return collection


@pytest.fixture
def retriever():
    rows = [
        {"id": "aapl-2023-a", "ticker": "AAPL", "year": 2023},
        {"id": "aapl-2023-b", "ticker": "AAPL", "year": 2023},
        {"id": "aapl-2024-a", "ticker": "AAPL", "year": 2024},
        {"id": "aapl-2025-a", "ticker": "AAPL", "year": 2025},
        {"id": "msft-2023-a", "ticker": "MSFT", "year": 2023},
    ]
    vectors = np.array([[1, 0, 0], [.6, .8, 0], [0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=np.float32)
    manifest = {field: str(index + 1) * 64 for index, field in enumerate(store.FINGERPRINT_FIELDS)}
    manifest.update({"dimension": 3, "passage_count": len(rows),
                     "rows": [{"id": row["id"], "ticker": row["ticker"], "year": row["year"],
                               "text_sha256": "a" * 64} for row in rows]})
    return SimpleNamespace(rows=rows, vectors=vectors, manifest=manifest, load_index=lambda: None,
                           dense_backend="numpy_exact_cosine")


def prepared(retriever):
    client = FakeClient()
    receipt = store.populate_chroma(retriever, "http://chroma:8000", client=client)
    collection = client.collections[receipt["collection"]]
    return client, collection, receipt


def test_population_uses_only_precomputed_vectors_and_no_embedding_function(retriever):
    client, collection, receipt = prepared(retriever)
    assert receipt["status"] == "populated"
    assert client.create_calls == 1
    assert collection.count() == 5
    assert collection.metadata["hnsw:space"] == "cosine"
    assert receipt["local_embedding_calls"] == receipt["generative_model_calls"] == receipt["external_provider_requests"] == 0
    assert all("passage_id" in record["metadata"] for record in collection.records.values())
    assert all(set(record) == {"embedding", "metadata"} for record in collection.records.values())
    for index, row in enumerate(retriever.rows):
        assert np.array_equal(np.asarray(collection.records[row["id"]]["embedding"], dtype=np.float32), retriever.vectors[index])


def test_repeat_population_reuses_complete_immutable_collection(retriever):
    client, collection, receipt = prepared(retriever)
    before = deepcopy(collection.records)
    again = store.populate_chroma(retriever, "http://chroma:8000", client=client)
    assert again["status"] == "reused" and again["collection"] == receipt["collection"]
    assert client.create_calls == 1 and collection.add_calls == 1
    assert collection.records == before


def test_only_bounded_float32_storage_roundoff_is_accepted(retriever):
    _, collection, _ = prepared(retriever)
    vector = collection.records["aapl-2023-a"]["embedding"]
    vector[2] = 5e-8
    store.validate_collection(retriever, collection)
    vector[2] = 2e-7
    with pytest.raises(RetrievalError, match="stored vectors"):
        store.validate_collection(retriever, collection)


def test_query_filters_company_year_and_exact_allowed_ids_before_ranking(retriever):
    client, collection, _ = prepared(retriever)
    adapter = store.attach_chroma(retriever, "http://chroma:8000", client=client)
    assert retriever.dense_backend == "chroma_cosine"
    # AAPL FY2023 has two passages; another issuer has a tied perfect vector.
    result = retriever.dense_candidates(np.array([1, 0, 0], dtype=np.float32), [0, 1], 5)
    assert [index for index, _ in result] == [0, 1]
    assert result[0][1] == pytest.approx(1)
    assert result[1][1] == pytest.approx(.6)
    clauses = collection.query_calls[0]["where"]["$and"]
    assert {"ticker": {"$eq": "AAPL"}} in clauses
    assert {"year": {"$in": [2023]}} in clauses
    assert {"passage_id": {"$in": ["aapl-2023-a", "aapl-2023-b"]}} in clauses
    # A narrower ID subset must not widen just because its issuer/year matches.
    assert adapter.dense_candidates(np.array([1, 0, 0]), [1], 5) == [(1, pytest.approx(.6))]


def test_multiyear_scope_is_filtered_before_ranking(retriever):
    client, collection, _ = prepared(retriever)
    adapter = store.attach_chroma(retriever, "http://chroma:8000", client=client)
    assert [index for index, _ in adapter.dense_candidates(np.array([0, 1, 0]), [0, 1, 2], 2)] == [2, 1]
    assert {"year": {"$in": [2023, 2024]}} in collection.query_calls[-1]["where"]["$and"]


@pytest.mark.parametrize("mutation,match", [
    (lambda collection: collection.metadata.update(corpus_fingerprint="0" * 64), "fingerprint"),
    (lambda collection: collection.metadata.update(configuration_hash="0" * 64), "fingerprint"),
    (lambda collection: collection.metadata.update(**{"hnsw:space": "l2"}), "cosine"),
    (lambda collection: collection.records.pop("aapl-2023-a"), "count"),
    (lambda collection: collection.records["aapl-2023-a"]["metadata"].update(ticker="MSFT"), "metadata"),
    (lambda collection: collection.records["aapl-2023-a"]["metadata"].update(year=2024), "metadata"),
    (lambda collection: collection.records["aapl-2023-a"]["metadata"].update(text_sha256="0" * 64), "metadata"),
    (lambda collection: collection.records["aapl-2023-a"]["embedding"].__setitem__(0, .99), "stored vectors"),
    (lambda collection: collection.records.update(unknown=collection.records.pop("aapl-2023-a")), "unknown"),
])
def test_stale_or_corrupt_collection_fails_closed_without_repopulation(retriever, mutation, match):
    client, collection, _ = prepared(retriever)
    mutation(collection)
    before = deepcopy(collection.records)
    with pytest.raises(RetrievalError, match=match):
        store.attach_chroma(retriever, "http://chroma:8000", client=client)
    assert retriever.dense_backend == "numpy_exact_cosine"
    assert client.create_calls == 1 and collection.add_calls == 1 and not collection.query_calls
    assert collection.records == before
    with pytest.raises(RetrievalError, match=match):
        store.populate_chroma(retriever, "http://chroma:8000", client=client)
    assert client.create_calls == 1 and collection.add_calls == 1


def test_runtime_attachment_never_creates_a_missing_collection(retriever):
    client = FakeClient()
    with pytest.raises(RetrievalError, match="populate it explicitly"):
        store.attach_chroma(retriever, "http://chroma:8000", client=client)
    assert not client.collections and client.create_calls == 0


@pytest.mark.parametrize("mutation,match", [
    (lambda result: result["ids"][0].__setitem__(0, "msft-2023-a"), "out-of-scope"),
    (lambda result: result["ids"][0].__setitem__(1, result["ids"][0][0]), "duplicate"),
    (lambda result: result["distances"][0].__setitem__(0, float("nan")), "cosine distance"),
    (lambda result: result["distances"][0].__setitem__(0, 3), "cosine distance"),
    (lambda result: result["distances"][0].__setitem__(0, True), "cosine distance"),
    (lambda result: result["distances"][0].__setitem__(0, .5), "prepared evidence vector"),
    (lambda result: result["metadatas"][0][0].update(year=2024), "scope metadata"),
    (lambda result: result["ids"][0].pop(), "incomplete"),
])
def test_returned_candidates_cannot_escape_scope_or_invent_scores(retriever, mutation, match):
    client, collection, _ = prepared(retriever)
    adapter = store.attach_chroma(retriever, "http://chroma:8000", client=client)
    collection.mutate_result = mutation
    with pytest.raises(RetrievalError, match=match):
        adapter.dense_candidates(np.array([1, 0, 0]), [0, 1], 5)


@pytest.mark.parametrize("vector,scope,limit", [
    ([float("nan"), 0, 0], [0], 5), ([0, 0, 0], [0], 5), ([1, 0], [0], 5),
    ([2, 0, 0], [0], 5), ([1, 0, 0], [0, 0], 5), ([1, 0, 0], [0, 4], 5),
    ([1, 0, 0], [-1], 5), ([1, 0, 0], [True], 5), ([1, 0, 0], [0], True),
])
def test_invalid_query_vectors_or_scopes_never_query_chroma(retriever, vector, scope, limit):
    client, collection, _ = prepared(retriever)
    adapter = store.attach_chroma(retriever, "http://chroma:8000", client=client)
    with pytest.raises(RetrievalError):
        adapter.dense_candidates(vector, scope, limit)
    assert not collection.query_calls


def test_empty_scope_does_not_call_vector_store(retriever):
    client, collection, _ = prepared(retriever)
    adapter = store.attach_chroma(retriever, "http://chroma:8000", client=client)
    assert adapter.dense_candidates([1, 0, 0], [], 5) == []
    assert not collection.query_calls


@pytest.mark.parametrize("url", [
    "https://public.example.com", "http://public.example.com", "http://user:password@chroma:8000",
    "http://chroma:8000/path", "http://chroma:8000?key=secret", "http://chroma:8000#fragment",
    "file:///tmp/chroma", "http://chroma:not-a-port",
])
def test_runtime_chroma_url_cannot_target_external_services_or_carry_credentials(url):
    with pytest.raises(RetrievalError, match="local Chroma"):
        store.chroma_client(url)


def test_local_client_disables_telemetry_and_never_supplies_auth_headers(monkeypatch):
    import chromadb
    calls = []
    monkeypatch.setattr(chromadb, "HttpClient", lambda **kwargs: calls.append(kwargs) or object())
    store.chroma_client("http://chroma:8000")
    assert calls[0]["host"] == "chroma" and calls[0]["port"] == 8000 and calls[0]["ssl"] is False
    assert calls[0]["settings"].anonymized_telemetry is False
    assert "headers" not in calls[0]


def test_index_identity_changes_collection_name_without_overwriting_previous_index(retriever):
    client, collection, receipt = prepared(retriever)
    retriever.manifest["index_fingerprint"] = "f" * 64
    second = store.populate_chroma(retriever, "http://chroma:8000", client=client)
    assert second["collection"] != receipt["collection"]
    assert len(client.collections) == 2 and collection.count() == 5
