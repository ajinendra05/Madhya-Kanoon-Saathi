# ruff: noqa: E501
"""Tune and score the dispute ("who is right") detector (DEC-033 item 6, DEC-076).

Usage:
    uv run python scripts/eval_dispute.py [--threshold T]

Same method as scripts/eval_crisis.py: int8 BGE-M3 margin (nearest merits example minus nearest
procedural question), threshold = lowest dev merits margin (recall first); test and holdout are
never used for tuning. Writes reports/safety/dispute_<date>.md and
data/safety/dispute_threshold.json. Exit 1 if test recall is below 100%.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from madhya_kanoon_saathi.generation.crisis import build_examples
from madhya_kanoon_saathi.generation.dispute import MERITS, route
from madhya_kanoon_saathi.retrieval.embedder import Embedder

DATA = Path("data/safety")
OUT = Path("reports/safety")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float)
    a = ap.parse_args()
    rows = [json.loads(x) for x in (DATA / "dispute_set_v0.jsonl").read_text("utf-8").splitlines()]
    exf = json.loads((DATA / "dispute_examples.json").read_text("utf-8"))
    ex, ordinary = exf["examples"], exf["ordinary"]
    leaked = [r["id"] for r in rows if r["text"] in set(ex[MERITS]) | set(ordinary)]
    if leaked:
        raise SystemExit(f"examples also in the test set: {leaked}")

    emb = Embedder.load("int8")
    vecs = emb.encode([r["text"] for r in rows])
    idx = build_examples(ex, emb.encode, 1.0, ordinary, categories=[MERITS])
    margins = [idx.similarities(v)[MERITS] for v in vecs]
    dev = [
        m
        for r, m in zip(rows, margins, strict=True)
        if r["split"] == "dev" and r["label"] == MERITS
    ]
    idx.threshold = a.threshold if a.threshold is not None else round(min(dev) - 1e-4, 4)

    stats: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    misses, alarms = [], []
    for r, v in zip(rows, vecs, strict=True):
        res = route(r["text"], v, idx)
        pos = r["label"] == MERITS
        layers = {"rules": res.by_rule, "embeddings": res.by_embedding, "detector": res.is_dispute}
        for layer, hit in layers.items():
            s = stats[(f"{r['split']}/{'merits' if pos else 'procedural'}", layer)]
            s[0] += hit
            s[1] += 1
        if pos and not res.is_dispute:
            misses.append((r, res))
        if not pos and res.is_dispute:
            alarms.append((r, res))

    L = [
        f"# Dispute detector eval: dispute_set_v0, {date.today().isoformat()}",
        "",
        "**Synthetic draft set (Claude, 2026-11-18) + 5 golden rows; not yet reviewed by Malik.** "
        "Holdout rows were written before the embedding layer was scored and were not used to tune.",
        "",
        f"- embedder: int8 BGE-M3 · merits examples: {len(ex[MERITS])} · procedural anchors: "
        f"{len(ordinary)} · margin threshold: **{idx.threshold}**",
        "",
        "| split / rows | rules | embeddings | detector (either) |",
        "| --- | --- | --- | --- |",
    ]
    for key in sorted({k[0] for k in stats}):
        what = "caught" if key.endswith("merits") else "false alarms"
        cells = [
            f"{stats[(key, x)][0]}/{stats[(key, x)][1]}"
            for x in ("rules", "embeddings", "detector")
        ]
        L.append(f"| {key} ({what}) | " + " | ".join(cells) + " |")
    L += ["", "## Missed", ""]
    L += [f"- {r['id']} ({r['split']}, margin {res.margin:.3f}): {r['text']}" for r, res in misses]
    L += ["", "## False alarms", ""]
    L += [
        f"- {r['id']} ({r['split']}, rule {res.by_rule}, margin {res.margin:.3f}): {r['text']}"
        for r, res in alarms
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"dispute_{date.today().isoformat()}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    (DATA / "dispute_threshold.json").write_text(
        json.dumps({"threshold": idx.threshold, "embedder": "int8", "set": "dispute_set_v0",
                    "score": "margin", "tuned_on": "dev"}, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )  # fmt: skip
    print("\n".join(L[4:]))
    test = stats[("test/merits", "detector")]
    return 0 if test[0] == test[1] else 1


if __name__ == "__main__":
    sys.exit(main())
