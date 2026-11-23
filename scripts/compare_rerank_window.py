"""Reranker window 1024 vs 256 on golden v1.0: same RRF pool, same int8 model, timing + quality."""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "scripts")
from eval_retrieval import GOLDEN, K, load_rows, uid
from madhya_kanoon_saathi.eval.retrieval_metrics import MATCHERS, score_row, summarise
from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder
from madhya_kanoon_saathi.retrieval.hybrid import POOL, passages_from_chunks, rerank_hits, rrf
from madhya_kanoon_saathi.retrieval.reranker import Reranker

chunks = [json.loads(x) for x in Path("data/parsed/chunks.jsonl").read_text("utf-8").splitlines()]
rows = load_rows(GOLDEN, {c["section_uid"] for c in chunks}, None)
man = json.loads(Path("data/corpus_manifest.json").read_text("utf-8"))
titles = {i["instrument_id"]: (i.get("title_en"), i.get("title_hi")) for i in man["instruments"]}
passages = passages_from_chunks(chunks, titles)
bm25, dense, emb = (
    Bm25Index.load(Path("data/index/bm25")),
    DenseIndex.load(Path("data/index/dense-int8")),
    Embedder.load("int8"),
)
windows = {1024: Reranker.load("int8", max_length=1024), 256: Reranker.load("int8", max_length=256)}
ranked, secs, trunc = defaultdict(dict), defaultdict(list), defaultdict(int)
for i, r in enumerate(rows, 1):
    q = r["raw_question_redacted"]
    pool = rrf(
        {"bm25": bm25.search(q, k=POOL), "dense": dense.search_vector(emb.encode([q])[0], k=POOL)}
    )
    for w, rr in windows.items():
        t = time.perf_counter()
        best = rerank_hits(rr, q, [*pool], passages, K)
        secs[w].append(time.perf_counter() - t)
        trunc[w] += rr.last_stats.truncated
        ranked[w][r["id"]] = [uid(h.chunk_id) for h in best]
    print(f"{i}/{len(rows)}", flush=True, file=sys.stderr)
out = {}
for subset_name, subset in {"indexed": [r for r in rows if r["_indexed"]], "all": rows}.items():
    for w in windows:
        s10 = summarise(
            [score_row(ranked[w][r["id"]], r["_expected"], MATCHERS["strict"], 10) for r in subset]
        )
        s6 = summarise(
            [score_row(ranked[w][r["id"]], r["_expected"], MATCHERS["strict"], 6) for r in subset]
        )
        out[f"{subset_name}/{w}"] = {
            "rows": len(subset),
            "R@10": round(s10.recall, 3),
            "R@6": round(s6.recall, 3),
            "MRR@10": round(s10.mrr, 3),
        }
for w in windows:
    s = sorted(secs[w])
    out[f"time/{w}"] = {
        "mean_s": round(sum(s) / len(s), 2),
        "p50_s": round(s[len(s) // 2], 2),
        "p95_s": round(s[int(0.95 * (len(s) - 1))], 2),
        "truncated_pairs": trunc[w],
    }
changed = sum(ranked[1024][r["id"]][:6] != ranked[256][r["id"]][:6] for r in rows)
out["top6_lists_changed"] = f"{changed}/{len(rows)}"
print(json.dumps(out, indent=1))
