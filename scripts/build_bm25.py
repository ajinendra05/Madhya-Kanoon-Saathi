"""Build the BM25 index from data/parsed/chunks.jsonl (W1.3, DEC-058).

Usage:
    uv run python scripts/build_bm25.py

Writes the index to data/index/bm25/ (git-ignored) and a committed build record to
data/parsed_manifest/bm25_build.json: input chunks sha256, chunk count, vocabulary size,
parameters, library versions and the git commit.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from madhya_kanoon_saathi.retrieval.bm25_index import K1, B, Bm25Index

SRC = Path("data/parsed/chunks.jsonl")
OUT = Path("data/index/bm25")
REC = Path("data/parsed_manifest/bm25_build.json")
RECORD_EXCLUDE = (
    ":!data/parsed_manifest"  # git pathspec: build records do not count as code changes
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def main() -> int:
    raw = SRC.read_bytes()
    chunks = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
    index = Bm25Index.build(chunks)
    index.save(OUT)
    record = {
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(
            git("status", "--porcelain", "--untracked-files=no", "--", ".", RECORD_EXCLUDE)
        ),
        "input": {
            "path": SRC.as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "chunks": len(chunks),
        },
        "params": {"method": "lucene", "k1": K1, "b": B},
        "vocab_size": index.vocab_size,
        "libraries": {p: md.version(p) for p in ("bm25s", "numpy")},
        "output": OUT.as_posix(),
    }
    REC.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"indexed {len(chunks)} chunks, vocabulary {index.vocab_size} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
