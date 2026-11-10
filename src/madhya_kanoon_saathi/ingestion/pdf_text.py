"""Born-digital PDF text extraction with pypdfium2 (DEC-055 item 1).

Lines are classified by **font size**, not by text pattern (observed on India Code PDFs, 2026-11-10,
e.g. IN.RTI2005@en@1 p.11): body text ~11 pt, amendment footnotes ~9 pt, superscript footnote
markers ~7 pt. So:

- ``body`` line: ordinary text; small digits inside it are footnote **markers** (spans kept);
- ``footnote`` line: most visible characters are smaller than body text but not marker-sized;
- ``header`` line: the page's first line when it is only a page number.

`raw` text is kept exactly as extracted (markers included). Canonical text is made later by the
chunker (DEC-055 7a).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

MARKER_RATIO = 0.75  # chars at or below this fraction of body size are superscripts (7/11 = 0.64)
FOOTNOTE_RATIO = 0.9  # lines whose typical size is below this fraction are footnotes (9/11 = 0.82)
_PAGE_NO = re.compile(r"^\s*\d{1,4}\s*$")
_PAGE_FOOTER = re.compile(r"^\s*Page \d{1,4} of \d{1,4}\s*$")
_FOOTNOTE_START = re.compile(r"^(\d{1,3}\*?|\*)\.\s*(\S.*)$")  # "1. ", "1.18th", "1*.", "*."


@dataclass(frozen=True)
class Line:
    page: int  # 1-based PDF page
    text: str  # raw, as extracted
    kind: str  # body | footnote | header
    markers: tuple[tuple[int, int], ...] = ()  # spans in `text` of superscript footnote markers


@dataclass
class Footnote:
    page: int
    n: str  # footnote label as printed: "1", "1*" or "*"
    text: str


@dataclass
class DocText:
    body_size: float
    lines: list[Line] = field(default_factory=list)
    footnotes: list[Footnote] = field(default_factory=list)
    page_chars: dict[int, int] = field(default_factory=dict)  # visible chars per page


def body_size(sizes: Iterable[float]) -> float:
    """Most common font size (rounded to 0.5 pt) among visible characters."""
    c = Counter(round(s * 2) / 2 for s in sizes if s > 1.5)
    return c.most_common(1)[0][0] if c else 0.0


def split_lines(chars: Sequence[tuple[str, float]]) -> list[list[tuple[str, float]]]:
    """Split a page's (char, size) stream into lines on newline; carriage returns are dropped."""
    lines: list[list[tuple[str, float]]] = [[]]
    for ch, size in chars:
        if ch == "\n":
            lines.append([])
        elif ch != "\r":
            lines[-1].append((ch, size))
    return [ln for ln in lines if any(not c.isspace() for c, _ in ln)]


def classify_line(
    chars: Sequence[tuple[str, float]], body: float
) -> tuple[str, tuple[tuple[int, int], ...]]:
    """Return (kind, marker spans) for one line: body or footnote (header is decided per page)."""
    visible = [s for c, s in chars if not c.isspace() and s > 1.5]
    if not visible or body <= 0:
        return "body", ()
    small_marker = [s <= body * MARKER_RATIO for s in visible]
    if all(small_marker):  # a line holding only a superscript marker (e.g. "1" before "[(j) ...")
        return "body", _marker_spans(chars, body)
    typical = sorted(visible)[len(visible) // 2]
    if body * MARKER_RATIO < typical < body * FOOTNOTE_RATIO:
        return "footnote", ()
    return "body", _marker_spans(chars, body)


def _marker_spans(chars: Sequence[tuple[str, float]], body: float) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    start = None
    for i, (c, s) in enumerate(chars):
        is_marker = (c.isdigit() or c == "*") and 1.5 < s <= body * MARKER_RATIO
        if is_marker and start is None:
            start = i
        elif not is_marker and start is not None:
            spans.append((start, i))
            start = None
    if start is not None:
        spans.append((start, len(chars)))
    return tuple(spans)


def lines_from_pages(pages: Sequence[Sequence[tuple[str, float]]]) -> DocText:
    """Pure core: build classified lines and footnotes from per-page (char, size) streams."""
    body = body_size(s for page in pages for c, s in page if not c.isspace())
    doc = DocText(body_size=body)
    for pno, page in enumerate(pages, start=1):
        doc.page_chars[pno] = sum(1 for c, _ in page if not c.isspace())
        current: Footnote | None = None
        raw_lines = split_lines(page)
        texts = ["".join(c for c, _ in chars) for chars in raw_lines]
        kinds: list[str] = []
        spans: list[tuple[tuple[int, int], ...]] = []
        for idx, (chars, text) in enumerate(zip(raw_lines, texts, strict=True)):
            if (idx == 0 and _PAGE_NO.match(text)) or _PAGE_FOOTER.match(text):
                kinds.append("header")
                spans.append(())
                continue
            kind, markers = classify_line(chars, body)
            kinds.append(kind)
            spans.append(markers)
        # Footnotes are only the trailing run of small lines at the page bottom; small lines in the
        # middle of a page (e.g. small-caps chapter titles in IN.COW2019@en@1 p.5) are body text.
        last_body = max((i for i, k in enumerate(kinds) if k == "body"), default=-1)
        for i, k in enumerate(kinds):
            if k == "footnote" and i < last_body:
                kinds[i] = "body"
        for text, kind, markers in zip(texts, kinds, spans, strict=True):
            doc.lines.append(Line(pno, text.strip() if kind == "header" else text, kind, markers))
            if kind == "footnote":
                m = _FOOTNOTE_START.match(text.strip())
                if m:
                    current = Footnote(pno, m.group(1), m.group(2).strip())
                    doc.footnotes.append(current)
                elif current is not None:
                    current.text += " " + text.strip()
    return doc


def extract(path: Path) -> DocText:
    """Read a born-digital PDF with pypdfium2 and classify its lines."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_c

    pdf = pdfium.PdfDocument(path)
    pages: list[list[tuple[str, float]]] = []
    try:
        for i in range(len(pdf)):
            tp = pdf[i].get_textpage()
            text = tp.get_text_range()
            n = tp.count_chars()
            pages.append(
                [
                    (text[k], float(pdfium_c.FPDFText_GetFontSize(tp.raw, k)))
                    for k in range(min(n, len(text)))
                ]
            )
            tp.close()
    finally:
        pdf.close()
    return lines_from_pages(pages)
