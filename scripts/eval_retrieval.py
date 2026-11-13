"""Deterministic retrieval eval on the golden set (W1.7, plan §7, DEC-065).

Usage:
    uv run python scripts/eval_retrieval.py [--configs bm25,dense,dense-fp32,rrf,rerank-int8,...]
        [--golden PATH] [--limit N]

For each configuration, retrieves the top 10 chunks per golden row and scores Recall@10,
Recall@6 (what generation sees), MRR@10 and nDCG@10, strict and lenient, on two row sets:
``indexed`` (every expected clause has a chunk in the index now; gated) and ``all``.
Writes reports/retrieval/<set>_<date>.md (+ .json with per-row ranks); both are committed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from madhya_kanoon_saathi.eval.retrieval_metrics import (
    MATCHERS,
    RowScore,
    lenient,
    score_row,
    summarise,
)
from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder
from madhya_kanoon_saathi.retrieval.hybrid import (
    POOL,
    HybridRetriever,
    passages_from_chunks,
    rerank_hits,
    rrf,
)
from madhya_kanoon_saathi.retrieval.reranker import Reranker

GOLDEN = Path("data/golden/v0.1-seed/golden_set_v0.1_seed.jsonl")
OUT = Path("reports/retrieval")
K = 10
GATES = {"recall@10": 0.85, "mrr@10": 0.6}  # plan §7; reported, not enforced (DEC-065)
ALL_CONFIGS = "bm25,dense,dense-fp32,rrf,rerank-int8,rerank-fp32"
SLICES = ("language", "domain", "answerability")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def uid(chunk_id: str) -> str:
    return chunk_id.split("@")[0]


def load_rows(path: Path, present: set[str], limit: int | None) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        exp = [c["section_uid"] or c["act_id"] for c in r.get("expected_clauses", [])]
        if not exp:
            continue
        r["_expected"] = exp
        r["_indexed"] = all(any(lenient(p, e) for p in present) for e in exp)
        rows.append(r)
    return rows[:limit] if limit else rows


def fmt(x: float) -> str:
    return f"{x:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=ALL_CONFIGS)
    ap.add_argument("--golden", type=Path, default=GOLDEN)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--tag", default="", help="suffix for the report file name")
    a = ap.parse_args()
    configs = a.configs.split(",")

    chunks = [
        json.loads(x)
        for x in Path("data/parsed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    present = {c["section_uid"] for c in chunks}
    rows = load_rows(a.golden, present, a.limit)
    manifest = json.loads(Path("data/corpus_manifest.json").read_text(encoding="utf-8"))
    titles = {
        i["instrument_id"]: (i.get("title_en"), i.get("title_hi")) for i in manifest["instruments"]
    }
    passages = passages_from_chunks(chunks, titles)
    bm25 = Bm25Index.load(Path("data/index/bm25"))
    dense = DenseIndex.load(Path("data/index/dense-int8"))
    embedder = Embedder.load("int8")
    hybrid = HybridRetriever(bm25, dense, embedder)
    fp32 = None
    if "dense-fp32" in configs:  # DEC-021 int8 acceptance: same queries, fp32 model + index
        fp32 = (DenseIndex.load(Path("data/index/dense-fp32")), Embedder.load("fp32"))
    rerankers = {v: Reranker.load(v) for v in ("int8", "fp32") if f"rerank-{v}" in configs}

    ranked: dict[str, dict[str, list[str]]] = defaultdict(dict)  # config -> row id -> uids
    seconds: dict[str, float] = defaultdict(float)
    for i, r in enumerate(rows, 1):
        q, rid = r["raw_question_redacted"], r["id"]
        t0 = time.perf_counter()
        lex = bm25.search(q, k=POOL)
        sem = dense.search_vector(embedder.encode([q])[0], k=POOL)
        base = time.perf_counter() - t0
        pool = rrf({"bm25": lex, "dense": sem})
        if "bm25" in configs:
            ranked["bm25"][rid] = [uid(h.chunk_id) for h in lex[:K]]
        if "dense" in configs:
            ranked["dense"][rid] = [uid(h.chunk_id) for h in sem[:K]]
        if fp32 is not None:
            hits32 = fp32[0].search_vector(fp32[1].encode([q])[0], k=K)
            ranked["dense-fp32"][rid] = [uid(h.chunk_id) for h in hits32]
        if "rrf" in configs:
            ranked["rrf"][rid] = [uid(h.chunk_id) for h in pool[:K]]
            seconds["rrf"] += base
        for v, rr in rerankers.items():
            t1 = time.perf_counter()
            best = rerank_hits(rr, q, [*pool], passages, K)
            seconds[f"rerank-{v}"] += base + time.perf_counter() - t1
            ranked[f"rerank-{v}"][rid] = [uid(h.chunk_id) for h in best]
        print(f"{i}/{len(rows)} {rid}", flush=True)
    del hybrid

    # ---------------------------------------------------------------- scoring
    def scores(cfg: str, match: str, k: int, subset: list[dict[str, Any]]) -> list[RowScore]:
        return [score_row(ranked[cfg][r["id"]], r["_expected"], MATCHERS[match], k) for r in subset]

    sets = {"indexed": [r for r in rows if r["_indexed"]], "all": rows}
    today = date.today().isoformat()
    name = a.golden.parent.name
    head = git("rev-parse", "--short", "HEAD")
    dirty = " (dirty)" if git("status", "--porcelain", "--", "src", "scripts") else ""
    lines = [
        f"# Retrieval eval: golden {name}, {today}",
        "",
        "**Seed set: synthetic, unverified (`draft_unverified`). Gates are reported, not enforced"
        " (DEC-065).** Strict = DEC-040 match (chunk equals or contains the expected provision);"
        " lenient = also a part of it. Recall@6 = what the generator sees.",
        "",
        f"- git: {head}{dirty}"
        f" · chunks: {len(chunks)} · query date: {today} · dense/embedder: int8 · RRF pool {POOL}",
        f"- rows with expected clauses: {len(rows)} · indexed: {len(sets['indexed'])}",
        f"- gates (plan §7): Recall@10 ≥ {GATES['recall@10']}, MRR@10 ≥ {GATES['mrr@10']}",
        "",
    ]
    result: dict[str, Any] = {"date": today, "golden": str(a.golden), "configs": {}}
    for set_name, subset in sets.items():
        lines += [
            f"## {set_name} rows ({len(subset)})",
            "",
            "| config | match | R@10 | R@6 | MRR@10 | nDCG@10 | gates | s/query |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for cfg in configs:
            for match in ("strict", "lenient"):
                s10, s6 = (
                    summarise(scores(cfg, match, K, subset)),
                    summarise(scores(cfg, match, 6, subset)),
                )
                ok = s10.recall >= GATES["recall@10"] and s10.mrr >= GATES["mrr@10"]
                gate = ("pass" if ok else "fail") if match == "strict" else ""
                secs = (
                    f"{seconds[cfg] / len(rows):.2f}"
                    if cfg in seconds and match == "strict"
                    else ""
                )
                lines.append(
                    f"| {cfg} | {match} | {fmt(s10.recall)} | {fmt(s6.recall)} | {fmt(s10.mrr)} "
                    f"| {fmt(s10.ndcg)} | {gate} | {secs} |"
                )
                result["configs"].setdefault(cfg, {})[f"{set_name}/{match}"] = {
                    "recall@10": s10.recall, "recall@6": s6.recall, "mrr@10": s10.mrr,
                    "ndcg@10": s10.ndcg, "rows": s10.rows,
                }  # fmt: skip
        lines.append("")
    for dim in SLICES:
        lines += [
            f"## Indexed rows by {dim} (strict R@10 / MRR@10)",
            "",
            f"| {dim} | rows | " + " | ".join(configs) + " |",
            "| --- | --- | " + " | ".join("---" for _ in configs) + " |",
        ]
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in sets["indexed"]:
            groups[str(r.get(dim))].append(r)
        for g, sub in sorted(groups.items()):
            cells = []
            for cfg in configs:
                s = summarise(scores(cfg, "strict", K, sub))
                cells.append(f"{fmt(s.recall)} / {fmt(s.mrr)}")
            lines.append(f"| {g} | {len(sub)} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Indexed rows missed by every config (strict R@10 = 0)", ""]
    for r in sets["indexed"]:
        if all(
            score_row(ranked[c][r["id"]], r["_expected"], MATCHERS["strict"]).recall == 0
            for c in configs
        ):
            lines.append(
                f"- {r['id']} ({r['language']}, {r['domain']}): "
                f"expected {', '.join(r['_expected'])}"
            )
    lines.append("")

    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"{name}_{today}{a.tag}"  # not Path.with_suffix: "v0.1-seed" contains a dot
    (OUT / f"{stem}.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    result["rows"] = {
        r["id"]: {
            "expected": r["_expected"],
            "indexed": r["_indexed"],
            **{c: ranked[c][r["id"]] for c in configs},
        }
        for r in rows
    }  # fmt: skip
    (OUT / f"{stem}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print("\n".join(lines[: 14 + 2 * len(configs)]))
    print(f"-> {OUT / stem}.md / .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
