"""Save the int8 reranker after ONNX Runtime graph optimisation (B3, docs/RERANKER.md, DEC-090).

    uv run python scripts/optimize_reranker.py

ONNX Runtime optimises a model's graph every time a session starts (constant folding, operator
fusion). Saving the optimised graph once lets each container start skip that work. Level
ORT_ENABLE_EXTENDED is used, not ORT_ENABLE_ALL: the "all" level adds layout changes tied to the
machine that ran it, and the file must also run on Cloud Run's CPUs.

Writes data/models/bge-reranker-v2-m3-int8-opt/<revision>/model.int8.opt.onnx (+ tokenizer), checks
that its scores match the plain int8 model on sample pairs, and records sha256s and the check in
data/parsed_manifest/models.json under "bge-reranker-v2-m3-int8-opt".
"""

from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

from madhya_kanoon_saathi.retrieval.reranker import Reranker

RECORD = Path("data/parsed_manifest/models.json")
SRC_ENTRY, OUT_ENTRY = "bge-reranker-v2-m3-int8", "bge-reranker-v2-m3-int8-opt"
PAIRS_Q = "मुफ्त कानूनी सहायता कौन ले सकता है?"
PASSAGES = [
    "The landlord shall not cut off or withhold any of the essential supplies or services",
    "12. Criteria for giving legal services.—Every person who has to file or defend a case "
    "shall be entitled to legal services under this Act if that person is a member of a "
    "Scheduled Caste or Scheduled Tribe",
    "Every public authority shall maintain all its records duly catalogued and indexed",
    "A complaint may be filed by a consumer to whom goods are sold or delivered",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    src = record[SRC_ENTRY]
    src_dir = Path(src["dir"])
    for f in src["files"]:
        if sha256(src_dir / f["file"]) != f["sha256"]:
            print(f"checksum mismatch: {f['file']}")
            return 1
    out_dir = Path(f"data/models/{OUT_ENTRY}") / src["revision"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "model.int8.opt.onnx"
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
    opts.optimized_model_filepath = str(out)
    ort.InferenceSession(str(src_dir / "model.int8.onnx"), opts, providers=["CPUExecutionProvider"])
    for tok in ("tokenizer.json", "tokenizer_config.json"):
        shutil.copy2(src_dir / tok, out_dir / tok)
    files = [
        {"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in sorted(out_dir.iterdir())
    ]
    record[OUT_ENTRY] = {
        "from": SRC_ENTRY,
        "revision": src["revision"],
        "method": "onnxruntime SessionOptions.optimized_model_filepath, ORT_ENABLE_EXTENDED",
        "onnxruntime": md.version("onnxruntime"),
        "dir": out_dir.as_posix(),
        "files": files,
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")

    plain = Reranker.load("int8").score(PAIRS_Q, PASSAGES)
    opt = Reranker.load("int8-opt").score(PAIRS_Q, PASSAGES)
    diff = float(np.max(np.abs(plain - opt)))
    same_order = list(np.argsort(-plain)) == list(np.argsort(-opt))
    record[OUT_ENTRY]["check"] = {
        "pairs": len(PASSAGES),
        "max_abs_diff_vs_int8": diff,
        "same_order": same_order,
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    for f in files:
        print(f["file"], f["bytes"], f["sha256"][:12])
    print(f"max |score diff| vs int8 = {diff:.2e}; same order: {same_order}")
    return 0 if same_order and diff < 1e-3 else 1


if __name__ == "__main__":
    sys.exit(main())
