"""Hybrid retrieval: BM25 + dense, fused with Reciprocal Rank Fusion (DEC-003, plan s.5, W1.5).

RRF score of a chunk = sum over retrievers of 1 / (K + rank), rank starting at 1 (Cormack,
Clarke & Buettcher, SIGIR 2009; K = 60 as in that paper). It uses ranks only, because BM25
scores (about 0-10) and cosine scores (about 0-1) are not on the same scale. Each retriever
already applied the shared filters (retrieval/filters.py), so fused hits are eligible only.

The fused top-40 is what the reranker (DEC-005, DEC-062) re-sorts to the final top-6
(``search_reranked``); ``rerank_pool=20`` is the DEC-021 latency fallback.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index, Hit
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder, embed_text
from madhya_kanoon_saathi.retrieval.filters import IN_SCOPE_STATES, NOT_IN_FORCE
from madhya_kanoon_saathi.retrieval.reranker import Reranker

RRF_K = 60
POOL = 40  # candidates taken from each retriever and returned after fusion (DEC-021: rerank top-40)
FINAL = 6  # passages kept after reranking (DEC-005)


@dataclass
class FusedHit:
    chunk_id: str
    score: float
    ranks: dict[str, int] = field(default_factory=dict)  # retriever name -> 1-based rank
    flags: list[str] = field(default_factory=list)
    rerank_score: float | None = None  # cross-encoder logit, set by search_reranked


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
    def __init__(
        self,
        bm25: Bm25Index,
        dense: DenseIndex,
        embedder: Embedder,
        reranker: Reranker | None = None,
        passages: Mapping[str, str] | None = None,
    ) -> None:
        """``passages``: chunk_id -> text the reranker reads (``embed_text`` form, DEC-061)."""
        if [m["chunk_id"] for m in bm25.meta] != [m["chunk_id"] for m in dense.meta]:
            raise ValueError("BM25 and dense indexes were built from different chunk sets")
        if reranker is not None and passages is None:
            raise ValueError("a reranker needs the passage texts")
        self.bm25 = bm25
        self.dense = dense
        self.embedder = embedder
        self.reranker = reranker
        self.passages = passages or {}

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

    def search_reranked(
        self,
        query: str,
        k: int = FINAL,
        rerank_pool: int = POOL,
        on: date | None = None,
        states: frozenset[str] = IN_SCOPE_STATES,
    ) -> list[FusedHit]:
        """RRF top-``rerank_pool`` re-sorted by the cross-encoder; best ``k`` returned."""
        if self.reranker is None:
            raise RuntimeError("no reranker loaded")
        return rerank_hits(
            self.reranker, query, self.search(query, rerank_pool, on, states), self.passages, k
        )


def rerank_hits(
    reranker: Reranker, query: str, hits: Sequence[FusedHit], passages: Mapping[str, str], k: int
) -> list[FusedHit]:
    """Cross-encoder order, then in-force law before not-in-force text (DEC-067); best ``k``."""
    by_id = {h.chunk_id: h for h in hits}
    missing = [h.chunk_id for h in hits if h.chunk_id not in passages]
    if missing:
        raise KeyError(f"no passage text for {missing[:3]}")
    scored = reranker.rerank(
        query, [(h.chunk_id, passages[h.chunk_id]) for h in hits], top=len(hits)
    )
    out = []
    for cid, score in scored:
        by_id[cid].rerank_score = score
        out.append(by_id[cid])
    return in_force_first(out)[:k]


def in_force_first(hits: Sequence[FusedHit]) -> list[FusedHit]:
    """Stable partition: hits without a not-in-force flag keep their order and come first."""
    later = [h for h in hits if NOT_IN_FORCE.intersection(h.flags)]
    return [h for h in hits if not NOT_IN_FORCE.intersection(h.flags)] + later


def passages_from_chunks(
    chunks: Sequence[Mapping[str, Any]], titles: Mapping[str, tuple[str | None, str | None]]
) -> dict[str, str]:
    """chunk_id -> reranker input: the same title / heading path / text the embedder reads."""
    return {c["chunk_id"]: embed_text(c, titles) for c in chunks}
