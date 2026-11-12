"""Download the pinned BGE-M3 ONNX files (DEC-060) and record their sha256.

Usage:
    uv run python scripts/fetch_models.py

Files go to data/models/bge-m3/<revision>/ (git-ignored). A committed record
(data/parsed_manifest/models.json) lists every file with its size and sha256; the embedder
refuses to run on files whose sha256 differs (DEC-022 checksum pinning).
The model is public and not gated: no token is needed or read.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO = "BAAI/bge-m3"
REVISION = "5617a9f61b028005a4858fdac845db406aefb181"  # pinned, checked 2026-11-12
FILES = [
    "onnx/model.onnx",
    "onnx/model.onnx_data",
    "onnx/Constant_7_attr__value",
    "onnx/config.json",
    "onnx/tokenizer.json",
    "onnx/tokenizer_config.json",
    "onnx/special_tokens_map.json",
    "onnx/sentencepiece.bpe.model",
]
DEST = Path("data/models/bge-m3") / REVISION
RECORD = Path("data/parsed_manifest/models.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    entries = []
    for name in FILES:
        local = Path(hf_hub_download(REPO, name, revision=REVISION, local_dir=DEST))
        entries.append({"file": name, "bytes": local.stat().st_size, "sha256": sha256(local)})
        print(name, entries[-1]["bytes"], entries[-1]["sha256"][:12], flush=True)
    record = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}
    record["bge-m3-fp32"] = {
        "repo": REPO,
        "revision": REVISION,
        "licence": "MIT",
        "dir": DEST.as_posix(),
        "files": entries,
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
