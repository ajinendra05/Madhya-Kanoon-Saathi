# ruff: noqa: E501
"""W1.6 embedding bake-off: BGE-M3 vs multilingual-e5-large (DEC-004: keep the winner by recall@10
per language, hi and en; dense retrieval only, same chunks, same golden rows, same filters).

Usage:
    uv run python scripts/bakeoff_e5.py

- e5: ``intfloat/multilingual-e5-large`` official ONNX export (MIT), pinned revision below;
  files go to data/models/e5-large/<revision>/ (git-ignored) and their sha256 are added to
  data/parsed_manifest/models.json. Model card: inputs need the prefixes ``query: `` and
  ``passage: ``; sentence vector = mean of token vectors over the attention mask, L2-normalised.
  Passages use the same text as BGE (DEC-061 ``embed_text``), with the prefix.
- BGE-M3: the existing int8 and fp32 dense indexes.
- Writes reports/retrieval/<golden>_<date>_bakeoff_e5.md and the e5 vectors to
  data/index/dense-e5-fp32/ (git-ignored; reused on re-runs).
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

from madhya_kanoon_saathi.eval.retrieval_metrics import lenient, score_row, strict, summarise
from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import Embedder, embed_text

REPO = "intfloat/multilingual-e5-large"
REVISION = "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3"  # HF API, checked 2026-11-18; licence MIT
FILES = ["onnx/model.onnx", "onnx/model.onnx_data", "onnx/tokenizer.json", "onnx/config.json"]
DEST = Path("data/models/e5-large") / REVISION
RECORD = Path("data/parsed_manifest/models.json")
VEC_DIR = Path("data/index/dense-e5-fp32")
GOLDEN = Path("data/golden/v1.0/golden_set_v1.0.jsonl")
MAX_LEN = 512  # e5-large position limit
K = 10


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch() -> Path:
    for f in FILES:
        hf_hub_download(REPO, f, revision=REVISION, local_dir=DEST)
    rec = json.loads(RECORD.read_text("utf-8")) if RECORD.is_file() else {}
    rec["e5-large-fp32"] = {
        "repo": REPO,
        "revision": REVISION,
        "dir": DEST.as_posix(),
        "licence": "MIT",
        "files": [
            {"file": f, "sha256": sha256(DEST / f), "bytes": (DEST / f).stat().st_size}
            for f in FILES
        ],
    }
    RECORD.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return DEST


class E5:
    def __init__(self, folder: Path) -> None:
        self.sess = ort.InferenceSession(
            str(folder / "onnx/model.onnx"), providers=["CPUExecutionProvider"]
        )
        self.inputs = {i.name for i in self.sess.get_inputs()}
        self.tok = Tokenizer.from_file(str(folder / "onnx/tokenizer.json"))
        self.tok.no_padding()
        self.tok.no_truncation()

    def encode(self, texts: list[str], batch: int = 8) -> np.ndarray:
        encs = self.tok.encode_batch(texts)
        out = np.zeros((len(texts), 1024), dtype=np.float32)
        order = np.argsort([len(e.ids) for e in encs], kind="stable")
        for s in range(0, len(order), batch):
            idx = order[s : s + batch]
            seqs = [encs[i].ids[:MAX_LEN] for i in idx]
            for q in seqs:
                if len(q) == MAX_LEN:
                    q[-1] = 2  # keep </s>
            w = max(len(q) for q in seqs)
            ids = np.full((len(seqs), w), 1, dtype=np.int64)
            mask = np.zeros((len(seqs), w), dtype=np.int64)
            for r, q in enumerate(seqs):
                ids[r, : len(q)] = q
                mask[r, : len(q)] = 1
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(ids)
            hidden = self.sess.run(None, feed)[0]  # last_hidden_state (b, w, 1024)
            m = mask[..., None].astype(np.float32)
            out[idx] = (hidden * m).sum(1) / np.maximum(m.sum(1), 1e-9)
        return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    chunks = [
        json.loads(x) for x in Path("data/parsed/chunks.jsonl").read_text("utf-8").splitlines()
    ]
    manifest = json.loads(Path("data/corpus_manifest.json").read_text("utf-8"))
    titles = {
        i["instrument_id"]: (i.get("title_en"), i.get("title_hi")) for i in manifest["instruments"]
    }
    bge = {"bge-int8": (DenseIndex.load(Path("data/index/dense-int8")), Embedder.load("int8")),
           "bge-fp32": (DenseIndex.load(Path("data/index/dense-fp32")), Embedder.load("fp32"))}  # fmt: skip
    order = [m["chunk_id"] for m in bge["bge-int8"][0].meta]
    by_id = {c["chunk_id"]: c for c in chunks}

    e5 = E5(fetch())
    vec_file = VEC_DIR / "vectors.npy"
    if vec_file.is_file() and json.loads((VEC_DIR / "order.json").read_text("utf-8")) == order:
        pv = np.load(vec_file)
    else:
        t0 = time.perf_counter()
        pv = e5.encode(["passage: " + embed_text(by_id[c], titles) for c in order])
        VEC_DIR.mkdir(parents=True, exist_ok=True)
        np.save(vec_file, pv)
        (VEC_DIR / "order.json").write_text(json.dumps(order), encoding="utf-8")
        print(f"e5 passages embedded in {time.perf_counter() - t0:.0f}s")
    e5_index = DenseIndex.build(pv, [by_id[c] for c in order])  # same filters as BGE

    present = {c["section_uid"] for c in chunks}
    rows = []
    for line in GOLDEN.read_text("utf-8").splitlines():
        r = json.loads(line)
        exp = [c["section_uid"] or c["act_id"] for c in r.get("expected_clauses", [])]
        if exp and all(any(lenient(p, e) for p in present) for e in exp):
            r["_exp"] = exp
            rows.append(r)
    scores: dict[tuple[str, str, str], list[Any]] = defaultdict(list)  # (model, match, lang)
    for r in rows:
        q = r["raw_question_redacted"]
        ranked: dict[str, list[str]] = {}
        for name, (idx, emb) in bge.items():
            ranked[name] = [
                h.chunk_id.split("@")[0] for h in idx.search_vector(emb.encode([q])[0], k=K)
            ]
        ranked["e5-fp32"] = [
            h.chunk_id.split("@")[0]
            for h in e5_index.search_vector(e5.encode(["query: " + q])[0], k=K)
        ]
        for name, ids in ranked.items():
            for mname, match in (("strict", strict), ("lenient", lenient)):
                s = score_row(ids, r["_exp"], match, K)
                scores[(name, mname, "all")].append(s)
                scores[(name, mname, r["language"])].append(s)

    langs = ["all", "en", "hi", "hinglish"]
    L = [f"# W1.6 embedding bake-off: BGE-M3 vs multilingual-e5-large ({date.today().isoformat()})", "",
         f"Dense retrieval only, top {K}, {len(rows)} golden rows whose expected provisions are all indexed "
         "(seed set, unverified labels). DEC-004: keep the winner by recall@10 per language (hi, en).", "",
         f"- e5: {REPO} @ {REVISION[:8]} (official ONNX, fp32, mean pooling, 'query: '/'passage: ' prefixes)",
         "- BGE-M3: existing int8 / fp32 indexes (DEC-060/061)", "",
         "| model | match | " + " | ".join(f"R@10 {lg} (n)" for lg in langs) + " | MRR@10 all |",
         "| --- | --- | " + " | ".join("---" for _ in langs) + " | --- |"]  # fmt: skip
    for name in ("bge-int8", "bge-fp32", "e5-fp32"):
        for mname in ("strict", "lenient"):
            cells = []
            for lg in langs:
                sm = summarise(scores[(name, mname, lg)])
                cells.append(f"{sm.recall:.3f} ({sm.rows})")
            L.append(
                f"| {name} | {mname} | "
                + " | ".join(cells)
                + f" | {summarise(scores[(name, mname, 'all')]).mrr:.3f} |"
            )
    out = (
        Path("reports/retrieval") / f"{GOLDEN.parent.name}_{date.today().isoformat()}_bakeoff_e5.md"
    )
    out.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    print("->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
