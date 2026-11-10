"""W0.5 OCR bake-off: pre-fill ground truth and score engines (DEC-014, DEC-053).

Usage:
    uv run python scripts/ocr_score.py prefill  # Tesseract output -> data/ocr_gt/<page_id>.txt
    uv run python scripts/ocr_score.py score    # CER/WER table -> docs/eval/ocr_bakeoff.md

prefill never overwrites an existing ground-truth file. Engine outputs are read from
data/ocr/out/<engine>/<page_id>.(txt|md) (downloaded from the Colab notebook). Only pages
with gt_status == "corrected" are scored, unless --include-drafts is given (dry runs).
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from madhya_kanoon_saathi.eval.ocr_metrics import OcrScores, plain_text, score

GT = Path("data/ocr_gt")
OUT = Path("data/ocr/out")
ENGINES = ("tesseract", "bodhan", "sarvam")


def load_pages() -> tuple[dict, list[dict]]:
    doc = json.loads((GT / "pages.json").read_text(encoding="utf-8"))
    return doc, doc["pages"]


def engine_text(engine: str, page_id: str) -> str | None:
    for ext in ("txt", "md"):
        f = OUT / engine / f"{page_id}.{ext}"
        if f.exists():
            return plain_text(f.read_text(encoding="utf-8"))
    return None


def prefill() -> None:
    doc, pages = load_pages()
    for p in pages:
        gt = GT / f"{p['page_id']}.txt"
        if gt.exists():
            continue
        text = engine_text("tesseract", p["page_id"])
        if text is None:
            print(p["page_id"], "no tesseract output yet")
            continue
        gt.write_text(text + "\n", encoding="utf-8", newline="\n")
        p.setdefault("gt_status", "draft")
        print(p["page_id"], "pre-filled", len(text), "chars")
    (GT / "pages.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _fmt(xs: list[float]) -> str:
    return f"{100 * statistics.fmean(xs):.1f}" if xs else "-"


def score_all(include_drafts: bool, out: Path) -> None:
    _, pages = load_pages()
    rows: dict[str, dict[str, OcrScores]] = defaultdict(dict)
    for p in pages:
        gt = GT / f"{p['page_id']}.txt"
        if not gt.exists() or (p.get("gt_status") != "corrected" and not include_drafts):
            continue
        ref = plain_text(gt.read_text(encoding="utf-8"))  # same conversion as the engines
        for e in ENGINES:
            hyp = engine_text(e, p["page_id"])
            if hyp is not None:
                rows[p["page_id"]][e] = score(ref, hyp)
    kinds = {p["page_id"]: p["kind"] for p in pages}
    langs = {p["page_id"]: p["lang"] for p in pages}

    scope = (
        "incl. uncorrected drafts: NOT FINAL" if include_drafts else "corrected ground truth only"
    )
    lines = [
        "# W0.5 OCR bake-off results",
        "",
        f"Pages scored: {len(rows)} ({scope}).",
        "Mean per-page error rates in %, lower is better. raw = whitespace-collapsed NFC;",
        "norm = shared normaliser (nukta folded, invisible characters removed).",
        "Produced by `scripts/ocr_score.py score`.",
        "",
        "| Slice | Engine | Pages | CER raw | CER norm | WER raw | WER norm |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    slices: dict[str, list[str]] = defaultdict(list)
    for pid in rows:
        slices["all"].append(pid)
        slices[f"lang={langs[pid]}"].append(pid)
        slices[f"kind={kinds[pid]}"].append(pid)
    for sl in sorted(slices, key=lambda s: (s != "all", s)):
        for e in ENGINES:
            sc = [rows[pid][e] for pid in slices[sl] if e in rows[pid]]
            if not sc:
                continue
            vals = [
                _fmt([getattr(s, k) for s in sc])
                for k in ("cer_raw", "cer_norm", "wer_raw", "wer_norm")
            ]
            lines.append(f"| {sl} | {e} | {len(sc)} | " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Per page (CER norm %)",
        "",
        "| Page | Kind | Lang | " + " | ".join(ENGINES) + " |",
        "| --- | --- | --- | " + " | ".join("---" for _ in ENGINES) + " |",
    ]
    for pid in sorted(rows):
        cells = [f"{100 * rows[pid][e].cer_norm:.1f}" if e in rows[pid] else "-" for e in ENGINES]
        lines.append(f"| {pid} | {kinds[pid]} | {langs[pid]} | " + " | ".join(cells) + " |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("prefill", "score"))
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--out", default="docs/eval/ocr_bakeoff.md")
    a = ap.parse_args()
    if a.cmd == "prefill":
        prefill()
    else:
        score_all(a.include_drafts, Path(a.out))


if __name__ == "__main__":
    main()
