"""Compare candidate-pool strategies for the reranker (S20, DEC-068).

The reranker re-sorts its whole pool, so what matters is which expected provisions reach the
pool ("pool recall"), not the fused order. For each strategy and pool size this reports strict
pool recall on the golden rows whose expected clauses are all indexed, per language.

    uv run python scripts/compare_fusion.py [--golden PATH] [--pools 40,20]

Writes reports/retrieval/<set>_<date>_fusion.{md,json}. Needs the built indexes and int8 model.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from collections.abc import Callable
from datetime import date
from pathlib import Path

from madhya_kanoon_saathi.eval.retrieval_metrics import MATCHERS, lenient, score_row
from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder
from madhya_kanoon_saathi.retrieval.hybrid import POOL, RRF_K, rrf

OUT = Path("reports/retrieval")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
LANGS = ("en", "hi", "hinglish")

Strategy = Callable[[list[str], list[str], str, int], list[str]]


def weighted_rrf(lists: dict[str, list[str]], weights: dict[str, float], limit: int) -> list[str]:
    """RRF with a weight per retriever; ties keep first-appearance order (as hybrid.rrf)."""
    score: dict[str, float] = defaultdict(float)
    first: dict[str, int] = {}
    for name, ids in lists.items():
        for rank, cid in enumerate(ids, start=1):
            score[cid] += weights[name] / (RRF_K + rank)
            first.setdefault(cid, len(first))
    return sorted(score, key=lambda c: (-score[c], first[c]))[:limit]


def union(dense: list[str], bm25: list[str], n_dense: int, limit: int) -> list[str]:
    out = list(dense[:n_dense])
    for cid in bm25:
        if len(out) >= limit:
            break
        if cid not in out:
            out.append(cid)
    return out


STRATEGIES: dict[str, Strategy] = {
    "dense only": lambda d, b, q, n: d[:n],
    "RRF 1:1 (current)": lambda d, b, q, n: weighted_rrf({"b": b, "d": d}, {"b": 1, "d": 1}, n),
    "RRF bm25 x0.5": lambda d, b, q, n: weighted_rrf({"b": b, "d": d}, {"b": 0.5, "d": 1}, n),
    "dense 3/4 + bm25 1/4": lambda d, b, q, n: union(d, b, n * 3 // 4, n),
    "RRF 1:1, no BM25 for Devanagari": lambda d, b, q, n: (
        d[:n] if DEVANAGARI.search(q) else weighted_rrf({"b": b, "d": d}, {"b": 1, "d": 1}, n)
    ),
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows console is cp1252
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--golden", type=Path, default=Path("data/golden/v0.1-seed/golden_set_v0.1_seed.jsonl")
    )
    ap.add_argument("--pools", default="40,20")
    a = ap.parse_args()
    pools = [int(p) for p in a.pools.split(",")]
    if max(pools) > POOL:
        raise SystemExit(f"pool sizes above {POOL} would need deeper retriever lists")

    chunks = [
        json.loads(x)
        for x in Path("data/parsed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    present = {c["section_uid"] for c in chunks}
    rows = []
    for line in a.golden.read_text(encoding="utf-8").splitlines():  # same row set as eval_retrieval
        r = json.loads(line)
        exp = [c["section_uid"] or c["act_id"] for c in r.get("expected_clauses", [])]
        if exp and all(any(lenient(p, e) for p in present) for e in exp):
            r["_expected"] = exp
            rows.append(r)
    bm25 = Bm25Index.load(Path("data/index/bm25"))
    dense = DenseIndex.load(Path("data/index/dense-int8"))
    embedder = Embedder.load("int8")

    def uid(cid: str) -> str:
        return cid.split("@")[0]

    recall: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for r in rows:
        q = r["raw_question_redacted"]
        expected = r["_expected"]
        lex = bm25.search(q, k=POOL)
        sem = dense.search_vector(embedder.encode([q])[0], k=POOL)
        b, d = [h.chunk_id for h in lex], [h.chunk_id for h in sem]
        # the 1:1 strategy must reproduce the production fusion exactly
        assert weighted_rrf({"b": b, "d": d}, {"b": 1, "d": 1}, POOL) == [
            h.chunk_id for h in rrf({"bm25": lex, "dense": sem})
        ]
        for name, strategy in STRATEGIES.items():
            for n in pools:
                pool = [uid(c) for c in strategy(d, b, q, n)]
                s = score_row(pool, expected, MATCHERS["strict"], n)
                for sl in ("all", r["language"]):
                    recall[(name, n, sl)].append(s.recall)

    head = (
        f"| strategy | pool | all ({len(rows)}) | "
        + " | ".join(
            f"{lang} ({len(recall[(next(iter(STRATEGIES)), pools[0], lang)])})" for lang in LANGS
        )
        + " |"
    )
    lines = [
        f"# Reranker candidate pools: golden {a.golden.parent.name}, {date.today().isoformat()}",
        "",
        "Strict pool recall (share of expected provisions inside the pool the reranker sees), "
        "on rows whose expected clauses have a chunk in the index. "
        "Seed set: synthetic, unverified. S20, DEC-068.",
        "",
        head,
        "| --- | --- | --- | " + " | ".join("---" for _ in LANGS) + " |",
    ]
    table = {}
    for name in STRATEGIES:
        for n in pools:
            vals = {sl: sum(v) / len(v) for sl in ("all", *LANGS) if (v := recall[(name, n, sl)])}
            table[f"{name}|{n}"] = vals
            cells = " | ".join(f"{vals[x]:.3f}" if x in vals else "-" for x in LANGS)
            lines.append(f"| {name} | {n} | {vals['all']:.3f} | {cells} |")
    stem = f"{a.golden.parent.name}_{date.today().isoformat()}_fusion"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / f"{stem}.json").write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"-> {OUT / stem}.md / .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
