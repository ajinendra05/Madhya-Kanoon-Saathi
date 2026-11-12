"""Make the int8 BGE-M3 ONNX from BAAI's fp32 export (DEC-021, DEC-060).

Usage:
    uv run python scripts/quantize_bge_m3.py

- Refuses to run unless every fp32 file matches the sha256 recorded by scripts/fetch_models.py.
- onnxruntime dynamic quantization, QInt8 weights (per-tensor), all supported operators.
- Writes data/models/bge-m3-int8/<revision>/model.int8.onnx (+ tokenizer files copied) and adds a
  "bge-m3-int8" entry with sha256s to data/parsed_manifest/models.json.
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
TOKENIZER_FILES = (
    "onnx/tokenizer.json",
    "onnx/tokenizer_config.json",
    "onnx/special_tokens_map.json",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    fp32 = record["bge-m3-fp32"]
    src = Path(fp32["dir"])
    for f in fp32["files"]:
        if sha256(src / f["file"]) != f["sha256"]:
            print(f"checksum mismatch: {f['file']}; re-run scripts/fetch_models.py")
            return 1
    out_dir = Path("data/models/bge-m3-int8") / fp32["revision"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "model.int8.onnx"
    quantize_dynamic(src / "onnx/model.onnx", out, weight_type=QuantType.QInt8)
    for name in TOKENIZER_FILES:
        shutil.copy2(src / name, out_dir / Path(name).name)
    files = [
        {"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)}
        for p in sorted(out_dir.iterdir())
    ]
    record["bge-m3-int8"] = {
        "from": "bge-m3-fp32",
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
    sys.exit(main())
