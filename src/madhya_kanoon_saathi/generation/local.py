"""Local runtime: loads chunks, manifest, indexes, embedder, reranker and the safety indexes,
and turns retrieval hits into :class:`~madhya_kanoon_saathi.generation.pipeline.Retrieved`.

Used by ``scripts/ask.py`` (local CLI) and later by the answer Lambda (W3.1). Retrieval follows
DEC-068: BM25 + dense (int8) fused by RRF into a pool of 40, reranked by the int8 cross-encoder,
in-force law first (DEC-067), top 6 to the generator. The query vector is computed once and reused
by the crisis router and the dispute detector (DEC-074/076).

Speed/quality options (docs/RERANKER.md, DEC-090) come from :class:`RetrievalConfig`, overridable
by environment variables (``MKS_RERANK_WINDOW`` etc.) so Cloud Run can set them without a rebuild:
A4 drops filler and duplicate-text candidates before reranking; A5 reranker window; A7 a small
in-process cache of recent retrievals; B1 thread count; B3 pre-optimised reranker; B7 batch size;
E1 extra BM25 + dense searches for the query rewrites, all fused by RRF.
"""

from __future__ import annotations

import json
import os
import re
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from madhya_kanoon_saathi.common.normalize import normalize
from madhya_kanoon_saathi.generation.crisis import ExampleIndex, build_examples
from madhya_kanoon_saathi.generation.dispute import MERITS
from madhya_kanoon_saathi.generation.pipeline import Retrieved
from madhya_kanoon_saathi.ingestion.chunker import MIN_CONTENT_SHARE, content_share
from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index, Hit
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder
from madhya_kanoon_saathi.retrieval.hybrid import FusedHit, passages_from_chunks, rerank_hits, rrf
from madhya_kanoon_saathi.retrieval.reranker import Reranker

DATA = Path("data")
POOL, FINAL = 40, 6
_DEVANAGARI = re.compile("[\u0900-\u097f]")


def _env_int(name: str, default: int | None) -> int | None:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


@dataclass(frozen=True)
class RetrievalConfig:
    pool: int = 20  # A2: candidates the reranker scores (DEC-091, DEC-093)
    final: int = FINAL
    search_k: int = POOL  # hits each BM25 / dense list contributes before fusion
    rerank_window: int = 256  # A5 (DEC-090)
    rerank_batch: int = 1  # B7: set from the batch benchmark
    rerank_variant: str = "int8"  # B3: "int8-opt" once the optimised file is built and recorded
    threads: int | None = None  # B1: None = ONNX Runtime default; Cloud Run sets the vCPU count
    drop_filler: bool = True  # A4
    one_version: bool = True  # A3: one language version per provision in the rerank pool
    cache_size: int = 256  # A7: recent questions kept per process

    @classmethod
    def from_env(cls) -> RetrievalConfig:
        d = cls()
        return cls(
            pool=_env_int("MKS_RERANK_POOL", d.pool) or d.pool,
            search_k=_env_int("MKS_SEARCH_K", d.search_k) or d.search_k,
            rerank_window=_env_int("MKS_RERANK_WINDOW", d.rerank_window) or d.rerank_window,
            rerank_batch=_env_int("MKS_RERANK_BATCH", d.rerank_batch) or d.rerank_batch,
            rerank_variant=os.environ.get("MKS_RERANK_VARIANT", "").strip() or d.rerank_variant,
            threads=_env_int("MKS_ORT_THREADS", d.threads),
            cache_size=_env_int("MKS_RETRIEVAL_CACHE", d.cache_size) or 0,
        )


def chunk_lang(chunk_id: str) -> str:
    return chunk_id.split("@")[1] if chunk_id.count("@") >= 2 else ""


def provision_key(chunk_id: str) -> str:
    """Provision + part: language versions share it; "~n" parts of one long unit do not."""
    uid, _, rest = chunk_id.partition("@")
    part = rest.rpartition("~")[2] if "~" in rest else ""
    return f"{uid}~{part}" if part else uid


def one_version_per_provision(hits: Sequence[FusedHit], prefer: str) -> list[FusedHit]:
    """A3: keep one chunk per provision (language ``prefer`` if the pool has it, else the best
    ranked), at the position of the provision's best-ranked chunk. The generator can still see the
    other language through ``versions()`` (e.g. RTI Rules r.14, DEC-077)."""
    groups: dict[str, list[FusedHit]] = {}
    order: list[str] = []
    for h in hits:
        k = provision_key(h.chunk_id)
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(h)
    out = []
    for k in order:
        g = groups[k]
        out.append(next((h for h in g if chunk_lang(h.chunk_id) == prefer), g[0]))
    return out


def keep_candidates(
    hits: Sequence[FusedHit], passages: dict[str, str], drop_filler: bool
) -> list[FusedHit]:
    """A4: skip candidates that are mostly filler, and later candidates whose passage text is
    identical to an earlier one (RRF order kept)."""
    out: list[FusedHit] = []
    seen: set[str] = set()
    for h in hits:
        text = passages[h.chunk_id]
        if drop_filler and content_share(text) < MIN_CONTENT_SHARE:
            continue
        key = " ".join(text.split())
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


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
    config: RetrievalConfig = field(default_factory=RetrievalConfig)
    _cache: OrderedDict[tuple[str, str, tuple[str, ...]], list[Retrieved]] = field(
        default_factory=OrderedDict
    )
    last_rerank_query: str = ""

    @classmethod
    def load(cls, data: Path = DATA, config: RetrievalConfig | None = None) -> LocalRuntime:
        cfg = config or RetrievalConfig.from_env()
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
        embedder = Embedder.load("int8", threads=cfg.threads)
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
            reranker=Reranker.load(
                cfg.rerank_variant,
                max_length=cfg.rerank_window,
                threads=cfg.threads,
                batch_size=cfg.rerank_batch,
            ),
            passages=passages_from_chunks(list(chunks.values()), titles),
            crisis_index=build_examples(cex["examples"], embedder.encode, ct, cex["ordinary"]),
            dispute_index=build_examples(
                dex["examples"], embedder.encode, dt, dex["ordinary"], categories=[MERITS]
            ),
            config=cfg,
        )

    def vector(self, question: str) -> np.ndarray:
        return np.asarray(self.embedder.encode([question])[0])

    def retrieve(
        self, question: str, vec: np.ndarray, on: date, rewrites: Sequence[str] = ()
    ) -> list[Retrieved]:
        """BM25 + dense for the question (and each rewrite, E1), RRF, A4 filter, rerank, top k."""
        cfg = self.config
        key = (normalize(question, fold_nukta=True).casefold(), on.isoformat(), tuple(rewrites))
        if cfg.cache_size and key in self._cache:  # A7
            self._cache.move_to_end(key)
            return list(self._cache[key])
        k = cfg.search_k
        lists: dict[str, Sequence[Hit]] = {
            "bm25": self.bm25.search(question, k=k, on=on),
            "dense": self.dense.search_vector(vec, k=k, on=on),
        }
        if rewrites:
            vecs = self.embedder.encode(list(rewrites))
            for i, (q, v) in enumerate(zip(rewrites, vecs, strict=True)):
                lists[f"bm25_rw{i}"] = self.bm25.search(q, k=k, on=on)
                lists[f"dense_rw{i}"] = self.dense.search_vector(np.asarray(v), k=k, on=on)
        # fuse everything, filter (A4, A3), then cut to the rerank pool (A2)
        fused = keep_candidates(rrf(lists, limit=10_000), self.passages, cfg.drop_filler)
        if cfg.one_version:
            fused = one_version_per_provision(fused, "hi" if _DEVANAGARI.search(question) else "en")
        pool = fused[: cfg.pool]
        # the reranker judges against the user's words plus the formal English rewrite
        rerank_query = f"{question}\n{rewrites[0]}" if rewrites else question
        self.last_rerank_query = rerank_query
        hits = rerank_hits(self.reranker, rerank_query, pool, self.passages, cfg.final)
        # the reranker logit rides along for abstention-threshold analysis (eval); not used yet
        out = [self._as_retrieved(self.chunks[h.chunk_id], h.rerank_score) for h in hits]
        if cfg.cache_size:
            self._cache[key] = out
            while len(self._cache) > cfg.cache_size:
                self._cache.popitem(last=False)
        return list(out)

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
