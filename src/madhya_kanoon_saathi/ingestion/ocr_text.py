"""Lines from Bodhan IndicOCR page outputs (W1.1b, DEC-053/069/071). Spec: ``docs/specs/chunks.md``.

Input: the bulk run's per-page markdown, ``<root>/**/out/<doc folder>/pNNNN.md`` (``<doc folder>``
is the doc_id with ``@`` replaced by ``_``). Parts may sit at ``<root>/<pkg>/out`` or, after a
Windows "extract to folder", at ``<root>/<pkg>_out/<pkg>/out``; pages are merged by page number.

Output: :class:`OcrDoc` with :class:`~madhya_kanoon_saathi.ingestion.pdf_text.Line` objects per
language, so the statute parser runs on OCR text unchanged.

- ``raw`` line text is Bodhan's text **unchanged** (U+2581 word marks, HTML table tags and dot
  leaders included, DEC-055 7a). The cleanup happens in ``chunker.canonicalise`` when the chunk's
  ``raw_map`` carries ``"ocr": [1]``.
- Gazette running heads (page numbers, "THE GAZETTE OF INDIA", "मध्यप्रदेश राजपत्र, दिनांक …",
  "[PART II—SEC. 3(i)]") in the first lines of a page, and a bare page number as the last line,
  are ``header`` lines: never chunked.
- Each body line is tagged Hindi or English by its letters (Devanagari share); lines without
  letters ("(1)", "2019") take the language of the line before. Bilingual gazettes thus split into
  one line list per language.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from madhya_kanoon_saathi.ingestion.pdf_text import Line

SP_MARK = "▁"  # SentencePiece word marker Bodhan leaves instead of spaces (TOOLS.md)
HEAD_WINDOW = 5  # running heads are looked for in the first lines of a page
# page numbers: "6", "226 (74)", "५." (Devanagari digits), "$$3$$"
_PAGE_NO = re.compile(r"^\$*\s*[\d०-९]{1,4}\s*(\([\d०-९]{1,4}\))?\s*\.?\s*\$*$")  # noqa: RUF001
_RULE_LINE = re.compile(r"^[_\-—\s]{3,}$")  # "______"
_HEAD = re.compile(
    r"(THE\s+GAZETTE\s+OF\s+INDIA|भारत\s+का\s+राजपत्र|मध्यप्रदेश\s+राजपत्र|"
    r"PART\s+[IVX]+\s*[—–-]\s*SEC|भाग\s+[IVX\d]+\s*[—–-]?\s*(खण्ड|\(ग\)|\(\S{1,3}\)))",  # noqa: RUF001
    re.I,
)
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN = re.compile(r"[A-Za-z]")
_ROW_START = re.compile(r"^\s*(\||<tr\b)")  # markdown or HTML table row
_TAG = re.compile(r"</?[A-Za-z][^<>]{0,200}>")
# the model describing a picture or reading a scanner watermark, not printed law text
# (MP.MWVDAOCT2026@hi@1 p.1: "The image contains a symbol ...", "Scanned with OKEN Scanner")
MODEL_NOTE = re.compile(r"^\s*(The\s+image\s+(contains|shows|depicts)|Scanned\s+with\b)", re.I)


def model_notes(lines: list[Line]) -> list[str]:
    """QA warnings for lines that look like model notes rather than source text."""
    return [
        f"p.{ln.page}: model note? {decode(ln.text)[:60]!r}"
        for ln in lines
        if MODEL_NOTE.match(decode(ln.text))
    ]


@dataclass
class OcrDoc:
    engine: str  # "ocr:bodhan@<revision>"
    pages: dict[int, str]  # page number -> raw markdown
    lines: dict[str, list[Line]] = field(default_factory=dict)  # "en" / "hi" -> body lines
    page_chars: dict[int, int] = field(default_factory=dict)  # visible chars per page (decoded)
    corrections: int = 0  # recorded human fixes applied (data/ocr_corrections.json)


def find_pages(root: Path, doc_id: str) -> tuple[dict[int, Path], set[str]]:
    """Page files for one document across all parts, and the Bodhan revisions that made them.

    Raises ValueError if one page exists twice with different text.
    """
    folder = doc_id.replace("@", "_")
    pages: dict[int, Path] = {}
    revisions: set[str] = set()
    for out in sorted(p.parent for p in root.rglob("out/" + folder)):
        if not (out / folder).is_dir():
            continue
        info = out / "run_info.json"
        if info.exists():
            rev = json.loads(info.read_text(encoding="utf-8")).get("bodhan", {}).get("revision")
            revisions.add(str(rev))
        else:
            revisions.add("unknown")
        for md in (out / folder).glob("p*.md"):
            n = int(md.stem[1:])
            if n in pages and pages[n].read_bytes() != md.read_bytes():
                raise ValueError(f"{doc_id} p.{n}: two different OCR outputs ({pages[n]}, {md})")
            pages.setdefault(n, md)
    return pages, revisions


def decode(text: str) -> str:
    """Visible text of a raw OCR line: word marks to spaces (used for recognising, not storing)."""
    return text.replace(SP_MARK, " ")


def is_running_head(text: str) -> bool:
    t = decode(text).strip()
    return bool(_PAGE_NO.match(t) or _RULE_LINE.match(t) or (_HEAD.search(t) and len(t) < 90))


def line_lang(text: str, prev: str) -> str:
    """'hi' or 'en' by letter share; lines without letters keep the previous language."""
    t = _TAG.sub(" ", decode(text))  # "<td>" is markup, not English
    hi, en = len(_DEVANAGARI.findall(t)), len(_LATIN.findall(t))
    if hi + en == 0:
        return prev
    return "hi" if hi >= en else "en"


def page_lines(page: int, md: str) -> list[tuple[Line, bool]]:
    """Lines of one page as (Line, is_body); blank lines mark the next line as a paragraph start."""
    out: list[tuple[Line, bool]] = []
    raw = md.split("\n")
    content = [i for i, ln in enumerate(raw) if decode(ln).strip()]
    head_zone = set(content[:HEAD_WINDOW])
    last = content[-1] if content else -1
    blank_before = False
    for i, ln in enumerate(raw):
        if not decode(ln).strip():
            blank_before = True
            continue
        head = (i in head_zone and is_running_head(ln)) or (
            i == last and _PAGE_NO.match(decode(ln).strip()) is not None
        )
        kind = "header" if head else "body"
        # a table row starts its own paragraph, so rows stay apart in canonical text
        para = blank_before or _ROW_START.match(decode(ln)) is not None
        out.append((Line(page, ln, kind, para_start=para and not head), not head))
        if not head:
            blank_before = False
    return out


def apply_corrections(
    doc_id: str, page: int, md: str, corrections: list[dict[str, Any]]
) -> tuple[str, int]:
    """Apply human-verified fixes (``data/ocr_corrections.json``) to one page; (text, applied).

    Spaces in ``find``/``replace`` stand for Bodhan's U+2581 word marks. Each ``find`` must occur
    exactly once on its page, so a fix can never land in the wrong place.
    """
    applied = 0
    for c in corrections:
        if c["doc_id"] != doc_id or int(c["page"]) != page:
            continue
        find, repl = c["find"].replace(" ", SP_MARK), c["replace"].replace(" ", SP_MARK)
        if md.count(find) != 1:
            raise ValueError(f"{doc_id} p.{page}: correction {c['find']!r} found {md.count(find)}x")
        md = md.replace(find, repl)
        applied += 1
    return md, applied


def load(
    root: Path,
    doc_id: str,
    n_pages: int,
    default_lang: str,
    corrections: list[dict[str, Any]] | None = None,
) -> OcrDoc:
    """Read a document's OCR pages (all of 1..n_pages must exist) into per-language lines.

    ``pages`` keeps Bodhan's text unchanged; recorded ``corrections`` are applied to the lines.
    """
    files, revisions = find_pages(root, doc_id)
    missing = [n for n in range(1, n_pages + 1) if n not in files]
    if missing:
        raise ValueError(f"{doc_id}: OCR pages missing: {missing[:10]}")
    if len(revisions) != 1 or "unknown" in revisions:
        raise ValueError(f"{doc_id}: OCR pages from several or unknown revisions: {revisions}")
    doc = OcrDoc(engine=f"ocr:bodhan@{next(iter(revisions))[:8]}", pages={})
    doc.lines = {"en": [], "hi": []}
    lang = default_lang
    for n in range(1, n_pages + 1):
        md = files[n].read_text(encoding="utf-8")
        doc.pages[n] = md
        md, k = apply_corrections(doc_id, n, md, corrections or [])
        doc.corrections += k
        doc.page_chars[n] = sum(1 for c in decode(md) if not c.isspace())
        for line, is_body in page_lines(n, md):
            if is_body:
                lang = line_lang(line.text, lang)
                doc.lines[lang].append(line)
    return doc
