"""Hybrid retrieval: BM25 + dense, fused with Reciprocal Rank Fusion (DEC-003, plan s.5, W1.5).

RRF score of a chunk = sum over retrievers of 1 / (K + rank), rank starting at 1 (Cormack,
Clarke & Buettcher, SIGIR 2009; K = 60 as in that paper). It uses ranks only, because BM25
scores (about 0-10) and cosine scores (about 0-1) are not on the same scale. Each retriever
already applied the shared filters (retrieval/filters.py), so fused hits are eligible only.

The fused top-40 is what the reranker (DEC-005, DEC-062) re-sorts to the final top-6.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index, Hit
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder
from madhya_kanoon_saathi.retrieval.filters import IN_SCOPE_STATES

RRF_K = 60
POOL = 40  # candidates taken from each retriever and returned after fusion (DEC-021: rerank top-40)


@dataclass
class FusedHit:
    chunk_id: str
    score: float
    ranks: dict[str, int] = field(default_factory=dict)  # retriever name -> 1-based rank
    flags: list[str] = field(default_factory=list)


def rrf(lists: dict[str, Sequence[Hit]], k: int = RRF_K, limit: int = POOL) -> list[FusedHit]:
    """Fuse ranked lists by RRF; ties keep the order of first appearance (BM25 list first)."""
    fused: dict[str, FusedHit] = {}
    for name, hits in lists.items():
        for rank, h in enumerate(hits, start=1):
            f = fused.setdefault(h.chunk_id, FusedHit(h.chunk_id, 0.0, flags=list(h.flags)))
            f.score += 1.0 / (k + rank)
            f.ranks[name] = rank
    return sorted(fused.values(), key=lambda f: -f.score)[:limit]


class HybridRetriever:
    def __init__(self, bm25: Bm25Index, dense: DenseIndex, embedder: Embedder) -> None:
        if [m["chunk_id"] for m in bm25.meta] != [m["chunk_id"] for m in dense.meta]:
            raise ValueError("BM25 and dense indexes were built from different chunk sets")
        self.bm25 = bm25
        self.dense = dense
        self.embedder = embedder

    def search(
        self,
        query: str,
        k: int = POOL,
        on: date | None = None,
        states: frozenset[str] = IN_SCOPE_STATES,
    ) -> list[FusedHit]:
        day = on or date.today()
        lexical = self.bm25.search(query, k=POOL, on=day, states=states)
        vector = self.embedder.encode([query])[0]
        semantic = self.dense.search_vector(vector, k=POOL, on=day, states=states)
        return rrf({"bm25": lexical, "dense": semantic}, limit=k)
