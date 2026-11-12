"""Exact dense search with FAISS ``IndexFlatIP`` (DEC-025, DEC-060).

Vectors are L2-normalised before they are added and before querying, so inner product = cosine.
No approximate index (HNSW/IVF) without a new decision (.claude/rules/retrieval.md).
Chunk metadata is the same per-chunk record the BM25 index keeps, and the same filters
(retrieval/filters.py) run after scoring.

Files written by ``save`` (git-ignored ``data/index/dense-<variant>/``): ``vectors.faiss`` and
``chunks.jsonl`` (chunk_id + filter metadata, in index order).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from madhya_kanoon_saathi.retrieval.bm25_index import META_FIELDS, Hit
from madhya_kanoon_saathi.retrieval.filters import IN_SCOPE_STATES, eligible, flags


def l2_normalise(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    out: np.ndarray = x / np.maximum(norms, 1e-12)
    return out


class DenseIndex:
    def __init__(self, index: faiss.Index, meta: list[dict[str, Any]]) -> None:
        self.index = index
        self.meta = meta

    @classmethod
    def build(cls, vectors: np.ndarray, chunks: Sequence[Mapping[str, Any]]) -> DenseIndex:
        if len(vectors) != len(chunks):
            raise ValueError(f"{len(vectors)} vectors for {len(chunks)} chunks")
        v = l2_normalise(vectors)
        index = faiss.IndexFlatIP(v.shape[1])
        index.add(v)
        return cls(index, [{k: c.get(k) for k in META_FIELDS} for c in chunks])

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(folder / "vectors.faiss"))
        with (folder / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as f:
            for m in self.meta:
                f.write(json.dumps(m, ensure_ascii=False, sort_keys=True) + "\n")

    @classmethod
    def load(cls, folder: Path) -> DenseIndex:
        index = faiss.read_index(str(folder / "vectors.faiss"))
        meta = [
            json.loads(x)
            for x in (folder / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        return cls(index, meta)

    def search_vector(
        self,
        query: np.ndarray,
        k: int = 40,
        on: date | None = None,
        states: frozenset[str] = IN_SCOPE_STATES,
    ) -> list[Hit]:
        """Exact top-k by cosine among eligible chunks (searches all, then filters)."""
        day = on or date.today()
        q = l2_normalise(np.asarray(query, dtype=np.float32).reshape(1, -1))
        scores, ids = self.index.search(q, self.index.ntotal)
        hits: list[Hit] = []
        for s, i in zip(scores[0], ids[0], strict=True):
            if i < 0 or len(hits) >= k:
                break
            m = self.meta[int(i)]
            if eligible(m, day, states):
                hits.append(Hit(m["chunk_id"], float(s), flags(m)))
        return hits
