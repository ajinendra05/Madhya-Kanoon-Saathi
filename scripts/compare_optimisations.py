"""Compare retrieval before and after the DEC-090 optimisations on 50 golden v1.0 questions.

    uv run python scripts/compare_optimisations.py [--rows 50] [--batch 1] [--threads 4]

Configurations (same questions, interleaved per question so machine load affects all equally):
- ``baseline``: index before the E2 filler fix (data/baseline/2026-11-23), reranker window 1024,
  batch 1, ONNX Runtime default threads, plain int8, no candidate filter, no rewriting.
- ``optimised_no_rw``: rebuilt index (E2), window 256 (A5), A4 filter, ``--batch`` (B7),
  ``--threads`` (B1), pre-optimised graph (B3); no query rewriting.
- ``optimised``: the same plus query rewriting (E1; one paid Sarvam call per question, local
  DEC-078 ledger cap).

Questions: golden v1.0 rows whose expected provisions are all indexed, taken round-robin by
language (hi, hinglish, en) up to ``--rows``. Strict matching (DEC-065).

Every result is appended to ``reports/retrieval/opt_2026-11-23/rows.jsonl`` as soon as it is
computed, with progress in ``progress.log``; a re-run skips (row, config) pairs already saved.
``summary.md`` / ``summary.json`` are rewritten after every question.
A1 (lazy retrieval), A7 (cache) and D1 (typing) do not change retrieval results; the cache is off
here so timings are honest.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from eval_retrieval import GOLDEN, load_rows, uid
from madhya_kanoon_saathi.eval.retrieval_metrics import MATCHERS, score_row
from madhya_kanoon_saathi.generation import rewrite
from madhya_kanoon_saathi.generation.llm import complete, request_body
from madhya_kanoon_saathi.generation.local import (
    LocalRuntime,
    RetrievalConfig,
)
from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.hybrid import (
    passages_from_chunks,
    rerank_hits,
    rrf,
)
from madhya_kanoon_saathi.retrieval.reranker import Reranker

OUT = Path("reports/retrieval/opt_2026-11-23")
BASE = Path("data/baseline/2026-11-23")
CONFIGS = ("baseline", "optimised_no_rw", "optimised")
LANGS = ("hi", "hinglish", "en")


def pick(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    by_lang: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in sorted((r for r in rows if r["_indexed"]), key=lambda r: r["id"]):
        by_lang[r.get("language", "en")].append(r)
    out: list[dict[str, Any]] = []
    while len(out) < n and any(by_lang.values()):
        for lang in LANGS:
            if by_lang[lang] and len(out) < n:
                out.append(by_lang[lang].pop(0))
    return out


def metrics(top: list[str], expected: list[str]) -> dict[str, float]:
    s10 = score_row(top, expected, MATCHERS["strict"], 10)
    s6 = score_row(top, expected, MATCHERS["strict"], 6)
    return {"r10": s10.recall, "r6": s6.recall, "mrr": s10.mrr}


def summarise(saved: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    agg: dict[str, Any] = {}
    lines = [
        "# Retrieval before/after DEC-090 optimisations: golden v1.0, 2026-11-23",
        "",
        "Strict matching (DEC-065), laptop i5-1155G7. `time` = rewrite + search + rerank"
        " per question.",
        "",
        "| config | slice | n | R@6 | R@10 | MRR@10 | time mean s | time p95 s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cfg in CONFIGS:
        for sl in ("all", *LANGS):
            rows = [r for r in saved if r["config"] == cfg and sl in ("all", r["language"])]
            if not rows:
                continue
            t = sorted(r["seconds"] for r in rows)
            m = {
                "n": len(rows),
                "r6": sum(r["r6"] for r in rows) / len(rows),
                "r10": sum(r["r10"] for r in rows) / len(rows),
                "mrr": sum(r["mrr"] for r in rows) / len(rows),
                "t_mean": sum(t) / len(t),
                "t_p95": t[int(0.95 * (len(t) - 1))],
            }
            agg[f"{cfg}/{sl}"] = m
            lines.append(
                f"| {cfg} | {sl} | {m['n']} | {m['r6']:.3f} | {m['r10']:.3f} | {m['mrr']:.3f} "
                f"| {m['t_mean']:.2f} | {m['t_p95']:.2f} |"
            )
    return agg, "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=50)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows_path, log_path = OUT / "rows.jsonl", OUT / "progress.log"
    saved = (
        [json.loads(x) for x in rows_path.read_text("utf-8").splitlines() if x.strip()]
        if rows_path.exists()
        else []
    )
    done = {(r["id"], r["config"]) for r in saved}
    rewrites_seen = {r["id"]: r["rewrites"] for r in saved if r["config"] == "optimised"}

    chunks = [
        json.loads(x) for x in Path("data/parsed/chunks.jsonl").read_text("utf-8").splitlines()
    ]
    rows = pick(load_rows(GOLDEN, {c["section_uid"] for c in chunks}, None), a.rows)

    # baseline: old index + old passages, window 1024, plain int8, default threads
    old = [json.loads(x) for x in (BASE / "parsed/chunks.jsonl").read_text("utf-8").splitlines()]
    man = json.loads(Path("data/corpus_manifest.json").read_text("utf-8"))
    titles = {
        i["instrument_id"]: (i.get("title_en"), i.get("title_hi")) for i in man["instruments"]
    }
    old_passages = passages_from_chunks(old, titles)
    old_bm25 = Bm25Index.load(BASE / "index/bm25")
    old_dense = DenseIndex.load(BASE / "index/dense-int8")
    old_rr = Reranker.load("int8", max_length=1024)

    cfg = RetrievalConfig(
        rerank_window=256,
        rerank_batch=a.batch,
        rerank_variant="int8-opt",
        threads=a.threads,
        cache_size=0,
    )
    rt = LocalRuntime.load(config=cfg)

    def rewrite_call(messages: list[dict[str, str]]) -> str:
        body = request_body(messages, "json_object", reasoning_effort="low", max_tokens=200)
        return complete(body, purpose="eval_rewrite_dec090").content

    on = date(2026, 11, 23)
    with (
        rows_path.open("a", encoding="utf-8", newline="\n") as out,
        log_path.open("a", encoding="utf-8", newline="\n") as log,
    ):
        log.write(
            f"start {time.strftime('%H:%M:%S')} rows={len(rows)}"
            f" batch={a.batch} threads={a.threads}\n"
        )
        for i, r in enumerate(rows, 1):
            q, exp, lang = r["raw_question_redacted"], r["_expected"], r.get("language", "en")
            for name in CONFIGS:
                if (r["id"], name) in done:
                    continue
                rw: list[str] = []
                t0 = time.perf_counter()
                if name == "baseline":
                    vec = rt.embedder.encode([q])[0]  # same model file as the baseline index
                    pool = rrf(
                        {
                            "bm25": old_bm25.search(q, k=40, on=on),
                            "dense": old_dense.search_vector(vec, k=40, on=on),
                        }
                    )
                    top = [uid(h.chunk_id) for h in rerank_hits(old_rr, q, pool, old_passages, 10)]
                else:
                    if name == "optimised":
                        rw = rewrites_seen.get(r["id"]) or rewrite.rewrite(q, rewrite_call)
                        rewrites_seen[r["id"]] = rw
                    rt.config = RetrievalConfig(**{**vars(cfg), "final": 10})
                    hits = rt.retrieve(q, rt.vector(q), on, rewrites=rw)
                    top = [uid(h.chunk_id) for h in hits]
                secs = time.perf_counter() - t0
                rec = {
                    "id": r["id"],
                    "config": name,
                    "language": lang,
                    "seconds": round(secs, 3),
                    "rewrites": rw,
                    "top10": top,
                    "expected": exp,
                    **metrics(top, exp),
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                saved.append(rec)
                log.write(
                    f"{time.strftime('%H:%M:%S')} {i}/{len(rows)} {r['id']} {lang} {name} "
                    f"{secs:.1f}s r6={rec['r6']:.2f} mrr={rec['mrr']:.2f}\n"
                )
                log.flush()
            agg, md = summarise(saved)
            (OUT / "summary.md").write_text(md, encoding="utf-8", newline="\n")
            (OUT / "summary.json").write_text(
                json.dumps(agg, indent=1), encoding="utf-8", newline="\n"
            )
        log.write(f"done {time.strftime('%H:%M:%S')}\n")
    print((OUT / "summary.md").read_text("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
