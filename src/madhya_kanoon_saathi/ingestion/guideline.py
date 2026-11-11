"""Decimal-numbered scheme guidelines (W1.1a, DEC-055, DEC-057). First case: IN.SVANSG2025@en@1.

Layout: a contents page with dot leaders ("5.1.1. Rate of Interest........"), then headings
"1. Background", "5.1. Working Capital Term Loans", "5.1.1. Rate of Interest", and lettered items
"a) ..." under them. IDs (DEC-057): heading 5 = ``para5``, 5.1 = ``para5:sp1``,
5.1.1 = ``para5:sp1:sp1``, item a) = ``...:cl_a``.

A heading is accepted only when its number is a valid next number in the hierarchy (first child,
next sibling, or next number at a higher level), and its text looks like a title. This keeps
table cells such as "1. 1" or numbered sentences from opening new paragraphs.

Output reuses :class:`structure.Unit` so the statute chunker applies unchanged: top-level paragraphs
have kind ``section``, first-level sub-paragraphs ``ss``, deeper ones ``subpara``, items ``clause``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import Parsed, Unit, visible_text

# "5.1.Working Capital" has no space after the number; titles may start with a quote mark
_HEADING = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s*(\S.{0,110})$")
# "Annexure 3" / "Annexure-A" on a line of its own (not "... at Annexure-E).")
_ANNEX = re.compile(r"^Annexure\s*[-–]?\s*([A-Z]|\d{1,2})\s*$")  # noqa: RUF001
# numbered items and table rows ("11 Monitoring/ End Use", or a bare "2" when the cell is empty)
_ANNEX_ITEM = re.compile(r"^(\d{1,2})\.?(\s+\S|\s*$)")
_DOT_LEADER = re.compile(r"\.{5,}")
_ITEM = re.compile(r"^\(?([a-z])\)\s+\S")


def _is_next(prev: tuple[int, ...], cand: tuple[int, ...]) -> bool:
    """True if `cand` may follow heading `prev` (5.1 -> 5.1.1 / 5.2 / 6)."""
    if not prev:
        return cand == (1,)
    if len(cand) == len(prev) + 1 and cand[:-1] == prev and cand[-1] == 1:
        return True  # first child
    for depth in range(len(prev), 0, -1):  # next sibling at this or a higher level
        if (
            len(cand) == depth
            and cand[:-1] == prev[: depth - 1]
            and cand[-1] == prev[depth - 1] + 1
        ):
            return True
    return False


def _uid(instrument_id: str, number: tuple[int, ...]) -> str:
    return ":".join([instrument_id, f"para{number[0]}", *(f"sp{n}" for n in number[1:])])


def parse_guideline(instrument_id: str, lines: Sequence[Line]) -> Parsed:
    units: list[Unit] = []
    unassigned: list[Line] = []
    current: tuple[int, ...] = ()
    cur: Unit | None = None
    head: Unit | None = None  # heading unit that owns items
    last_item: str | None = None
    annex: Unit | None = (
        None  # annexures become schedules: "Annexure 3" = sch3, "Annexure A" = sch1
    )
    annex_para = 0
    for ln in lines:
        if ln.kind != "body":
            continue
        t = visible_text(ln)
        if _DOT_LEADER.search(t):  # contents page
            unassigned.append(ln)
            continue
        ma = _ANNEX.match(t)
        if ma and head is not None:
            label = ma.group(1)
            n = int(label) if label.isdigit() else ord(label) - ord("A") + 1
            annex = cur = Unit(
                uid=f"{instrument_id}:sch{n}", kind="schedule", label=f"Annexure {label}"
            )
            annex.heading = f"Annexure {label}"
            units.append(annex)
            annex.lines.append(ln)
            annex_para = 0
            continue
        if annex is not None:
            mp = _ANNEX_ITEM.match(t)
            if mp and int(mp.group(1)) == annex_para + 1:
                annex_para += 1
                cur = Unit(uid=f"{annex.uid}:para{annex_para}", kind="para", label=str(annex_para))
                units.append(cur)
            assert cur is not None
            cur.lines.append(ln)
            continue
        m = _HEADING.match(t)
        if m:
            number = tuple(int(x) for x in m.group(1).split("."))
            title = m.group(2).strip()
            first_letter = next((c for c in title if c.isalpha()), "")
            if (
                _is_next(current, number)
                and first_letter.isupper()
                and not title.endswith((",", ";"))
            ):
                current = number
                kind = "section" if len(number) == 1 else ("ss" if len(number) == 2 else "subpara")
                head = cur = Unit(
                    uid=_uid(instrument_id, number),
                    kind=kind,
                    label=".".join(map(str, number)),
                    heading=title.rstrip(". "),
                )
                units.append(cur)
                cur.lines.append(ln)
                last_item = None
                continue
        if head is None:
            unassigned.append(ln)
            continue
        mi = _ITEM.match(t)
        if mi and (
            (last_item is None and mi.group(1) == "a")
            or (last_item is not None and ord(mi.group(1)) == ord(last_item) + 1)
        ):
            last_item = mi.group(1)
            cur = Unit(uid=f"{head.uid}:cl_{last_item}", kind="clause", label=f"{last_item})")
            units.append(cur)
            cur.lines.append(ln)
            continue
        assert cur is not None
        cur.lines.append(ln)
    return Parsed(units=units, unassigned=unassigned)
