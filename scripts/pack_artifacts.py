"""Pack the git-ignored runtime files into release archives for `mks-artifacts` (DEC-085, DEC-086).

    uv run python scripts/pack_artifacts.py <out_dir> <release_tag>

Writes ``models-int8.tar`` and ``index.tar`` (paths relative to the repo root, so CI extracts them
in place), with fixed order, timestamps and owners so the same inputs give the same bytes. Each
model file's sha256 is checked against ``data/parsed_manifest/models.json`` before packing.
Records archive names, sizes and sha256 in ``data/artifacts.json`` (committed); the build refuses
an archive whose checksum differs.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tarfile
from pathlib import Path

GROUPS = {
    "models-int8.tar": ["data/models/bge-m3-int8", "data/models/bge-reranker-v2-m3-int8"],
    "index.tar": [
        "data/index/bm25",
        "data/index/dense-int8",
        "data/parsed/chunks.jsonl",
        "data/parsed_manifest/models.json",
    ],
}
MODEL_KEYS = ("bge-m3-int8", "bge-reranker-v2-m3-int8")
RECORD = Path("data/artifacts.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def files_of(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for p in map(Path, paths):
        out += sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p]
    return sorted(out, key=lambda x: x.as_posix())


def check_models() -> None:
    record = json.loads(Path("data/parsed_manifest/models.json").read_text("utf-8"))
    for key in MODEL_KEYS:
        folder = Path(record[key]["dir"])
        for f in record[key]["files"]:
            if sha256(folder / f["file"]) != f["sha256"]:
                raise SystemExit(f"checksum mismatch: {folder / f['file']}")


def pack(name: str, paths: list[str], out: Path) -> dict[str, object]:
    target = out / name
    with tarfile.open(target, "w", format=tarfile.PAX_FORMAT) as tar:
        for f in files_of(paths):
            info = tar.gettarinfo(str(f), arcname=f.as_posix())
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            info.mode = 0o644
            with f.open("rb") as fh:
                tar.addfile(info, fh)
    return {"file": name, "bytes": target.stat().st_size, "sha256": sha256(target)}


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    out, tag = Path(sys.argv[1]), sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    check_models()
    assets = [pack(name, paths, out) for name, paths in GROUPS.items()]
    RECORD.write_text(
        json.dumps(
            {
                "repo": "ajinendra05/mks-artifacts",
                "tag": tag,
                "note": "Git-ignored runtime files for the Cloud Run image (DEC-085/086); "
                "made by scripts/pack_artifacts.py, checked by the build.",
                "assets": assets,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    for a in assets:
        print(f"{a['file']}: {a['bytes']:,} bytes sha256 {a['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
