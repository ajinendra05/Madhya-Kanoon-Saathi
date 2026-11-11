"""Build data/parsed/chunks.jsonl and the committed build record (W1.1, DEC-055).

Spec: docs/specs/chunks.md.

Usage:
    uv run python scripts/build_chunks.py [--only DOC_ID ...]

- Reads data/corpus_manifest.json; considers documents with mode index or guide.
- Supported now (W1.1a): born-digital English India Code PDFs. Others are listed as unsupported
  in the QA report with the reason (W1.1a remainder: other born-digital layouts and HTML;
  W1.1b: OCR pages).
- Re-checks every input file's sha256 against the manifest (hard error on mismatch).
- Hard QA errors stop the build: nothing is written. Warnings go to the QA report.
- Writes data/parsed/chunks.jsonl (git-ignored) and
  data/parsed_manifest/{build_manifest.json,qa_report.md} (committed).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import platform
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from madhya_kanoon_saathi.common.normalize import NORMALISER_VERSION
from madhya_kanoon_saathi.ingestion.bill_layout import split_margin
from madhya_kanoon_saathi.ingestion.chunker import (
    CHUNKER_VERSION,
    MAX_TOKENS,
    MIN_TOKENS,
    build_chunks,
    qa,
)
from madhya_kanoon_saathi.ingestion.guideline import parse_guideline
from madhya_kanoon_saathi.ingestion.manifest import Document, parse_manifest
from madhya_kanoon_saathi.ingestion.pdf_text import extract
from madhya_kanoon_saathi.ingestion.structure import parse_statute

DATA = Path("data")
OUT = DATA / "parsed" / "chunks.jsonl"
REC = DATA / "parsed_manifest"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# Documents whose layout is known by inspection (DEC-055); everything else is routed by rule.
BILL_LAYOUT = {"IN.MTA2021@en@1"}  # margin-note headings, contents pages (bill_layout.py)
GUIDELINE = {"IN.SVANSG2025@en@1", "IN.SVANLOG2025@en@1"}  # decimal-numbered paragraphs (DEC-057)


def route(doc: Document) -> str | None:
    """Return the parser name for a document, or None with the reason recorded by the caller."""
    if doc.doc_id in BILL_LAYOUT and doc.text_layer == "born_digital":
        return "bill_layout"
    if doc.doc_id in GUIDELINE and doc.text_layer in ("born_digital", "mixed"):
        return "guideline"  # mixed: image-only annexure pages are reported as low-text pages
    if (
        doc.content_type == "application/pdf"
        and doc.text_layer == "born_digital"
        and doc.language == "en"
        and "indiacode.nic.in/bitstream" in doc.source_url
    ):
        return "india_code"
    return None


def unsupported_reason(doc: Document) -> str:
    if doc.text_layer in ("scanned", "mixed"):
        return f"{doc.text_layer} text layer: needs OCR (W1.1b)"
    if doc.content_type.startswith("text/html"):
        return "HTML guide: parser to do (W1.1a remainder)"
    return "born-digital layout other than India Code: parser to do (W1.1a remainder)"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()

    manifest, merrors = parse_manifest(
        json.loads((DATA / "corpus_manifest.json").read_text(encoding="utf-8"))
    )
    if manifest is None or merrors:
        print("manifest invalid:", *merrors, sep="\n  ")
        return 1
    docs = [d for d in manifest.documents.values() if d.mode in ("index", "guide")]
    if a.only:
        docs = [d for d in docs if d.doc_id in set(a.only)]

    errors: list[str] = []
    per_doc: dict[str, dict] = {}
    unsupported: dict[str, str] = {}
    chunks = []
    inputs = []
    for doc in sorted(docs, key=lambda d: d.doc_id):
        kind = route(doc)
        if kind is None:
            unsupported[doc.doc_id] = unsupported_reason(doc)
            continue
        path = DATA / (doc.local_path or "")
        if not path.is_file():
            errors.append(f"{doc.doc_id}: file missing at {path}")
            continue
        digest = sha256(path)
        if digest != doc.sha256:
            errors.append(f"{doc.doc_id}: sha256 {digest[:12]} != manifest {doc.sha256[:12]}")
            continue
        inputs.append({"doc_id": doc.doc_id, "sha256": digest, "local_path": doc.local_path})
        inst = manifest.instruments[doc.instrument_id]
        text = extract(path)
        if kind == "bill_layout":
            split = split_margin(text.lines)
            parsed = parse_statute(doc.instrument_id, split.lines, margin_headings=True)
            for u in parsed.units:
                if u.kind == "section":
                    u.heading = split.headings.get(u.label, "")
            if any(u.kind == "section" and not u.heading for u in parsed.units):
                errors.append(f"{doc.doc_id}: section without a heading from the contents pages")
        elif kind == "guideline":
            parsed = parse_guideline(doc.instrument_id, text.lines)
        else:
            parsed = parse_statute(doc.instrument_id, text.lines)
        res = qa(
            build_chunks(parsed, doc, inst, text.footnotes, f"pdfium-{md.version('pypdfium2')}"),
            text.page_chars,
        )
        errors += [f"{doc.doc_id}: {e}" for e in res.errors]
        toks = [c.token_estimate for c in res.chunks]
        per_doc[doc.doc_id] = {
            "parser": kind,
            "chunks": len(res.chunks),
            "sections": sum(1 for u in parsed.units if u.kind == "section"),
            "tokens": {
                "below_min": sum(t < MIN_TOKENS for t in toks),
                "in_range": sum(MIN_TOKENS <= t <= MAX_TOKENS for t in toks),
                "above_max": sum(t > MAX_TOKENS for t in toks),
            },
            "warnings": [w for w in res.warnings if "token_estimate" not in w],
            "skipped": res.skipped,
            "state_amendment_blocks": len(parsed.state_amendments),
            "state_amendment_blocks_mp": sum(s.mentions_mp for s in parsed.state_amendments),
            "unassigned_lines": len(parsed.unassigned),
            "trailing_lines": len(parsed.trailing),
            "footnotes": len(text.footnotes),
        }
        chunks += res.chunks

    if errors:
        print(f"BUILD FAILED: {len(errors)} hard QA error(s); nothing written")
        for e in errors[:50]:
            print("  ", e)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for c in chunks:
            f.write(json.dumps(c.to_json(), ensure_ascii=False, sort_keys=True) + "\n")
    out_sha = sha256(OUT)

    REC.mkdir(parents=True, exist_ok=True)
    record = {
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "python": platform.python_version(),
        "libraries": {p: md.version(p) for p in ("pypdfium2", "pypdf")},
        "normaliser_version": NORMALISER_VERSION,
        "chunker_version": CHUNKER_VERSION,
        "inputs": inputs,
        "output": {
            "path": str(OUT.as_posix()),
            "sha256": out_sha,
            "chunks": len(chunks),
            "by_doc": dict(Counter(c.doc_id for c in chunks)),
        },
        "qa": {"errors": 0, "warnings": sum(len(v["warnings"]) for v in per_doc.values())},
        "unsupported": unsupported,
    }
    (REC / "build_manifest.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (REC / "qa_report.md").write_text(qa_report(record, per_doc), encoding="utf-8", newline="\n")
    print(
        f"built {len(chunks)} chunks from {len(inputs)} documents -> {OUT} (sha256 {out_sha[:12]})"
    )
    print(f"unsupported for now: {len(unsupported)} documents (see qa_report.md)")
    return 0


def qa_report(record: dict, per_doc: dict[str, dict]) -> str:
    L = [
        "# Chunk build QA report",
        "",
        f"Built {record['built_at']} from commit `{record['git_commit'][:10]}`"
        f"{' (uncommitted changes)' if record['git_dirty'] else ''}; "
        f"chunker v{record['chunker_version']}, normaliser v{record['normaliser_version']}. "
        f"Output sha256 `{record['output']['sha256'][:16]}`.",
        "",
        "Hard QA errors: **0** (the build stops on any). Token counts are estimates until W1.4.",
        "",
        f"| Document | Sections | Chunks | < {MIN_TOKENS} | in range | > {MAX_TOKENS} "
        "| Footnotes | "
        "State-amendment blocks (MP) | Skipped | Unassigned lines | Appended Bill lines |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for doc_id, v in per_doc.items():
        t = v["tokens"]
        L.append(
            f"| {doc_id} | {v['sections']} | {v['chunks']} | {t['below_min']} | {t['in_range']} "
            f"| {t['above_max']} | {v['footnotes']} "
            f"| {v['state_amendment_blocks']} ({v['state_amendment_blocks_mp']}) "
            f"| {len(v['skipped'])} | {v['unassigned_lines']} | {v['trailing_lines']} |"
        )
    L += ["", "## Warnings and skipped units", ""]
    for doc_id, v in per_doc.items():
        if v["warnings"] or v["skipped"]:
            L.append(f"### {doc_id}")
            L += [f"- warning: {w}" for w in v["warnings"]]
            L += [f"- skipped: {s}" for s in v["skipped"]]
            L.append("")
    L += ["## Not chunked yet", "", "| Document | Reason |", "| --- | --- |"]
    L += [f"| {d} | {r} |" for d, r in sorted(record["unsupported"].items())]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
