"""Run hybrid retrieval + reranking on golden questions: latency and int8-vs-fp32 agreement.

A quick check for W1.5, **not** the W1.7 retrieval eval (no slices, unverified seed rows).

Usage:
    uv run python scripts/try_rerank.py [--pool 40] [--rows 20]
        [--variants int8,fp32] [--max-length 1024]

Uses golden rows whose expected clauses are all retrievable now; a row "hits" when a top-6
chunk and an expected clause cover each other (equal, ancestor or descendant; DEC-040).
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from madhya_kanoon_saathi.common.section_uid import covers
from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder
from madhya_kanoon_saathi.retrieval.hybrid import (
    FINAL,
    HybridRetriever,
    passages_from_chunks,
    rerank_hits,
)
from madhya_kanoon_saathi.retrieval.reranker import Reranker

GOLDEN = Path("data/golden/v0.1-seed/golden_set_v0.1_seed.jsonl")


def hit(chunk_ids: list[str], expected: list[str]) -> bool:
    uids = [c.split("@")[0] for c in chunk_ids]
    return any(covers(u, e) or covers(e, u) for u in uids for e in expected)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", type=int, default=40)
    ap.add_argument("--rows", type=int, default=20)
    ap.add_argument("--variants", default="int8,fp32")
    ap.add_argument("--max-length", type=int, default=1024)
    a = ap.parse_args()

    chunks = [
        json.loads(x)
        for x in Path("data/parsed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    present = {c["section_uid"] for c in chunks}
    manifest = json.loads(Path("data/corpus_manifest.json").read_text(encoding="utf-8"))
    titles = {
        i["instrument_id"]: (i.get("title_en"), i.get("title_hi")) for i in manifest["instruments"]
    }
    passages = passages_from_chunks(chunks, titles)

    rows = []
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        exp = [c["section_uid"] for c in r["expected_clauses"] if c["section_uid"]]
        if exp and all(any(covers(p, e) or covers(e, p) for p in present) for e in exp):
            rows.append((r["id"], r["language"], r["raw_question_redacted"], exp))
    rows = rows[: a.rows]

    hybrid = HybridRetriever(
        Bm25Index.load(Path("data/index/bm25")),
        DenseIndex.load(Path("data/index/dense-int8")),
        Embedder.load("int8"),
    )
    variants = a.variants.split(",")
    rerankers = {v: Reranker.load(v, max_length=a.max_length) for v in variants}

    times: dict[str, list[float]] = {v: [] for v in variants}
    hits = {"rrf": 0, **{v: 0 for v in variants}}
    same_top1 = overlap = 0
    for rid, lang, q, exp in rows:
        pool = hybrid.search(q, k=a.pool)
        top = {"rrf": [h.chunk_id for h in pool[:FINAL]]}
        for v, rr in rerankers.items():
            t0 = time.perf_counter()
            best = rerank_hits(rr, q, [*pool], passages, FINAL)
            times[v].append(time.perf_counter() - t0)
            top[v] = [h.chunk_id for h in best]
        for k in hits:
            hits[k] += hit(top[k], exp)
        if len(variants) == 2:
            same_top1 += top[variants[0]][:1] == top[variants[1]][:1]
            overlap += len(set(top[variants[0]]) & set(top[variants[1]]))
        marks = " ".join(f"{k}={'Y' if hit(top[k], exp) else '-'}" for k in hits)
        print(f"{rid} {lang:8} {marks}  {top[variants[0]][0]}", flush=True)
    n = len(rows)
    print(f"\nrows {n}, pool {a.pool}, top {FINAL}")
    print("hit@6  " + "  ".join(f"{k} {v}/{n}" for k, v in hits.items()))
    if len(variants) == 2:
        print(
            f"{variants[0]} vs {variants[1]}: same top-1 {same_top1}/{n}, "
            f"mean top-6 overlap {overlap / n:.1f}/6"
        )
    for v, ts in times.items():
        ts = sorted(ts)
        p95 = ts[max(0, round(0.95 * len(ts)) - 1)]
        print(f"rerank {v}: median {statistics.median(ts):.2f}s  p95 {p95:.2f}s  max {ts[-1]:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
