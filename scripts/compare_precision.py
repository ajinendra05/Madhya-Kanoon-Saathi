"""Paired int8-vs-fp32 retrieval comparison from one eval report (DEC-021, DEC-066 step 5).

Both configs come from the same ``eval_retrieval.py`` run, so they share the golden rows, corpus
snapshot, retrieval settings and eval code (DEC-066 item 1). Scores strict Recall@10 on the
report's indexed rows, per language; verified rows decide pass/fail (>= 50 per slice).

    uv run python scripts/compare_precision.py --report reports/retrieval/<run>.json \
        [--pair dense,dense-fp32] [--pair rerank-int8,rerank-fp32]

Writes reports/retrieval/<run>_precision.{md,json}.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from madhya_kanoon_saathi.eval.paired import (
    MIN_VERIFIED,
    N_BOOT,
    TOLERANCE,
    PairRow,
    accepted,
    compare,
)
from madhya_kanoon_saathi.eval.retrieval_metrics import strict

K = 10


def hits(retrieved: list[str], expected: list[str]) -> int:
    return sum(any(strict(u, e) for u in retrieved[:K]) for e in expected)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows console is cp1252
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--pair", action="append", help="a,b config names (a = int8, b = fp32)")
    a = ap.parse_args()
    pairs = [tuple(p.split(",")) for p in (a.pair or ["dense,dense-fp32"])]

    report = json.loads(a.report.read_text(encoding="utf-8"))
    golden = {
        (r := json.loads(x))["id"]: r
        for x in Path(report["golden"]).read_text(encoding="utf-8").splitlines()
    }
    out: dict[str, Any] = {"report": a.report.as_posix(), "golden": report["golden"], "pairs": {}}
    lines = [
        f"# int8 vs fp32, paired: {a.report.stem}",
        "",
        f"DEC-021 rule: int8 strict Recall@{K} >= fp32 - {TOLERANCE}, overall and per language. "
        f"Verdicts use verified golden rows only and need >= {MIN_VERIFIED} per slice (DEC-066); "
        f"otherwise `insufficient_sample`. diff = int8 - fp32; 95% CI from a paired bootstrap "
        f"({N_BOOT} resamples of rows, fixed seed). Rows: indexed rows of the report.",
    ]
    for ca, cb in pairs:
        rows = []
        for rid, v in report["rows"].items():
            if not v["indexed"] or ca not in v or cb not in v:
                continue
            g = golden[rid]
            rows.append(
                PairRow(
                    row_id=rid,
                    slice=g["language"],
                    verified=g.get("review_status") == "verified",
                    expected=len(v["expected"]),
                    hits_a=hits(v[ca], v["expected"]),
                    hits_b=hits(v[cb], v["expected"]),
                )
            )
        if not rows:
            raise SystemExit(f"no indexed rows carry both {ca} and {cb}")
        res = compare(rows)
        decision = accepted(res)
        changed = [
            f"{r.row_id} ({r.slice}): {ca} {r.hits_a}/{r.expected} vs {cb} {r.hits_b}/{r.expected}"
            for r in rows
            if r.hits_a != r.hits_b
        ]
        out["pairs"][f"{ca} vs {cb}"] = {
            "decision": decision,
            "slices": [asdict(s) for s in res],
            "disagreements": changed,
        }
        lines += [
            "",
            f"## {ca} vs {cb}: **{decision}**",
            "",
            "| slice | questions | verified | clauses | hits a / b | misses a / b "
            "| R@10 a | R@10 b | diff | 95% CI | a better / b better | verdict |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for s in res:
            lines.append(
                f"| {s.name} | {s.questions} | {s.verified} | {s.clauses} "
                f"| {s.hits_a} / {s.hits_b} | {s.clauses - s.hits_a} / {s.clauses - s.hits_b} "
                f"| {s.recall_a:.3f} "
                f"| {s.recall_b:.3f} | {s.diff:+.3f} | [{s.ci_low:+.3f}, {s.ci_high:+.3f}] "
                f"| {s.a_better} / {s.b_better} | {s.verdict} |"
            )
        lines += ["", "Paired disagreements:", ""]
        lines += [f"- {c}" for c in changed] or ["- none"]

    stem = f"{a.report.stem}_precision"
    dest = a.report.parent
    (dest / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (dest / f"{stem}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"-> {dest / stem}.md / .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
