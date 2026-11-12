"""Embed all chunks with BGE-M3 and build the exact FAISS index (W1.4, DEC-021/022/025/060).

Usage:
    uv run python scripts/build_dense.py int8      # or fp32

Writes (git-ignored) data/index/dense-<variant>/{vectors.faiss, chunks.jsonl, vectors.npy} and
(committed) data/parsed_manifest/dense_<variant>_build.json plus the parity reference
data/parsed_manifest/parity_<variant>.json: vectors of three fixed sentences, which
tests/unit/test_embedder_parity.py re-computes in any environment (DEC-022).
"""

from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
from madhya_kanoon_saathi.retrieval.embedder import EMBED_FORMAT, Embedder, embed_text

SRC = Path("data/parsed/chunks.jsonl")
REC_DIR = Path("data/parsed_manifest")
RECORD_EXCLUDE = ":!data/parsed_manifest"
PARITY_SENTENCES = [
    "Every public authority shall maintain all its records duly catalogued and indexed.",
    "सूचना का अधिकार अधिनियम की धारा 8(1)(j) के अंतर्गत व्यक्तिगत सूचना",
    "eshram registration ke liye kya documents chahiye",
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def main() -> int:
    variant = sys.argv[1] if len(sys.argv) > 1 else "int8"
    raw = SRC.read_bytes()
    chunks = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
    emb = Embedder.load(variant)
    t0 = time.time()
    manifest = json.loads(Path("data/corpus_manifest.json").read_text(encoding="utf-8"))
    titles = {
        i["instrument_id"]: (i.get("title_en"), i.get("title_hi")) for i in manifest["instruments"]
    }
    vecs = emb.encode([embed_text(c, titles) for c in chunks])
    seconds = time.time() - t0
    out = Path(f"data/index/dense-{variant}")
    DenseIndex.build(vecs, chunks).save(out)
    np.save(out / "vectors.npy", vecs)
    parity = emb.encode(PARITY_SENTENCES)
    (REC_DIR / f"parity_{variant}.json").write_text(
        json.dumps(
            {
                "variant": variant,
                "sentences": PARITY_SENTENCES,
                "vectors": np.round(parity, 7).tolist(),
            }
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    models = json.loads((REC_DIR / "models.json").read_text(encoding="utf-8"))
    key = "bge-m3-fp32" if variant == "fp32" else "bge-m3-int8"
    record = {
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(
            git("status", "--porcelain", "--untracked-files=no", "--", ".", RECORD_EXCLUDE)
        ),
        "variant": variant,
        "model": {"key": key, "files": models[key]["files"]},
        "input": {
            "path": SRC.as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "chunks": len(chunks),
        },
        "text_embedded": EMBED_FORMAT,
        "max_length": emb.max_length,
        "truncated": emb.last_stats.truncated,
        "seconds": round(seconds, 1),
        "ms_per_chunk": round(seconds / len(chunks) * 1000, 1),
        "machine": {
            "python": platform.python_version(),
            "cpu": platform.processor(),
            "os": platform.platform(),
        },
        "libraries": {
            p: md.version(p) for p in ("onnxruntime", "tokenizers", "faiss-cpu", "numpy")
        },
        "output": out.as_posix(),
    }
    (REC_DIR / f"dense_{variant}_build.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        f"{variant}: {len(chunks)} chunks in {seconds:.0f}s, "
        f"truncated {emb.last_stats.truncated} -> {out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
