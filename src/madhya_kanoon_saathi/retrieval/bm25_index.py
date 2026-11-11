"""BM25 keyword index over chunks (DEC-003, DEC-026, DEC-058).

Indexed tokens per chunk = tokenize(text) + provision_tokens(section_uid) + tokenize(heading);
the query goes through the same tokenize(). Okapi BM25 (bm25s "lucene" variant), k1=1.5, b=0.75.
Filters (retrieval/filters.py) are applied after scoring, so they never change the scores.

Files written by ``save`` (git-ignored ``data/index/bm25/``): the bm25s index files plus
``chunks.jsonl`` with each chunk_id and the metadata the filters need, in index order.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import bm25s
import numpy as np

from madhya_kanoon_saathi.retrieval.filters import IN_SCOPE_STATES, eligible, flags
from madhya_kanoon_saathi.retrieval.tokenizer import provision_tokens, tokenize

K1, B = 1.5, 0.75
META_FIELDS = (
    "chunk_id",
    "doc_id",
    "jurisdiction",
    "lang",
    "status",
    "applies_to",
    "valid_from",
    "valid_to",
    "expires_on",
)


_CLAUSE_START = re.compile(r"^\[?\(([a-z]{1,4})\)\s")


def contained_tokens(chunk: Mapping[str, Any]) -> list[str]:
    """Reference tokens of clauses that start a paragraph inside the chunk.

    A sub-section chunk such as IN.RTI2005:s8:ss1 holds clauses (a)-(j) in its text; its own uid
    only gives s8, s8_1. Adding s8_1_a ... s8_1_j lets "धारा 8(1)(j)" match it (derived at index
    time from the canonical text, no extra chunk field).
    """
    own = provision_tokens(chunk["section_uid"])
    if not own:
        return []
    return [
        f"{own[-1]}_{m.group(1)}"
        for line in chunk["text"].split("\n")
        if (m := _CLAUSE_START.match(line))
    ]


def chunk_tokens(chunk: Mapping[str, Any]) -> list[str]:
    return (
        tokenize(chunk["text"])
        + provision_tokens(chunk["section_uid"])
        + contained_tokens(chunk)
        + tokenize(chunk.get("heading", ""))
    )


@dataclass
class Hit:
    chunk_id: str
    score: float
    flags: list[str] = field(default_factory=list)


class Bm25Index:
    def __init__(self, retriever: bm25s.BM25, meta: list[dict[str, Any]]) -> None:
        self.retriever = retriever
        self.meta = meta

    @classmethod
    def build(cls, chunks: Iterable[Mapping[str, Any]]) -> Bm25Index:
        chunks = list(chunks)
        retriever = bm25s.BM25(k1=K1, b=B, method="lucene")
        retriever.index([chunk_tokens(c) for c in chunks], show_progress=False)
        meta = [{k: c.get(k) for k in META_FIELDS} for c in chunks]
        return cls(retriever, meta)

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        self.retriever.save(str(folder), show_progress=False)
        with (folder / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as f:
            for m in self.meta:
                f.write(json.dumps(m, ensure_ascii=False, sort_keys=True) + "\n")

    @classmethod
    def load(cls, folder: Path) -> Bm25Index:
        retriever = bm25s.BM25.load(str(folder), show_progress=False)
        meta = [
            json.loads(x)
            for x in (folder / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        return cls(retriever, meta)

    @property
    def vocab_size(self) -> int:
        return len(self.retriever.vocab_dict)

    def scores(self, query: str) -> np.ndarray:
        toks = tokenize(query)
        if not toks:
            return np.zeros(len(self.meta), dtype=np.float32)
        return np.asarray(self.retriever.get_scores(toks), dtype=np.float32)

    def search(
        self,
        query: str,
        k: int = 40,
        on: date | None = None,
        states: frozenset[str] = IN_SCOPE_STATES,
    ) -> list[Hit]:
        """Top-k eligible chunks by BM25 score; zero-score chunks are never returned."""
        day = on or date.today()
        s = self.scores(query)
        hits: list[Hit] = []
        for i in np.argsort(-s, kind="stable"):
            if s[i] <= 0 or len(hits) >= k:
                break
            m = self.meta[int(i)]
            if eligible(m, day, states):
                hits.append(Hit(m["chunk_id"], float(s[i]), flags(m)))
        return hits
