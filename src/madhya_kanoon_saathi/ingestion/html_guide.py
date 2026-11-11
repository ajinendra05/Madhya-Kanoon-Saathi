"""HTML official guides (W1.1a, DEC-055 7c, DEC-057). Standard library only (html.parser).

Two layouts, both saved pages listed in the manifest:

- ``faq``: IN.ESHRAMFAQ2026@en@1 (eshram.gov.in/faqs). Accordion panels: an ``<h4>``
  "Q - 29. Are there any income criteria?" followed by an answer panel with an ``id``. One unit
  per question: ``para29``, locator selector ``#<answer panel id>``.
- ``headed``: MP.SLSALAGUIDE2025@en@1 (MP SLSA legal-aid page). ``<h2>`` "1. Legal Services" with
  ``<h3>`` questions under it, until the ``<h2>`` "Useful Links". Units ``para1`` and
  ``para1:sp<k>``; the page has no ids, so the selector is an XPath such as ``(//h3)[2]``.

Each text block (paragraph, list item, table cell, answer panel text) becomes one line with
``para_start=True``, so canonical text keeps blocks as separate paragraphs. Lines use page 0
(HTML has no pages); chunks get an ``html`` locator instead (see chunker).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import Parsed, Unit

_BLOCK = {
    "p",
    "li",
    "div",
    "td",
    "th",
    "dt",
    "dd",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "br",
    "tr",
    "section",
}
_SKIP = {"script", "style", "noscript", "nav", "header", "footer", "form", "svg", "button"}
_FAQ_Q = re.compile(r"^Q\s*-?\s*(\d{1,3})\s*[.:)]\s*(.+)$")
_NUM_HEAD = re.compile(r"^(\d{1,2})\.\s*(.+)$")


@dataclass
class Block:
    text: str
    heading: int  # 0 = not a heading, else 1-6
    anchor: str  # nearest element id at the block's start ("" if none)
    index: int  # n-th heading of this level (for XPath), 0 for non-headings


class _Blocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.buf: list[str] = []
        self.skip = 0
        self.heading = 0
        self.ids: list[str] = []
        self.anchor = ""
        self.counts = {n: 0 for n in range(1, 7)}

    def flush(self) -> None:
        text = " ".join("".join(self.buf).split())
        self.buf = []
        if text:
            idx = self.counts[self.heading] if self.heading else 0
            self.blocks.append(Block(text, self.heading, self.anchor, idx))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in _BLOCK:
            self.flush()
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                self.heading = int(tag[1])
                self.counts[self.heading] += 1
        el_id = dict(attrs).get("id")
        if el_id:
            self.anchor = el_id

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in _BLOCK:
            self.flush()
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                self.heading = 0

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.buf.append(data)


def blocks(html_text: str) -> list[Block]:
    p = _Blocks()
    p.feed(html_text)
    p.close()
    p.flush()
    return p.blocks


def _line(text: str) -> Line:
    return Line(0, text, "body", para_start=True)


def parse_faq(instrument_id: str, html_text: str) -> Parsed:
    units: list[Unit] = []
    unassigned: list[Line] = []
    cur: Unit | None = None
    for b in blocks(html_text):
        m = _FAQ_Q.match(b.text) if b.heading == 4 else None
        if m:
            cur = Unit(
                uid=f"{instrument_id}:para{int(m.group(1))}", kind="section", label=m.group(1)
            )
            cur.heading = m.group(2).strip()
            cur.chapter = "Frequently Asked Questions"
            units.append(cur)
            cur.lines.append(_line(b.text))
            continue
        if cur is None or b.heading:
            unassigned.append(_line(b.text))
            cur = None if b.heading else cur
            continue
        if not cur.selector and b.anchor:
            cur.selector = f"#{b.anchor}"
        cur.lines.append(_line(b.text))
    return Parsed(units=units, unassigned=unassigned)


def parse_headed(instrument_id: str, html_text: str, stop_at: str = "Useful Links") -> Parsed:
    units: list[Unit] = []
    unassigned: list[Line] = []
    top: Unit | None = None
    cur: Unit | None = None
    sub = 0
    for b in blocks(html_text):
        if b.heading == 2 and b.text.strip() == stop_at:
            break
        m = _NUM_HEAD.match(b.text) if b.heading == 2 else None
        if m:
            top = cur = Unit(
                uid=f"{instrument_id}:para{int(m.group(1))}", kind="section", label=m.group(1)
            )
            top.heading = m.group(2).strip()
            top.selector = f"(//h2)[{b.index}]"
            units.append(top)
            top.lines.append(_line(b.text))
            sub = 0
            continue
        if b.heading == 3 and top is not None:
            sub += 1
            cur = Unit(uid=f"{top.uid}:sp{sub}", kind="ss", label=f"{top.label}.{sub}")
            cur.heading = b.text.strip()
            cur.selector = f"(//h3)[{b.index}]"
            units.append(cur)
            cur.lines.append(_line(b.text))
            continue
        if cur is None:
            unassigned.append(_line(b.text))
            continue
        cur.lines.append(_line(b.text))
    return Parsed(units=units, unassigned=unassigned)
