"""Pack the scanned/mixed corpus PDFs for the bulk Bodhan OCR run on Colab (W1.2, DEC-001/015/053).

Selects manifest documents with mode index or gated and text_layer scanned or mixed, copies the
PDFs (not rendered pages: ~50x smaller to upload) and writes jobs.json with sha256 and page
counts. The Colab notebook renders pages with the same pypdfium2 version as `uv.lock` at
300 dpi (as in the bake-off) and checks every sha256 before OCR.

    uv run python scripts/prepare_ocr_bulk.py [--out data/ocr/bulk]

Output: <out>/mks_ocr_bulk/{jobs.json, pdfs/*.pdf} and <out>/mks_ocr_bulk.zip (upload the
unzipped folder to Google Drive root). Index-mode documents come first, the largest gated
document (MPLRC Hindi consolidation) last, so a short session still covers what is indexed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from importlib.metadata import version
from pathlib import Path

import pypdfium2 as pdfium

DATA = Path("data")
DPI = 300  # same as the W0.5 bake-off pages


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DATA / "ocr" / "bulk")
    a = ap.parse_args()

    manifest = json.loads((DATA / "corpus_manifest.json").read_text(encoding="utf-8"))
    docs = [
        d
        for d in manifest["documents"]
        if d["mode"] in ("index", "gated") and d.get("text_layer") in ("scanned", "mixed")
    ]
    root = a.out / "mks_ocr_bulk"
    (root / "pdfs").mkdir(parents=True, exist_ok=True)
    jobs = []
    for d in docs:
        src = DATA / d["local_path"]
        digest = sha256(src)
        if digest != d["sha256"]:
            raise SystemExit(f"{d['doc_id']}: file sha256 differs from the manifest")
        pdf = pdfium.PdfDocument(str(src))
        pages = len(pdf)
        pdf.close()
        name = f"{d['doc_id'].replace('@', '_')}.pdf"
        shutil.copyfile(src, root / "pdfs" / name)
        jobs.append(
            {
                "doc_id": d["doc_id"],
                "file": f"pdfs/{name}",
                "sha256": digest,
                "pages": pages,
                "language": d["language"],
                "mode": d["mode"],
                "text_layer": d["text_layer"],
            }
        )
    # index first, then gated; smaller first inside each group
    jobs.sort(key=lambda j: (j["mode"] != "index", j["pages"]))
    info = {
        "dpi": DPI,
        "renderer": f"pypdfium2=={version('pypdfium2')}",
        "total_pages": sum(j["pages"] for j in jobs),
        "jobs": jobs,
    }
    (root / "jobs.json").write_text(
        json.dumps(info, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    zpath = a.out / "mks_ocr_bulk.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(root.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(a.out).as_posix())
    for j in jobs:
        print(f"{j['mode']:6s} {j['pages']:4d}p  {j['doc_id']}")
    mb = zpath.stat().st_size / 1e6
    print(f"{len(jobs)} documents, {info['total_pages']} pages -> {zpath} ({mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
