"""Tune and score the crisis router (DEC-033 item 1, DEC-074).

Usage:
    uv run python scripts/eval_crisis.py [--threshold T]

- Embeds the example crisis messages and every message of data/safety/crisis_set_v0.jsonl with the
  int8 BGE-M3 embedder (same model as retrieval).
- Threshold (unless given): the lowest same-category similarity among **dev** crisis rows, so the
  embedding layer alone catches every dev crisis (recall first); false alarms are reported, not
  optimised. Test and holdout rows are never used for tuning.
- Reports recall / false alarms per split, layer and language, lists every miss and false alarm,
  and writes reports/safety/crisis_<date>.md + data/safety/crisis_threshold.json.
- Exit code 1 if crisis recall on the test split is below 100% (the DEC-033 gate).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from madhya_kanoon_saathi.generation.crisis import ORDER, build_examples, route
from madhya_kanoon_saathi.retrieval.embedder import Embedder

DATA = Path("data/safety")
OUT = Path("reports/safety")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float)
    a = ap.parse_args()
    rows = [json.loads(x) for x in (DATA / "crisis_set_v0.jsonl").read_text("utf-8").splitlines()]
    ex = json.loads((DATA / "crisis_examples.json").read_text("utf-8"))["examples"]
    texts = {t for v in ex.values() for t in v}
    leaked = [r["id"] for r in rows if r["text"] in texts]
    if leaked:
        raise SystemExit(f"examples also in the test set: {leaked}")

    emb = Embedder.load("int8")
    vecs = emb.encode([r["text"] for r in rows])
    probe = build_examples(ex, emb.encode, threshold=1.0)  # threshold set below
    sims = [probe.similarities(v) for v in vecs]
    dev_own = [s[r["label"]] for r, s in zip(rows, sims, strict=True)
               if r["split"] == "dev" and r["label"] != "none"]  # fmt: skip
    threshold = a.threshold if a.threshold is not None else round(min(dev_own) - 1e-4, 4)
    probe.threshold = threshold

    stats: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])  # (split, layer)
    lang_stats: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    misses, alarms = [], []
    for r, v in zip(rows, vecs, strict=True):
        res = route(r["text"], v, probe)
        crisis = r["label"] != "none"
        layers = {
            "rules": r["label"] in res.by_rule if crisis else bool(res.by_rule),
            "embeddings": r["label"] in res.by_embedding if crisis else bool(res.by_embedding),
            "router": r["label"] in res.categories if crisis else res.is_crisis,
        }
        kind = "crisis" if crisis else "none"
        for layer, hit in layers.items():
            s = stats[(f"{r['split']}/{kind}", layer)]
            s[0] += hit
            s[1] += 1
        if crisis:
            ls = lang_stats[(r["split"], r["lang"])]
            ls[0] += layers["router"]
            ls[1] += 1
            if not layers["router"]:
                misses.append((r, res))
        elif res.is_crisis:
            alarms.append((r, res))

    L = [
        f"# Crisis router eval: crisis_set_v0, {date.today().isoformat()}",
        "",
        "**Synthetic draft set (Claude, 2026-11-17), not yet reviewed by Malik.** Rules and "
        "dev/test rows were written by the same author, so dev/test recall is optimistic; "
        "the holdout split "
        "was written afterwards with different wording and was not used to tune anything.",
        "",
        f"- embedder: int8 BGE-M3 · examples: {sum(len(v) for v in ex.values())} "
        f"· threshold: **{threshold}** "
        f"({'given' if a.threshold is not None else 'min dev crisis'})",
        "",
        "| split / rows | rules | embeddings | router (either) |",
        "| --- | --- | --- | --- |",
    ]
    for key in sorted({k[0] for k in stats}):
        cells = []
        for layer in ("rules", "embeddings", "router"):
            hit, n = stats[(key, layer)]
            cells.append(f"{hit}/{n}")
        what = "caught" if key.endswith("crisis") else "false alarms"
        L.append(f"| {key} ({what}) | " + " | ".join(cells) + " |")
    L += ["", "Router recall by language (crisis rows):", ""]
    L += [f"- {s} / {lg}: {h}/{n}" for (s, lg), (h, n) in sorted(lang_stats.items())]
    L += ["", "## Missed crises", ""]
    for r, res in misses:
        top = max(res.similarity.items(), key=lambda kv: kv[1]) if res.similarity else ("-", 0)
        L.append(
            f"- {r['id']} ({r['split']}, {r['label']}, best sim {top[0]} {top[1]:.3f}): {r['text']}"
        )
    L += ["", "## False alarms", ""]
    for r, res in alarms:
        L.append(
            f"- {r['id']} ({r['split']}) → {res.categories} (rules {res.by_rule}): {r['text']}"
        )
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"crisis_{date.today().isoformat()}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    (DATA / "crisis_threshold.json").write_text(
        json.dumps({"threshold": threshold, "embedder": "int8", "set": "crisis_set_v0",
                    "categories": list(ORDER), "tuned_on": "dev"}, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )  # fmt: skip
    print("\n".join(L[4:]))
    print("->", out)
    test = stats[("test/crisis", "router")]
    return 0 if test[0] == test[1] else 1


if __name__ == "__main__":
    sys.exit(main())
