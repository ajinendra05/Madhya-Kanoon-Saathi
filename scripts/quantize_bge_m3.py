"""Make int8 ONNX models from the fp32 ones (DEC-021, DEC-060, DEC-062).

Usage:
    uv run python scripts/quantize_bge_m3.py            # embedder (BAAI/bge-m3)
    uv run python scripts/quantize_bge_m3.py reranker   # BAAI/bge-reranker-v2-m3

- Refuses to run unless every fp32 file matches its recorded sha256 (embedder: written by
  scripts/fetch_models.py; reranker: export_info.json from notebooks/reranker_export_colab.ipynb,
  copied into data/parsed_manifest/models.json on first run).
- onnxruntime dynamic quantization, QInt8 weights (per-tensor), all supported operators.
- Writes data/models/<name>-int8/<revision>/model.int8.onnx (+ tokenizer files copied) and adds a
  "<name>-int8" entry with sha256s to data/parsed_manifest/models.json.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import shutil
import sys
from pathlib import Path

from onnxruntime.quantization import QuantType, quantize_dynamic

RECORD = Path("data/parsed_manifest/models.json")
MODELS = {
    "embedder": (
        "bge-m3",
        "onnx/model.onnx",
        ("onnx/tokenizer.json", "onnx/tokenizer_config.json", "onnx/special_tokens_map.json"),
    ),
    "reranker": ("bge-reranker-v2-m3", "model.onnx", ("tokenizer.json", "tokenizer_config.json")),
}
RERANKER_EXPORT = Path("data/models/bge-reranker-v2-m3")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def register_reranker_export(record: dict) -> None:
    """Copy the Colab export_info.json into the models record (once)."""
    if "bge-reranker-v2-m3-fp32" in record:
        return
    info = json.loads((RERANKER_EXPORT / "export_info.json").read_text(encoding="utf-8"))
    record["bge-reranker-v2-m3-fp32"] = {
        "repo": info["repo"],
        "revision": info["revision"],
        "licence": info["licence"],
        "exported": info["exported"],
        "export_versions": info["versions"],
        "export_check": info["check"],
        "dir": RERANKER_EXPORT.as_posix(),
        "files": info["files"],
    }


def main(argv: list[str]) -> int:
    which = argv[0] if argv else "embedder"
    if which not in MODELS:
        print(f"unknown model {which!r}; choose from {sorted(MODELS)}")
        return 2
    name, model_file, tokenizer_files = MODELS[which]
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    if which == "reranker":
        register_reranker_export(record)
    fp32 = record[f"{name}-fp32"]
    src = Path(fp32["dir"])
    for f in fp32["files"]:
        if sha256(src / f["file"]) != f["sha256"]:
            print(f"checksum mismatch: {f['file']}; re-download the fp32 files")
            return 1
    out_dir = Path(f"data/models/{name}-int8") / fp32["revision"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "model.int8.onnx"
    quantize_dynamic(src / model_file, out, weight_type=QuantType.QInt8)
    for tok in tokenizer_files:
        shutil.copy2(src / tok, out_dir / Path(tok).name)
    files = [
        {"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in sorted(out_dir.iterdir())
    ]
    record[f"{name}-int8"] = {
        "from": f"{name}-fp32",
        "revision": fp32["revision"],
        "method": "onnxruntime.quantization.quantize_dynamic, QuantType.QInt8, per-tensor",
        "onnxruntime": md.version("onnxruntime"),
        "dir": out_dir.as_posix(),
        "files": files,
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    for f in files:
        print(f["file"], f["bytes"], f["sha256"][:12])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
