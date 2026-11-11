"""Hybrid retrieval — BM25 + Chroma vectors + RRF + cross-encoder reranker.

Pipeline for one query:
  1. BM25 search over all passage texts          (keyword matching)
  2. Chroma vector search with local embeddings  (semantic matching)
  3. Reciprocal Rank Fusion to merge both lists  (no weight tuning needed)
  4. Cross-encoder reranker on top-k results     (precise relevance scoring)

Why each step:
  BM25   — catches exact terminology (e.g. "goodwill impairment", "CIK")
  Chroma — catches semantic similarity even when wording differs
  RRF    — combines without needing to tune score scales
  Rerank — cross-encoder sees query + passage together, much more accurate
           but too slow to run on all passages, so only on top-k after RRF

Each step can be switched off (mode, rerank) so the evaluation can measure
what it adds: see scripts/run.py retrieval.
"""

from __future__ import annotations

from analystdesk.paths import RUNTIME_ROOT

import hashlib
import re
import threading

INDEX_DIR = RUNTIME_ROOT / "index"

_retriever = None


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens; punctuation dropped so "revenue," matches "revenue"."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _rrf(bm25_hits: list[str], vec_hits: list[str], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion — merge two ranked lists into one.

    RRF score = sum of 1/(k + rank) across lists.
    k=60 is the standard default (Cormack, Clarke & Buettcher 2009).
    Returns passage_ids sorted by descending RRF score.
    """
    scores: dict[str, float] = {}
    for rank, pid in enumerate(bm25_hits, 1):
        scores[pid] = scores.get(pid, 0) + 1 / (k + rank)
    for rank, pid in enumerate(vec_hits, 1):
        scores[pid] = scores.get(pid, 0) + 1 / (k + rank)
    return sorted(scores, key=lambda p: scores[p], reverse=True)


def _collection_name(passages: list[dict], prefix: str) -> str:
    """Name the Chroma collection after the passages it holds.

    Re-ingesting changes the passages, so it gets a fresh collection instead
    of silently reusing embeddings of the old ones.
    """
    digest = hashlib.sha1()
    for p in passages:
        digest.update(p["passage_id"].encode())
        digest.update(str(len(p["text"])).encode())
    return f"{prefix}_{digest.hexdigest()[:12]}"


class HybridRetriever:
    def __init__(self, passages: list[dict], collection_prefix: str = "analyst_desk"):
        from rank_bm25 import BM25Okapi
        import chromadb
        from sentence_transformers import SentenceTransformer, CrossEncoder

        self._bm25_class = BM25Okapi
        self.base_passages = passages
        self._planted: list[dict] = []
        self._index_keyword(passages)

        # Chroma vector store with local MiniLM embeddings (no API cost)
        print("  Loading embedding model (first run downloads ~90MB)...")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        client = chromadb.PersistentClient(path=str(INDEX_DIR))
        self.collection = client.get_or_create_collection(
            _collection_name(passages, collection_prefix)
        )

        if self.collection.count() != len(passages):
            print(f"  Embedding {len(passages)} passages (first run only)...")
            batch = 64
            for i in range(0, len(passages), batch):
                batch_p = passages[i:i+batch]
                embeddings = self.embedder.encode(
                    [p["text"] for p in batch_p], show_progress_bar=False
                ).tolist()
                self.collection.upsert(
                    ids=[p["passage_id"] for p in batch_p],
                    embeddings=embeddings,
                    documents=[p["text"] for p in batch_p],
                    metadatas=[{
                        "company": p["company"],
                        "fiscal_year": str(p["fiscal_year"]),
                        "item": p["item"],
                    } for p in batch_p],
                )
            print(f"  ✓ Index built: {len(passages)} passages")

    def _index_keyword(self, passages: list[dict]) -> None:
        self.passages = passages
        self.pid_to_passage = {p["passage_id"]: p for p in passages}
        self.pids = [p["passage_id"] for p in passages]
        # BM25 over tokenised passage texts
        self.bm25 = self._bm25_class([_tokenize(p["text"]) for p in passages])

    def plant(self, planted: list[dict]) -> None:
        """Red-team runs only: add planted passages (attack text) to the data path.

        They join BM25 and passage lookup, then compete in the reranker like any
        filing passage. The vector index on disk is never changed, so an
        experiment cannot leave attack text behind. plant([]) removes them.
        """
        if planted == self._planted:
            return
        self._planted = list(planted)
        self._index_keyword(self.base_passages + self._planted)

    def _matches(self, passage: dict, company: str | None, year: int | None,
                 item: str | None = None) -> bool:
        return ((not company or passage["company"] == company)
                and (not year or passage["fiscal_year"] == year)
                and (not item or passage["item"] == item))

    def _bm25_search(self, query: str, n: int, company, year, item=None) -> list[str]:
        scores = self.bm25.get_scores(_tokenize(query))
        # Filter before taking the top n, so a company/year filter still gets
        # n candidates instead of whatever survives of the global top n
        allowed = [
            i for i, p in enumerate(self.passages) if self._matches(p, company, year, item)
        ]
        ranked = sorted(allowed, key=lambda i: scores[i], reverse=True)[:n]
        return [self.pids[i] for i in ranked]

    def _vector_search(self, query: str, n: int, company, year, item=None) -> list[str]:
        q_emb = self.embedder.encode([query], show_progress_bar=False).tolist()
        # Chroma requires $and when combining multiple filter keys
        filters = []
        if company:
            filters.append({"company": {"$eq": company}})
        if year:
            filters.append({"fiscal_year": {"$eq": str(year)}})
        if item:
            filters.append({"item": {"$eq": item}})
        if len(filters) == 1:
            where = filters[0]
        elif len(filters) > 1:
            where = {"$and": filters}
        else:
            where = None
        results = self.collection.query(query_embeddings=q_emb, n_results=n, where=where)
        return results["ids"][0] if results["ids"] else []

    def search(self, query: str, top_k: int = 5,
               company: str | None = None,
               year: int | None = None,
               item: str | None = None,
               mode: str = "hybrid",
               rerank: bool = True) -> list[dict]:
        """Return top_k passages for query.

        mode:   "bm25", "vector" or "hybrid" (both, merged with RRF)
        rerank: re-score the candidates with the cross-encoder
        Optional filters narrow the search to a company, year and/or item
        ("item1a" risk factors, "item7" MD&A).
        """
        n_candidates = min(50, len(self.passages))

        if mode == "bm25":
            ranked = self._bm25_search(query, n_candidates, company, year, item)
        elif mode == "vector":
            ranked = self._vector_search(query, n_candidates, company, year, item)
        elif mode == "hybrid":
            ranked = _rrf(
                self._bm25_search(query, n_candidates, company, year, item),
                self._vector_search(query, n_candidates, company, year, item),
            )
        else:
            raise ValueError(f"Unknown retrieval mode: {mode!r}")

        candidates = [
            self.pid_to_passage[pid] for pid in ranked[:n_candidates]
            if pid in self.pid_to_passage
        ]
        if not candidates:
            return []

        if not rerank:
            return [{**p, "score": 1 / (i + 1)} for i, p in enumerate(candidates[:top_k])]

        # Cross-encoder reranker — scores query+passage jointly
        pairs = [(query, c["text"]) for c in candidates]
        rerank_scores = self.reranker.predict(pairs, show_progress_bar=False)
        ranked_pairs = sorted(
            zip(candidates, rerank_scores), key=lambda x: x[1], reverse=True
        )
        return [{**p, "score": float(s)} for p, s in ranked_pairs[:top_k]]


_build_lock = threading.Lock()


def get_retriever(passages: list[dict] | None = None) -> HybridRetriever:
    """Return a cached HybridRetriever. Builds the index on first call.

    Locked: parallel first searches (C1 can issue several tool calls at once) must not
    open the vector store twice, which fails inside Chroma.
    """
    global _retriever
    if _retriever is not None:
        return _retriever
    with _build_lock:
        return _build(passages)


def _build(passages: list[dict] | None) -> HybridRetriever:
    global _retriever
    if _retriever is None:
        if passages is None:
            from analystdesk.retrieval.ingest import load_passages
            passages = load_passages()
        if not passages:
            raise RuntimeError(
                "No passages found. Run ingest first: "
                "python -c \"from analystdesk.ingest import ingest_all; ingest_all()\""
            )
        print(f"Building retriever over {len(passages)} passages...")
        _retriever = HybridRetriever(passages)
        from analystdesk.evaluation.redteam import planted_passages
        _retriever.plant(planted_passages())   # none, except in red-team runs and demos
    return _retriever


def reset_retriever():
    """Force rebuild on next call (useful after re-ingestion)."""
    global _retriever
    _retriever = None
