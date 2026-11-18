"""Local runtime: loads chunks, manifest, indexes, embedder, reranker and the safety indexes,
and turns retrieval hits into :class:`~madhya_kanoon_saathi.generation.pipeline.Retrieved`.

Used by ``scripts/ask.py`` (local CLI) and later by the answer Lambda (W3.1). Retrieval follows
DEC-068: BM25 + dense (int8) fused by RRF into a pool of 40, reranked by the int8 cross-encoder,
in-force law first (DEC-067), top 6 to the generator. The query vector is computed once and reused
by the crisis router and the dispute detector (DEC-074/076).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from madhya_kanoon_saathi.generation.crisis import ExampleIndex, build_examples
from madhya_kanoon_saathi.generation.dispute import MERITS
from madhya_kanoon_saathi.generation.pipeline import Retrieved
from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder
from madhya_kanoon_saathi.retrieval.hybrid import passages_from_chunks, rerank_hits, rrf
from madhya_kanoon_saathi.retrieval.reranker import Reranker

DATA = Path("data")
POOL, FINAL = 40, 6


@dataclass
class LocalRuntime:
    chunks: dict[str, dict[str, Any]]
    manifest: dict[str, Any]
    bm25: Bm25Index
    dense: DenseIndex
    embedder: Embedder
    reranker: Reranker
    passages: dict[str, str]
    crisis_index: ExampleIndex
    dispute_index: ExampleIndex

    @classmethod
    def load(cls, data: Path = DATA) -> LocalRuntime:
        chunks = {
            c["chunk_id"]: c
            for c in (
                json.loads(x)
                for x in (data / "parsed/chunks.jsonl").read_text("utf-8").splitlines()
            )
        }
        manifest = json.loads((data / "corpus_manifest.json").read_text("utf-8"))
        titles = {
            i["instrument_id"]: (i.get("title_en"), i.get("title_hi"))
            for i in manifest["instruments"]
        }
        embedder = Embedder.load("int8")
        safety = data / "safety"
        cex = json.loads((safety / "crisis_examples.json").read_text("utf-8"))
        dex = json.loads((safety / "dispute_examples.json").read_text("utf-8"))
        ct = json.loads((safety / "crisis_threshold.json").read_text("utf-8"))["threshold"]
        dt = json.loads((safety / "dispute_threshold.json").read_text("utf-8"))["threshold"]
        return cls(
            chunks=chunks,
            manifest=manifest,
            bm25=Bm25Index.load(data / "index/bm25"),
            dense=DenseIndex.load(data / "index/dense-int8"),
            embedder=embedder,
            reranker=Reranker.load("int8"),
            passages=passages_from_chunks(list(chunks.values()), titles),
            crisis_index=build_examples(cex["examples"], embedder.encode, ct, cex["ordinary"]),
            dispute_index=build_examples(
                dex["examples"], embedder.encode, dt, dex["ordinary"], categories=[MERITS]
            ),
        )

    def vector(self, question: str) -> np.ndarray:
        return np.asarray(self.embedder.encode([question])[0])

    def retrieve(self, question: str, vec: np.ndarray, on: date) -> list[Retrieved]:
        lex = self.bm25.search(question, k=POOL, on=on)
        sem = self.dense.search_vector(vec, k=POOL, on=on)
        hits = rerank_hits(
            self.reranker, question, rrf({"bm25": lex, "dense": sem}), self.passages, FINAL
        )
        # the reranker logit rides along for abstention-threshold analysis (eval); not used yet
        return [self._as_retrieved(self.chunks[h.chunk_id], h.rerank_score) for h in hits]

    def versions(self, section_uid: str) -> list[Retrieved]:
        """Every language version of one provision (e.g. RTI Rules r.14 in English and Hindi)."""
        return [
            self._as_retrieved(c) for c in self.chunks.values() if c["section_uid"] == section_uid
        ]

    def _as_retrieved(self, c: dict[str, Any], rerank: float | None = None) -> Retrieved:
        pages = c.get("locator", {}).get("pages")
        doc: dict[str, Any] = next(
            (d for d in self.manifest["documents"] if d["doc_id"] == c["doc_id"]), {}
        )
        extra: dict[str, str] = {}
        # wage answers (DEC-050): number, issuing authority and validity from the manifest document
        for key in ("notification_no", "publisher", "valid_from", "valid_to"):
            if doc.get(key):
                extra[key] = str(doc[key])
        # when the official copy was last checked: the latest confirmed verification, else fetch
        confirmed = [
            v["on"] for v in doc.get("verifications", []) if v.get("result") == "confirmed"
        ]
        checked = max(confirmed) if confirmed else str(doc.get("fetched_at", ""))[:10]
        if checked:
            extra["checked_on"] = checked
        if rerank is not None:
            extra["rerank"] = f"{rerank:.4f}"
        return Retrieved(
            chunk_id=c["chunk_id"],
            text=c["text"],
            section_uid=c["section_uid"],
            status=c.get("status", "in_force"),
            extraction=c.get("extraction", ""),
            pages=tuple(pages) if pages else None,
            source_url=c.get("source_url", ""),
            extra=extra,
        )
