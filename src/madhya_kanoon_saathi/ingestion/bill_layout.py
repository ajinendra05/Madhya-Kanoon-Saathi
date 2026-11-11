"""Bill-layout statutes (W1.1a, DEC-055). First case: IN.MTA2021@en@1 (MoHUA Model Tenancy Act).

In this layout a section starts "1. (1) This Act ..." and its heading is a **margin note** set in a
smaller font (10 pt beside 12 pt body text). The extractor puts margin text after the section's
lines, or on the same line ("... requires,-- Definitions."), and consecutive notes run together,
so pairing notes with sections is unreliable (tried 2026-11-11: headings drifted by s.21).

So:
- section **headings come from the document's own contents pages** ("ARRANGEMENT OF CLAUSES",
  e.g. "21.Eviction and recovery of possession of premises by landlord."), before "BE it enacted";
- all margin text in the body is marked as ``skips`` (kept in raw text, dropped from canonical
  text, DEC-055 7a); citation notes ("41 of 2006.") are counted for the QA report.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from madhya_kanoon_saathi.ingestion.pdf_text import Line

_ENACTING = re.compile(r"^BE\s+it\s+enacted\b")
_TOC_ENTRY = re.compile(r"^(\d{1,4}[A-Z]{0,3})\s?\.\s*(\S.*)$")
_TOC_SCHEDULE = re.compile(r"(?i)^(the\s+)?\w+\s+schedule\b")
_CITATION = re.compile(r"^\d{1,4}\s+of\s*\d{0,4}\.?$|^\d{4}\.?$")


@dataclass
class MarginSplit:
    lines: list[Line]
    headings: dict[str, str] = field(default_factory=dict)  # section label -> heading (contents)
    citations: list[str] = field(default_factory=list)  # margin citation fragments, e.g. "41 of"


def _plain(line: Line) -> str:
    return " ".join(line.text.split())


def toc_headings(lines: Sequence[Line]) -> dict[str, str]:
    """Section headings from the contents pages (all lines before "BE it enacted")."""
    out: dict[str, str] = {}
    last: str | None = None
    for ln in lines:
        if ln.kind != "body":
            continue
        t = _plain(ln)
        if _ENACTING.match(t):
            break
        m = _TOC_ENTRY.match(t)
        if m:
            last = m.group(1)
            out[last] = m.group(2)
        elif (
            last
            and t
            and not t.isupper()
            and not t.startswith("Clauses")
            and not _TOC_SCHEDULE.match(t)
        ):
            out[last] = (
                f"{out[last]} {t}"  # wrapped entry ("... Rent Court and Rent" / "Tribunal.")
            )
        else:
            last = None  # CHAPTER / title lines end the current entry
    return {k: v.rstrip(". ") for k, v in out.items()}


def split_margin(lines: Sequence[Line]) -> MarginSplit:
    res = MarginSplit(lines=[], headings=toc_headings(lines))
    in_body = False
    for ln in lines:
        if not in_body:
            in_body = ln.kind == "body" and bool(_ENACTING.match(_plain(ln)))
            res.lines.append(ln)
            continue
        if ln.kind == "footnote":  # no real footnotes in this layout: small lines are margin text
            res.citations += [_plain(ln)] if _CITATION.match(_plain(ln)) else []
            res.lines.append(replace(ln, kind="body", skips=((0, len(ln.text)),)))
            continue
        for a, b in ln.small:
            frag = " ".join(ln.text[a:b].split())
            if _CITATION.match(frag):
                res.citations.append(frag)
        res.lines.append(replace(ln, skips=ln.small) if ln.small else ln)
    return res
