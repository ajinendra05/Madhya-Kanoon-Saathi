"""Pack the scanned/mixed corpus PDFs for the bulk Bodhan OCR run on Colab (W1.2, DEC-001/015/053).

Selects manifest documents with mode index or gated and text_layer scanned or mixed, copies the
PDFs (not rendered pages: ~50x smaller to upload) and writes jobs.json with sha256 and page
counts. The Colab notebook renders pages with the same pypdfium2 version as `uv.lock` at
300 dpi (as in the bake-off) and checks every sha256 before OCR.

    uv run python scripts/prepare_ocr_bulk.py [--out data/ocr/bulk] [--parts 2]

Output: <out>/mks_ocr_bulk/{jobs.json, pdfs/*.pdf} and <out>/mks_ocr_bulk.zip (upload the
unzipped folder to Google Drive root). Index-mode documents come first, the largest gated
document (MPLRC Hindi consolidation) last, so a short session still covers what is indexed.
With --parts N the ordered job list is cut into N packages of about equal page count
(<out>/mks_ocr_bulk_p1 ... _pN, each with its own jobs.json and zip), so each part fits in one
GPU session. A document larger than one share is split by page range: its job carries `first`
and `last` (1-based, inclusive) and outputs keep the original page numbers, so parts merge by
(doc_id, page).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium

DATA = Path("data")
DPI = 300  # same as the W0.5 bake-off pages


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def split_by_pages(jobs: list[dict[str, Any]], parts: int) -> list[list[dict[str, Any]]]:
    """Cut the ordered pages of all jobs into `parts` contiguous runs of near-equal size.

    Page g (0-based, across all jobs in order) goes to part g * parts // total, so part sizes
    differ by at most one page. A job crossing a boundary becomes one slice per part, each with
    its own `first`/`last` page range.
    """
    total = sum(j["pages"] for j in jobs)
    groups: list[list[dict[str, Any]]] = [[] for _ in range(min(parts, total))]
    g = 0
    for j in jobs:
        n = 1
        while n <= j["pages"]:
            k = g * len(groups) // total
            # last global page index (exclusive) that still belongs to part k
            end = -(-(k + 1) * total // len(groups))
            take = min(j["pages"] - n + 1, end - g)
            groups[k].append({**j, "first": n, "last": n + take - 1})
            n += take
            g += take
    return groups


def write_package(out: Path, name: str, jobs: list[dict[str, Any]], part: tuple[int, int]) -> None:
    root = out / name
    # rebuild inputs from scratch; never touch root/"out" (downloaded OCR results)
    if (root / "pdfs").exists():
        shutil.rmtree(root / "pdfs")
    (root / "pdfs").mkdir(parents=True)
    for j in jobs:
        if not (root / j["file"]).exists():
            shutil.copyfile(j["_src"], root / j["file"])
    info = {
        "package": name,
        "part": part[0],
        "parts": part[1],
        "dpi": DPI,
        "renderer": f"pypdfium2=={version('pypdfium2')}",
        "total_pages": sum(j["last"] - j["first"] + 1 for j in jobs),
        "jobs": [{k: v for k, v in j.items() if k != "_src"} for j in jobs],
    }
    (root / "jobs.json").write_text(
        json.dumps(info, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    zpath = out / f"{name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(root.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(out).as_posix())
    print(f"== {name}")
    for j in jobs:
        rng = f"pp.{j['first']}-{j['last']}"
        print(f"{j['mode']:6s} {j['last'] - j['first'] + 1:4d}p  {j['doc_id']} {rng}")
    mb = zpath.stat().st_size / 1e6
    print(f"{len(jobs)} documents, {info['total_pages']} pages -> {zpath} ({mb:.1f} MB)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DATA / "ocr" / "bulk")
    ap.add_argument("--parts", type=int, default=1, help="split into N packages by page count")
    a = ap.parse_args()
    if a.parts < 1:
        raise SystemExit("--parts must be >= 1")

    manifest = json.loads((DATA / "corpus_manifest.json").read_text(encoding="utf-8"))
    docs = [
        d
        for d in manifest["documents"]
        if d["mode"] in ("index", "gated") and d.get("text_layer") in ("scanned", "mixed")
    ]
    jobs = []
    for d in docs:
        src = DATA / d["local_path"]
        digest = sha256(src)
        if digest != d["sha256"]:
            raise SystemExit(f"{d['doc_id']}: file sha256 differs from the manifest")
        pdf = pdfium.PdfDocument(str(src))
        pages = len(pdf)
        pdf.close()
        jobs.append(
            {
                "doc_id": d["doc_id"],
                "file": f"pdfs/{d['doc_id'].replace('@', '_')}.pdf",
                "sha256": digest,
                "pages": pages,
                "language": d["language"],
                "mode": d["mode"],
                "text_layer": d["text_layer"],
                "_src": src,
            }
        )
    # index first, then gated; smaller first inside each group
    jobs.sort(key=lambda j: (j["mode"] != "index", j["pages"]))
    groups = split_by_pages(jobs, a.parts)
    for i, group in enumerate(groups, 1):
        name = "mks_ocr_bulk" if a.parts == 1 else f"mks_ocr_bulk_p{i}"
        write_package(a.out, name, group, part=(i, a.parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
