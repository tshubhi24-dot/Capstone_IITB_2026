"""Scoped BM25, frozen learned vectors, reciprocal-rank fusion and reranking.

Only public filing evidence enters these local CPU models. Model and index
artifacts are prepared explicitly; a configured learned arm never falls back.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading

import numpy as np
from rank_bm25 import BM25Okapi


CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "retrieval_config.json"
MODES = {"bm25", "hybrid", "hybrid_rerank"}


class RetrievalError(ValueError):
    """A bounded, operator-actionable retrieval configuration failure."""


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def load_config(path=None):
    config = json.loads(Path(path or CONFIG_PATH).read_text())
    if config.get("version") != "hybrid-minilm-v1" or config.get("dimension") != 384:
        raise RetrievalError("Unsupported retrieval configuration.")
    return config


def document_text(row, table_aware=True):
    """Retrieval text includes canonical table cells; the cited passage stays exact."""
    text = str(row["text"])
    table = row.get("table")
    if table_aware and isinstance(table, list) and table:
        cells = [" | ".join(str(cell) for cell in values) for values in table if isinstance(values, list)]
        if cells:
            text += "\nTable cells:\n" + "\n".join(cells)
    return text


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def decompose_query(query, max_parts=3):
    """Keep the original and at most two literal subquestions; never invent facts."""
    original = " ".join(query.split())
    if not original or len(original) > 2000:
        raise RetrievalError("Search requires a nonempty query of at most 2000 characters.")
    parts = [original]
    if max_parts <= 1:
        return parts
    for part in re.split(r"\s+and\s+|\s*;\s*|\?\s+", original, flags=re.I):
        part = part.strip(" ?;,")
        if len(tokenize(part)) >= 2 and part.casefold() not in {value.casefold() for value in parts}:
            parts.append(part)
        if len(parts) >= max_parts:
            break
    return parts


def model_fingerprint(config):
    return canonical_hash({role: config[role] for role in ("encoder", "reranker")})


def verify_model_files(directory, specification):
    root = Path(directory).resolve()
    for name, expected in specification["files"].items():
        file = root / name
        # Model bundles contain data only and may not refer outside their root.
        if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(root):
            raise RetrievalError("A pinned local retrieval model file is missing or unsafe.")
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise RetrievalError("A pinned local retrieval model file failed its checksum.")


def _token_windows(text, tokenizer, budget, overlap):
    offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True,
                        truncation=False, verbose=False)["offset_mapping"]
    if not offsets:
        return [text or " "]
    if len(offsets) > 32768:
        raise RetrievalError("A retrieval document exceeds the bounded local token budget.")
    step = max(1, budget - overlap)
    return [text[offsets[start][0]:offsets[min(start + budget, len(offsets)) - 1][1]]
            for start in range(0, len(offsets), step)
            if start == 0 or start + overlap < len(offsets)]


class LocalModels:
    """Pinned safetensors models, CPU only, no Hub requests or remote code."""
    def __init__(self, root, config):
        from sentence_transformers import SentenceTransformer, CrossEncoder
        import torch
        self.root, self.config = Path(root), config
        for role in ("encoder", "reranker"):
            verify_model_files(self.root / role, config[role])
        torch.set_num_threads(max(1, min(int(os.getenv("RETRIEVAL_CPU_THREADS", "2")), 4)))
        kwargs = dict(device="cpu", local_files_only=True, trust_remote_code=False,
                      token=False, model_kwargs={"use_safetensors": True})
        self.encoder = SentenceTransformer(str(self.root / "encoder"), **kwargs)
        self.encoder.max_seq_length = config["encoder"]["max_length"]
        self.reranker = CrossEncoder(str(self.root / "reranker"),
                                    max_length=config["reranker"]["max_length"], **kwargs)
        self.lock = threading.Lock()

    def encode(self, texts):
        windows, owners = [], []
        for index, text in enumerate(texts):
            parts = _token_windows(text, self.encoder.tokenizer,
                                   self.config["encoder"]["max_length"] - 2, 32)
            windows.extend(parts)
            owners.extend([index] * len(parts))
        with self.lock:
            encoded = self.encoder.encode(windows, batch_size=32, show_progress_bar=False,
                                          normalize_embeddings=True, convert_to_numpy=True)
        pooled = np.zeros((len(texts), self.config["dimension"]), dtype=np.float32)
        counts = np.zeros(len(texts), dtype=np.int32)
        for owner, vector in zip(owners, encoded):
            pooled[owner] += vector
            counts[owner] += 1
        pooled /= counts[:, None]
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        if not np.isfinite(pooled).all() or np.any(norms <= 0):
            raise RetrievalError("The embedding model produced invalid vectors.")
        return np.asarray(pooled / norms, dtype=np.float32)

    def score(self, query, documents):
        tokens = self.reranker.tokenizer(query, add_special_tokens=False,
                                         truncation=True, max_length=96, verbose=False)["input_ids"]
        bounded_query = self.reranker.tokenizer.decode(tokens, skip_special_tokens=True)
        budget = self.config["reranker"]["max_length"] - len(tokens) - 3
        pairs, owners = [], []
        for index, document in enumerate(documents):
            windows = _token_windows(document, self.reranker.tokenizer, budget, 32)
            pairs.extend((bounded_query, text) for text in windows)
            owners.extend([index] * len(windows))
        with self.lock:
            values = self.reranker.predict(pairs, batch_size=16, show_progress_bar=False,
                                           convert_to_numpy=True)
        result = np.full(len(documents), -np.inf)
        for owner, value in zip(owners, values):
            result[owner] = max(result[owner], float(value))
        if not np.isfinite(result).all():
            raise RetrievalError("The reranker produced invalid relevance scores.")
        return result


def index_rows(rows, table_aware=True):
    return [{"id": row["id"], "ticker": row["ticker"], "year": int(row["year"]),
             "text_sha256": hashlib.sha256(document_text(row, table_aware).encode()).hexdigest()}
            for row in rows]


def write_index(output, corpus_fingerprint, rows, vectors, config):
    """Publish an immutable NumPy index and manifest after a complete build."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.shape != (len(rows), config["dimension"]) or not np.isfinite(vectors).all():
        raise RetrievalError("The generated retrieval index has invalid dimensions or values.")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1, atol=1e-4):
        raise RetrievalError("The generated retrieval index must contain normalized vectors.")
    target = output / "vectors.npy"
    with (output / "vectors.tmp").open("wb") as handle:
        np.save(handle, vectors, allow_pickle=False)
    (output / "vectors.tmp").replace(target)
    manifest = {"version": 1, "backend": "numpy_exact_cosine", "corpus_fingerprint": corpus_fingerprint,
                "configuration_hash": canonical_hash(config), "model_fingerprint": model_fingerprint(config),
                "passage_count": len(rows), "dimension": config["dimension"],
                "rows": index_rows(rows, config["table_aware"]),
                "vectors_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "encoder": {key: config["encoder"][key] for key in ("id", "revision")},
                "reranker": {key: config["reranker"][key] for key in ("id", "revision")},
                "text_policy": config["text_policy"], "query_policy": config["query_policy"]}
    manifest["index_fingerprint"] = canonical_hash(manifest)
    temporary = output / "manifest.tmp"
    temporary.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    temporary.replace(output / "manifest.json")
    return manifest


class HybridRetriever:
    def __init__(self, corpus, *, artifacts=None, models=None, config=None):
        self.corpus = corpus
        self.config = config or load_config()
        self.rows = sorted(corpus._passages.values(), key=lambda row: row["id"])
        self.texts = [document_text(row, self.config["table_aware"]) for row in self.rows]
        self.tokens = [tokenize(text) or ["empty"] for text in self.texts]
        self.artifacts = Path(artifacts or os.getenv("RETRIEVAL_ARTIFACTS", "/retrieval"))
        self._models = models
        self.vectors = None
        self.manifest = None
        self.lexical_cache = {}
        self.dense_backend = "numpy_exact_cosine"
        self._load_lock = threading.Lock()
        self._models_load_lock = threading.Lock()

    @property
    def models(self):
        if self._models is None:
            with self._models_load_lock:
                if self._models is None:
                    self._models = LocalModels(self.artifacts / "models", self.config)
        return self._models

    def load_index(self):
        with self._load_lock:
            if self.vectors is not None:
                return
            try:
                manifest = json.loads((self.artifacts / "manifest.json").read_text())
                recorded = manifest.pop("index_fingerprint")
                if canonical_hash(manifest) != recorded:
                    raise RetrievalError("The retrieval manifest fingerprint does not match.")
                manifest["index_fingerprint"] = recorded
                expected = index_rows(self.rows, self.config["table_aware"])
                if (manifest["corpus_fingerprint"] != self.corpus.fingerprint
                        or manifest["configuration_hash"] != canonical_hash(self.config)
                        or manifest["model_fingerprint"] != model_fingerprint(self.config)
                        or manifest["rows"] != expected or manifest["passage_count"] != len(self.rows)
                        or manifest["dimension"] != self.config["dimension"]):
                    raise RetrievalError("The retrieval artifacts are stale for this source or configuration.")
                vector_file = self.artifacts / "vectors.npy"
                if hashlib.sha256(vector_file.read_bytes()).hexdigest() != manifest["vectors_sha256"]:
                    raise RetrievalError("The retrieval vector checksum does not match.")
                vectors = np.load(vector_file, allow_pickle=False)
                if (vectors.shape != (len(self.rows), self.config["dimension"])
                        or vectors.dtype != np.float32 or not np.isfinite(vectors).all()
                        or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)):
                    raise RetrievalError("The stored retrieval vectors are invalid.")
                self.vectors, self.manifest = vectors, manifest
            except RetrievalError:
                raise
            except (OSError, ValueError, KeyError, TypeError) as error:
                raise RetrievalError("Prepared local retrieval artifacts are unavailable or invalid; rebuild them explicitly.") from error

    def dense_candidates(self, query_vector, scoped_indices, limit):
        """Replaceable dense backend; every caller supplies the allowed row subset."""
        values = self.vectors[scoped_indices] @ query_vector
        return [(scoped_indices[index], float(values[index])) for index in
                sorted(range(len(scoped_indices)), key=lambda index: (-values[index], self.rows[scoped_indices[index]]["id"]))[:limit]]

    def search(self, query, ticker, years, k=5, *, mode="hybrid_rerank"):
        if mode not in MODES:
            raise RetrievalError("Unknown retrieval mode.")
        if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= 10:
            raise RetrievalError("Search requires between one and ten results.")
        if not isinstance(years, list) or not 1 <= len(years) <= 3 or any(type(year) is not int for year in years):
            raise RetrievalError("Search requires one to three integer fiscal years.")
        if ticker not in {company["ticker"] for company in self.corpus.companies()} or not set(years) <= set(self.corpus.years(ticker)):
            raise RetrievalError("Search scope is outside the frozen company/year catalogue.")
        variants = decompose_query(query, self.config["max_query_parts"] if mode != "bm25" else 1)
        indices = [index for index, row in enumerate(self.rows) if row["ticker"] == ticker and int(row["year"]) in years]
        if not indices:
            return []
        scope_key = (ticker, tuple(sorted(set(years))))
        if scope_key not in self.lexical_cache:
            self.lexical_cache[scope_key] = BM25Okapi([self.tokens[index] for index in indices])
        lexical = self.lexical_cache[scope_key]
        fused, lexical_best, dense_best = defaultdict(float), {}, {}
        limit = self.config["candidates_per_channel"]
        query_vectors = None
        if mode != "bm25":
            self.load_index()
            query_vectors = self.models.encode(variants)
            if query_vectors.shape != (len(variants), self.config["dimension"]) or not np.isfinite(query_vectors).all():
                raise RetrievalError("The query encoder produced invalid vectors.")
        for variant_index, variant in enumerate(variants):
            scores = lexical.get_scores(tokenize(variant))
            ranked = sorted(range(len(indices)), key=lambda index: (-scores[index], self.rows[indices[index]]["id"]))
            if mode == "bm25":
                return [deepcopy({**self.rows[indices[index]], "retrieval_score": float(scores[index]),
                                  "retrieval": {"mode": mode, "backend": "bm25", "table_aware": self.config["table_aware"],
                                                "query_variants": variants, "configuration_hash": canonical_hash(self.config)}})
                        for index in ranked[:k]]
            for rank, local_index in enumerate(ranked[:limit], 1):
                index = indices[local_index]
                fused[index] += 1 / (self.config["rrf_k"] + rank)
                lexical_best[index] = max(lexical_best.get(index, -math.inf), float(scores[local_index]))
            candidates = self.dense_candidates(query_vectors[variant_index], indices, limit)
            # A remote index is never allowed to widen the caller's scope.
            if any(index not in indices or not math.isfinite(score) for index, score in candidates):
                raise RetrievalError("The dense backend returned evidence outside the allowed source scope.")
            for rank, (index, score) in enumerate(candidates, 1):
                fused[index] += 1 / (self.config["rrf_k"] + rank)
                dense_best[index] = max(dense_best.get(index, -math.inf), score)
        selected = sorted(fused, key=lambda index: (-fused[index], self.rows[index]["id"]))[:self.config["rerank_candidates"]]
        reranked = {}
        if mode == "hybrid_rerank":
            values = self.models.score(variants[0], [self.texts[index] for index in selected])
            if len(values) != len(selected) or not np.isfinite(values).all():
                raise RetrievalError("The reranker returned invalid candidate scores.")
            reranked = {index: float(value) for index, value in zip(selected, values)}
            selected.sort(key=lambda index: (-reranked[index], -fused[index], self.rows[index]["id"]))
        return [deepcopy({**self.rows[index], "retrieval_score": reranked.get(index, fused[index]),
                          "retrieval": {"mode": mode, "backend": self.dense_backend, "table_aware": self.config["table_aware"],
                                        "configuration_hash": canonical_hash(self.config),
                                        "index_fingerprint": self.manifest["index_fingerprint"],
                                        "model_fingerprint": self.manifest["model_fingerprint"],
                                        "query_variants": variants, "rrf_score": fused[index],
                                        "bm25_score": lexical_best.get(index), "dense_score": dense_best.get(index),
                                        "rerank_score": reranked.get(index), "scoped_passages": len(indices),
                                        "rerank_candidate_count": len(selected) if reranked else 0}})
                for index in selected[:k]]
