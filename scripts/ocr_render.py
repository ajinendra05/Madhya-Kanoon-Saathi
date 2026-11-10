"""Render the W0.5 OCR bake-off pages (DEC-053) to PNG and optionally a contact sheet.

Usage:
    uv run python scripts/ocr_render.py data/ocr_gt/pages.json OUT_DIR [--sheet S.png] [--dpi 300]

`pages.json` = {"pages": [{"page_id", "doc_id", "page" (1-based), "kind", "lang", "why"}]}.
The PDF path comes from the manifest's `local_path` under MKS_DATA_DIR (default ./data).
Output: OUT_DIR/<page_id>.png.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages")
    ap.add_argument("out_dir")
    ap.add_argument("--sheet")
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()

    data_dir = Path(os.environ.get("MKS_DATA_DIR", "data"))
    manifest = json.loads((data_dir / "corpus_manifest.json").read_text(encoding="utf-8"))
    paths = {
        d["doc_id"]: data_dir / d["local_path"] for d in manifest["documents"] if "local_path" in d
    }
    pages = json.loads(Path(a.pages).read_text(encoding="utf-8"))["pages"]
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    thumbs = []
    for p in pages:
        pdf = pdfium.PdfDocument(paths[p["doc_id"]])
        img = pdf[p["page"] - 1].render(scale=a.dpi / 72).to_pil().convert("RGB")
        img.save(out / f"{p['page_id']}.png")
        print(p["page_id"], img.size)
        if a.sheet:
            t = img.copy()
            t.thumbnail((360, 500))
            ImageDraw.Draw(t).text((5, 5), p["page_id"], fill=(255, 0, 0))
            thumbs.append(t)
        pdf.close()

    if a.sheet and thumbs:
        cols = 5
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 360, rows * 500), "white")
        for i, t in enumerate(thumbs):
            sheet.paste(t, ((i % cols) * 360, (i // cols) * 500))
        sheet.save(a.sheet)


if __name__ == "__main__":
    main()
