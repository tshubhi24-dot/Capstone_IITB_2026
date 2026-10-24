"""Chroma adapter for validated, precomputed public filing vectors.

The application can read an explicitly populated collection. It cannot create
one, download models or ask Chroma to embed text. Exact issuer/year/ID filters
apply before vector ranking and returned IDs are checked again afterwards.
"""
import math
import re
from urllib.parse import urlsplit

import numpy as np

from desk.retrieval import RetrievalError, canonical_hash

PAGE_SIZE = 256
FINGERPRINT_FIELDS = ("index_fingerprint", "corpus_fingerprint", "configuration_hash",
                      "model_fingerprint", "vectors_sha256")


def chroma_client(url):
    """Connect only to the local stack; never allow credentials or public hosts."""
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname not in {"chroma", "localhost", "127.0.0.1", "::1"}
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError("Invalid local vector-store URL")
        port = parsed.port or 8000
        if not 1 <= port <= 65535:
            raise ValueError("Invalid local vector-store port")
        import chromadb
        from chromadb.config import Settings
        return chromadb.HttpClient(host=parsed.hostname, port=port, ssl=False,
                                   settings=Settings(anonymized_telemetry=False, allow_reset=False))
    except Exception as error:
        raise RetrievalError("The configured local Chroma service is unavailable or invalid.") from error


def _expected(retriever):
    retriever.load_index()
    manifest = retriever.manifest
    if (any(not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get(field, ""))) for field in FINGERPRINT_FIELDS)
            or manifest.get("passage_count") != len(retriever.rows)
            or manifest.get("dimension") != retriever.vectors.shape[1]
            or len(manifest.get("rows", [])) != len(retriever.rows)):
        raise RetrievalError("The validated vector manifest is incomplete.")
    metadata = {field: manifest[field] for field in FINGERPRINT_FIELDS}
    metadata.update({"passage_count": len(retriever.rows), "dimension": manifest["dimension"],
                     "hnsw:space": "cosine", "analyst_desk_vector_version": 1})
    identity = {field: manifest[field] for field in ("index_fingerprint", "corpus_fingerprint", "configuration_hash")}
    name = "analyst-" + canonical_hash(identity)[:40]
    by_id = {row["id"]: index for index, row in enumerate(retriever.rows)}
    if len(by_id) != len(retriever.rows):
        raise RetrievalError("Canonical passage identifiers must be unique.")
    return name, metadata, by_id


def _row_metadata(retriever, index):
    row, indexed = retriever.rows[index], retriever.manifest["rows"][index]
    if indexed["id"] != row["id"]:
        raise RetrievalError("Vector manifest passage order differs from the source.")
    return {"ticker": row["ticker"], "year": int(row["year"]), "passage_id": row["id"],
            "text_sha256": indexed["text_sha256"], "index_fingerprint": retriever.manifest["index_fingerprint"]}


def validate_collection(retriever, collection):
    """Check collection identity, every canonical ID, metadata and stored vector."""
    name, expected, by_id = _expected(retriever)
    if getattr(collection, "name", None) != name:
        raise RetrievalError("Chroma collection name does not match the frozen index.")
    metadata = getattr(collection, "metadata", None)
    if not isinstance(metadata, dict) or any(metadata.get(key) != value for key, value in expected.items()):
        raise RetrievalError("Chroma collection fingerprint or cosine configuration differs.")
    if collection.count() != len(by_id):
        raise RetrievalError("Chroma collection passage count differs from the frozen index.")
    seen = set()
    for offset in range(0, len(by_id), PAGE_SIZE):
        result = collection.get(limit=PAGE_SIZE, offset=offset, include=["metadatas", "embeddings"])
        if not isinstance(result, dict):
            raise RetrievalError("Chroma returned invalid collection records.")
        ids, metadatas, embeddings = result.get("ids"), result.get("metadatas"), result.get("embeddings")
        required_count = min(PAGE_SIZE, len(by_id) - offset)
        if (not isinstance(ids, list) or len(ids) != required_count or not isinstance(metadatas, list)
                or len(metadatas) != len(ids) or embeddings is None or len(embeddings) != len(ids)):
            raise RetrievalError("Chroma collection page is incomplete.")
        for identifier, row_metadata, vector in zip(ids, metadatas, embeddings):
            if not isinstance(identifier, str) or identifier not in by_id or identifier in seen:
                raise RetrievalError("Chroma contains missing, duplicate or unknown passage identifiers.")
            index = by_id[identifier]
            if not isinstance(row_metadata, dict) or row_metadata != _row_metadata(retriever, index):
                raise RetrievalError("Chroma passage metadata differs from the frozen source.")
            vector = np.asarray(vector, dtype=np.float32)
            if vector.shape != retriever.vectors[index].shape or not np.array_equal(vector, retriever.vectors[index]):
                raise RetrievalError("Chroma stored vectors differ from the prepared vector artifact.")
            seen.add(identifier)
    if seen != set(by_id):
        raise RetrievalError("Chroma does not contain every canonical passage identifier.")
    return name


class ChromaDenseAdapter:
    def __init__(self, retriever, collection):
        self.retriever = retriever
        self.collection = collection
        self.collection_name = validate_collection(retriever, collection)
        self.by_id = {row["id"]: index for index, row in enumerate(retriever.rows)}

    def dense_candidates(self, query_vector, scoped_indices, limit):
        try:
            return self._dense_candidates(query_vector, scoped_indices, limit)
        except RetrievalError:
            raise
        except Exception as error:
            raise RetrievalError("The scoped Chroma query failed validation or could not complete.") from error

    def _dense_candidates(self, query_vector, scoped_indices, limit):
        vector = np.asarray(query_vector, dtype=np.float32)
        if (vector.shape != (self.retriever.manifest["dimension"],) or not np.isfinite(vector).all()
                or not np.isclose(np.linalg.norm(vector), 1, atol=1e-4)):
            raise RetrievalError("Chroma requires a normalized finite query vector of the frozen dimension.")
        if (type(limit) is not int or not 1 <= limit <= 100 or not isinstance(scoped_indices, list)
                or len(set(scoped_indices)) != len(scoped_indices)
                or any(type(index) is not int or not 0 <= index < len(self.retriever.rows) for index in scoped_indices)):
            raise RetrievalError("Chroma query candidate scope or limit is invalid.")
        if not scoped_indices:
            return []
        rows = [self.retriever.rows[index] for index in scoped_indices]
        tickers = {row["ticker"] for row in rows}
        years = sorted({int(row["year"]) for row in rows})
        if len(tickers) != 1 or not 1 <= len(years) <= 3:
            raise RetrievalError("Chroma query requires one issuer and one to three fiscal years.")
        allowed = {row["id"] for row in rows}
        where = {"$and": [
            {"ticker": {"$eq": next(iter(tickers))}}, {"year": {"$in": years}},
            {"passage_id": {"$in": sorted(allowed)}},
        ]}
        count = min(limit, len(allowed))
        result = self.collection.query(query_embeddings=[vector.tolist()], n_results=count,
                                       where=where, include=["distances", "metadatas"])
        if not isinstance(result, dict):
            raise RetrievalError("Chroma returned invalid query records.")
        groups = [result.get(key) for key in ("ids", "distances", "metadatas")]
        if any(not isinstance(group, list) or len(group) != 1 or not isinstance(group[0], list)
               or len(group[0]) != count for group in groups):
            raise RetrievalError("Chroma query returned incomplete candidate records.")
        identifiers, distances, metadatas = [group[0] for group in groups]
        seen, candidates = set(), []
        for identifier, distance, row_metadata in zip(identifiers, distances, metadatas):
            if (not isinstance(identifier, str) or identifier not in allowed or identifier not in self.by_id
                    or identifier in seen):
                raise RetrievalError("Chroma query returned unknown, duplicate or out-of-scope evidence.")
            index = self.by_id[identifier]
            if not isinstance(row_metadata, dict) or row_metadata != _row_metadata(self.retriever, index):
                raise RetrievalError("Chroma query result scope metadata differs from the frozen source.")
            if (isinstance(distance, bool) or not isinstance(distance, (int, float)) or not math.isfinite(distance)
                    or not -1e-5 <= distance <= 2 + 1e-5):
                raise RetrievalError("Chroma returned an invalid cosine distance.")
            score = float(self.retriever.vectors[index] @ vector)
            if not math.isclose(1. - float(distance), score, abs_tol=1e-4, rel_tol=0):
                raise RetrievalError("Chroma cosine score differs from the prepared evidence vector.")
            candidates.append((index, min(1., max(-1., score))))
            seen.add(identifier)
        return sorted(candidates, key=lambda pair: (-pair[1], self.retriever.rows[pair[0]]["id"]))


def attach_chroma(retriever, url, *, client=None):
    """Attach a pre-existing validated collection; never create one at query time."""
    try:
        name, _, _ = _expected(retriever)
        client = client if client is not None else chroma_client(url)
        collection = client.get_collection(name=name, embedding_function=None)
        adapter = ChromaDenseAdapter(retriever, collection)
    except RetrievalError:
        raise
    except Exception as error:
        raise RetrievalError("The frozen Chroma collection is unavailable; populate it explicitly before research.") from error
    retriever.dense_candidates = adapter.dense_candidates
    retriever.dense_backend = "chroma_cosine"
    return adapter


def populate_chroma(retriever, url, *, client=None):
    """Operator-only population of precomputed vectors; existing data is immutable."""
    name, metadata, by_id = _expected(retriever)
    client = client if client is not None else chroma_client(url)
    from chromadb.errors import NotFoundError
    try:
        collection = client.get_collection(name=name, embedding_function=None)
    except NotFoundError:
        collection = None
    except Exception as error:
        raise RetrievalError("The local vector store could not be inspected safely.") from error
    status = "reused"
    if collection is None:
        status = "populated"
        try:
            collection = client.create_collection(name=name, metadata=metadata, embedding_function=None)
            for offset in range(0, len(by_id), PAGE_SIZE):
                indices = list(range(offset, min(offset + PAGE_SIZE, len(by_id))))
                collection.add(ids=[retriever.rows[index]["id"] for index in indices],
                               embeddings=retriever.vectors[indices].tolist(),
                               metadatas=[_row_metadata(retriever, index) for index in indices])
        except Exception as error:
            raise RetrievalError("Vector population did not complete; an operator must inspect the collection before retrying.") from error
    validate_collection(retriever, collection)
    return {"status": status, "backend": "chroma_cosine", "collection": name,
            **{field: metadata[field] for field in FINGERPRINT_FIELDS},
            "passage_count": len(by_id), "dimension": metadata["dimension"],
            "stored_vector_verification": "all_float32_vectors_match_prepared_artifact",
            "scope_filter": "issuer_and_fiscal_year_and_allowed_canonical_passage_ids_before_ranking",
            "local_embedding_calls": 0, "generative_model_calls": 0, "external_provider_requests": 0}
