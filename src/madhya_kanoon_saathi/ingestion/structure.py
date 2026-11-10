"""Provision tree for India Code style statutes (W1.1a, DEC-055). Spec: ``docs/specs/chunks.md``.

Input: classified lines from :mod:`pdf_text`. Output: provision **units** in document order, each
with its ``section_uid`` and the raw lines that belong to it (children's lines are not included).

Recognised starts (after removing footnote markers and a leading insertion bracket ``[``):

- ``CHAPTER IV`` + title line: chapter (path only; chapters are not in the uid)
- ``8. Heading.--(1) text``: section ``s8`` (inserted ``8A`` is ``s8A``), sub-section on the
  same line
- ``(2) text``: sub-section ``ss2`` (only the expected next number: ``(1A)`` or ``(2)`` after
  ``(1)``)
- ``(a) text`` / ``(iv) text``: clause ``cl_a`` / ``clr_iv``; a new list inside a clause is a
  sub-clause
- ``Provided that`` / ``Provided further that``: proviso ``prov<n>`` of the current sub-section,
  or of the clause before it when another clause follows
- ``Explanation.--`` / ``Explanation 1.--``: explanation ``expl<n>``, placed like provisos
- ``THE FIRST SCHEDULE`` / ``THE SCHEDULE``: schedule ``sch<n>``; numbered items are ``para<n>``
- ``STATE AMENDMENT`` blocks are set aside (not main-Act text); repealed sections are flagged

Sequence checks guard against false starts (a wrapped line beginning "(1)" that is a
cross-reference). Lines before the enactment date line (``[15th June, 2005.]``) are front
matter (title, contents) and are returned separately as ``unassigned``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from madhya_kanoon_saathi.ingestion.pdf_text import Line

_ENACTED = re.compile(r"^\[\d{1,2}(st|nd|rd|th)\s+[A-Z][a-z]+,?\s+\d{4}\.?\]\.?$")
_CHAPTER = re.compile(r"^CHAPTER\s+([IVXLC]+[A-Z]?)\s*$")
_SECTION = re.compile(
    r"^(\d{1,4})([A-Z]{0,3})\s?\.\s*(?=[A-Za-z\[\"“(])(.*)$"
)  # "8. ", "49.Matters", "39 .Time"
_HEAD_DASH = re.compile(r"\.?\s*[—–]\s*")  # noqa: RUF001  heading ends with em or en dash
_SUBSEC = re.compile(r"^\((\d{1,3})([A-Z]{0,2})\)\s*(.*)$")
_CLAUSE = re.compile(r"^\(([a-z]{1,4})\)\s*(.*)$")
_DEF_START = re.compile(r"^[\"“‘']")  # noqa: RUF001  a definition starts with the quoted term
_PROVISO = re.compile(r"^Provided\s+(further\s+|also\s+)?that\b")
_EXPLAN = re.compile(r"^Explanations?\s*(\d+|[IVX]+)?\s*\.?\s*[—–-]")  # noqa: RUF001
_SCHEDULE = re.compile(
    r"^THE\s+((FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)"
    r"\s+)?SCHEDULE\b"
)
_REPEALED = re.compile(r"^\[(.+?)\]\.?\s*(Rep\.|Repealed|Omitted)")
_NO_DASH_SS1 = re.compile(r"\.\s+(?=\(1\)\s)")
_STATE_AMEND = re.compile(r"^STATE\s+AMENDMENTS?\.?$")
_SCHED_PARA = re.compile(r"^(\d{1,3})\.\s+\S")
_ORDINALS = {
    "FIRST": 1, "SECOND": 2, "THIRD": 3, "FOURTH": 4, "FIFTH": 5, "SIXTH": 6,
    "SEVENTH": 7, "EIGHTH": 8, "NINTH": 9, "TENTH": 10, "ELEVENTH": 11, "TWELFTH": 12,
}  # fmt: skip
_ROMAN = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
    "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15, "xvi": 16, "xvii": 17, "xviii": 18,
    "xix": 19, "xx": 20, "xxi": 21, "xxii": 22, "xxiii": 23, "xxiv": 24, "xxv": 25,
}  # fmt: skip


@dataclass
class Unit:
    uid: str
    kind: str  # section | ss | clause | subclause | prov | expl | schedule | para
    label: str  # as printed: "8", "(1)", "(j)", "Provided that", ...
    heading: str = ""  # section heading (marginal note) without the trailing ".—"
    chapter: str = ""  # "CHAPTER II — TITLE"
    repealed: bool = False  # "[Heading.] Rep. by ..." / "Omitted": no current text, not chunked
    lines: list[Line] = field(default_factory=list)


@dataclass
class StateAmendment:
    """An India Code "STATE AMENDMENT" block printed inside the body (not part of the main text)."""

    after_uid: str  # the main-Act unit it follows
    lines: list[Line] = field(default_factory=list)

    @property
    def mentions_mp(self) -> bool:
        return any("Madhya Pradesh" in ln.text for ln in self.lines)


@dataclass
class Parsed:
    units: list[Unit]
    unassigned: list[Line]  # front matter and anything before the first section
    state_amendments: list[StateAmendment] = field(default_factory=list)


def visible_text(line: Line) -> str:
    """Line text without footnote marker spans (used only for recognising starts)."""
    out, last = [], 0
    for a, b in line.markers:
        out.append(line.text[last:a])
        last = b
    out.append(line.text[last:])
    return "".join(out).strip()


def _start_text(line: Line) -> str:
    t = visible_text(line)
    return t[1:].lstrip() if t.startswith("[") else t


def _alpha_next(prev: str | None) -> set[str]:
    """Expected next letter labels after `prev` ('a' first; 'j' -> 'k' or inserted 'ja')."""
    if prev is None:
        return {"a"}
    nxt = {prev + "a"}  # inserted clause, e.g. (j) -> (ja)
    last = prev[-1]
    if last != "z":
        nxt.add(prev[:-1] + chr(ord(last) + 1))  # (ja) -> (jb); (j) -> (k)
    if len(prev) > 1:
        base = prev[0]
        if base != "z":
            nxt.add(chr(ord(base) + 1))  # (ja) -> (k)
    return nxt


def _is_next_roman(prev: str | None, label: str) -> bool:
    n = _ROMAN.get(label)
    return n is not None and n == (_ROMAN.get(prev, 0) if prev else 0) + 1


def _next_clause_label(lines: Sequence[Line], i: int, window: int = 80) -> str | None:
    """Label of the next clause-like line after line i, stopping at the next section."""
    for j in range(i + 1, min(i + 1 + window, len(lines))):
        t = _start_text(lines[j])
        if _SECTION.match(t):
            return None
        m = _CLAUSE.match(t)
        if m:
            return m.group(1)
    return None


def parse_statute(instrument_id: str, lines: Sequence[Line]) -> Parsed:
    body = [ln for ln in lines if ln.kind == "body"]
    # merge marker-only lines into the following line ("1" + "[(j) information ...", RTI p.11)
    merged: list[Line] = []
    carry: Line | None = None
    for ln in body:
        if ln.markers and not visible_text(ln):
            carry = (
                ln
                if carry is None
                else Line(ln.page, carry.text + "\n" + ln.text, "body", carry.markers)
            )
            continue
        if carry is not None:
            off = len(carry.text) + 1
            ln = Line(
                ln.page,
                carry.text + "\n" + ln.text,
                "body",
                carry.markers + tuple((a + off, b + off) for a, b in ln.markers),
            )
            carry = None
        merged.append(ln)

    start = next((i + 1 for i, ln in enumerate(merged) if _ENACTED.match(visible_text(ln))), 0)
    unassigned = list(merged[:start])
    units: list[Unit] = []
    chapter = ""
    pending_chapter: str | None = None
    sec: Unit | None = None
    ss: Unit | None = None  # current sub-section (or None: clauses hang off the section)
    cur: Unit | None = None  # unit receiving lines
    clause: Unit | None = None
    sub: Unit | None = None
    clause_sys: str | None = None  # "alpha" | "roman" for the current clause list
    sub_sys: str | None = None  # numbering system of the current sub-clause list
    last_clause: str | None = None
    last_sub: str | None = None
    last_ss: tuple[int, str] | None = None
    last_sec = 0
    heading_open = False
    n_prov = n_expl = 0
    after_clause: list[Unit] = []  # provisos/explanations seen after the current clause
    sched: Unit | None = None
    sa: StateAmendment | None = None  # open STATE AMENDMENT block
    state_amendments: list[StateAmendment] = []
    last_para = 0

    def owner() -> Unit:
        assert sec is not None
        return ss if ss is not None else sec

    def new(uid: str, kind: str, label: str, heading: str = "") -> Unit:
        u = Unit(uid=uid, kind=kind, label=label, heading=heading, chapter=chapter)
        units.append(u)
        return u

    for idx in range(start, len(merged)):
        ln = merged[idx]
        t = _start_text(ln)
        if _STATE_AMEND.match(t):
            sa = StateAmendment(after_uid=units[-1].uid if units else instrument_id)
            state_amendments.append(sa)
            sa.lines.append(ln)
            continue
        if sa is not None:
            m_next = _SECTION.match(t)
            leaves = (m_next is not None and int(m_next.group(1)) > last_sec) or bool(
                _CHAPTER.match(t) or _SCHEDULE.match(t)
            )
            if not leaves:
                sa.lines.append(ln)
                continue
            sa = None
        m_ch = _CHAPTER.match(t)
        if m_ch and sched is None:
            pending_chapter = f"CHAPTER {m_ch.group(1)}"
            continue
        if pending_chapter is not None:
            chapter = f"{pending_chapter} — {t}"
            pending_chapter = None
            continue

        m_sch = _SCHEDULE.match(t)
        if m_sch:
            n = _ORDINALS.get(m_sch.group(2) or "", 1)
            sched = new(f"{instrument_id}:sch{n}", "schedule", t)
            sec = ss = clause = sub = None
            after_clause = []
            cur, last_para = sched, 0
            cur.lines.append(ln)
            continue
        if sched is not None:
            m_p = _SCHED_PARA.match(t)
            if m_p and int(m_p.group(1)) == last_para + 1:
                last_para += 1
                cur = new(f"{sched.uid}:para{last_para}", "para", m_p.group(1))
            assert cur is not None
            cur.lines.append(ln)
            continue

        m_s = _SECTION.match(t)
        if m_s:
            num, ins, rest = int(m_s.group(1)), m_s.group(2), m_s.group(3)
            plausible = (
                (num == last_sec and ins)
                or (last_sec < num <= last_sec + 3)
                or (last_sec == 0 and num == 1)
            )
            if plausible:
                parts = _HEAD_DASH.split(rest, maxsplit=1)
                m_rep = _REPEALED.match(rest)
                if len(parts) < 2 and not m_rep:
                    # "9. Procedure ... etc. (1) A Social ...": dash missing (IN.SSC2020 s.9)
                    parts = _NO_DASH_SS1.split(rest, maxsplit=1)
                heading_open = len(parts) < 2 and not m_rep  # heading wraps until ".--"
                if m_rep:
                    heading = m_rep.group(1).rstrip(". ")
                else:
                    heading = parts[0].rstrip(". ") if len(parts) == 2 else rest.rstrip()
                last_sec = num
                sec = new(f"{instrument_id}:s{num}{ins}", "section", f"{num}{ins}", heading)
                sec.repealed = bool(m_rep)
                ss = clause = sub = None
                clause_sys = last_clause = last_sub = sub_sys = None
                last_ss = None
                n_prov = n_expl = 0
                after_clause = []
                cur = sec
                tail = parts[1] if len(parts) == 2 else ""
                m_ss = _SUBSEC.match(tail)
                if m_ss and m_ss.group(1) == "1" and not m_ss.group(2):
                    # "8. Heading.--(1) text": the line opens sub-section (1), heading included
                    ss = new(f"{sec.uid}:ss1", "ss", "(1)")
                    last_ss = (1, "")
                    cur = ss
                cur.lines.append(ln)
                continue
        if sec is None:
            unassigned.append(ln)
            continue
        if heading_open and cur is sec:
            # wrapped heading (IN.TPA1882 s.106 "... written contract or / local usage.--")
            m_rep2 = _REPEALED.match(f"{sec.heading} {t}")
            if m_rep2:  # wrapped "[Heading ...] Rep. by ..." (IN.RA1908 s.56)
                sec.heading, sec.repealed, heading_open = m_rep2.group(1).rstrip(". "), True, False
                cur.lines.append(ln)
                continue
            parts = _HEAD_DASH.split(t, maxsplit=1)
            if len(parts) == 2:
                sec.heading = f"{sec.heading} {parts[0]}".strip().rstrip(". ")
                heading_open = False
                m_ss = _SUBSEC.match(parts[1])
                if m_ss and m_ss.group(1) == "1" and not m_ss.group(2):
                    ss = new(f"{sec.uid}:ss1", "ss", "(1)")
                    last_ss = (1, "")
                    cur = ss
                cur.lines.append(ln)
                continue
            if len(sec.lines) < 3:
                sec.heading = f"{sec.heading} {t}".strip()
                cur.lines.append(ln)
                continue
            heading_open = False

        m_ss = _SUBSEC.match(t)
        if m_ss:
            n, suf = int(m_ss.group(1)), m_ss.group(2)
            ok = (last_ss is None and n == 1 and not suf) or (
                last_ss is not None
                and ((n == last_ss[0] + 1 and not suf) or (n == last_ss[0] and suf > last_ss[1]))
            )
            if ok:
                ss = new(f"{sec.uid}:ss{n}{suf}", "ss", f"({n}{suf})")
                last_ss = (n, suf)
                clause = sub = None
                clause_sys = last_clause = last_sub = sub_sys = None
                n_prov = n_expl = 0
                after_clause = []
                cur = ss
                cur.lines.append(ln)
                continue

        if _PROVISO.match(t) or _EXPLAN.match(t):
            is_prov = bool(_PROVISO.match(t))
            if is_prov:
                n_prov += 1
                cur = new(f"{owner().uid}:prov{n_prov}", "prov", "Provided")
            else:
                n_expl += 1
                cur = new(f"{owner().uid}:expl{n_expl}", "expl", "Explanation")
            sub = None
            if clause is not None:
                after_clause.append(cur)  # re-parented to the clause if another clause follows
            cur.lines.append(ln)
            continue

        m_cl = _CLAUSE.match(t)
        if m_cl and cur is not None:
            lab = m_cl.group(1)
            in_body = cur.kind not in ("prov", "expl")
            cand_main: str | None = None
            if clause_sys in (None, "alpha") and lab in _alpha_next(
                last_clause if clause_sys else None
            ):
                cand_main = "alpha"
            elif clause_sys in (None, "roman") and _is_next_roman(
                last_clause if clause_sys else None, lab
            ):
                cand_main = "roman"
            cand_sub: str | None = None
            if clause is not None and in_body:
                sub_roman = clause_sys == "alpha" and (
                    (sub_sys == "roman" and _is_next_roman(last_sub, lab))
                    or (sub_sys != "roman" and lab == "i")
                )
                sub_alpha = (sub_sys == "alpha" and lab in _alpha_next(last_sub)) or (
                    sub_sys != "alpha" and lab == "a"
                )
                if sub_roman and sub_alpha:
                    # "(i)" after sub-clause "(h)": letter if "(j)" follows, roman if "(ii)" does
                    # (definition of "wages", IN.COW2019@en@1 s.2(y), exclusions list (a)-(k))
                    nxt = _next_clause_label(merged, idx)
                    cand_sub = "roman" if nxt is not None and _is_next_roman(lab, nxt) else "alpha"
                elif sub_roman:
                    cand_sub = "roman"
                elif sub_alpha:
                    cand_sub = "alpha"
            choice: str | None = None
            if cand_main and cand_sub == "roman":
                # "(i)" after clause (h): roman sub-clause if "(ii)" comes next, else clause (i)
                nxt = _next_clause_label(merged, idx)
                choice = "sub" if nxt is not None and _is_next_roman(lab, nxt) else "main"
            elif cand_main and cand_sub == "alpha":
                # "(d)" after sub-clause "(c)" inside clause (c): a definition (quoted term)
                # starts the next main clause; otherwise the open sub-list continues
                choice = "main" if _DEF_START.match(m_cl.group(2)) else "sub"
            elif cand_sub:
                choice = "sub"
            elif cand_main:
                choice = "main"
            if choice == "sub":
                assert clause is not None and cand_sub is not None
                prefix = "scl_" if cand_sub == "roman" else "scla_"
                sub = new(f"{clause.uid}:{prefix}{lab}", "subclause", f"({lab})")
                sub_sys, last_sub, cur = cand_sub, lab, sub
                cur.lines.append(ln)
                continue
            if choice == "main":
                assert cand_main is not None
                prev_clause = clause
                seg = "cl_" if cand_main == "alpha" else "clr_"
                clause = new(f"{owner().uid}:{seg}{lab}", "clause", f"({lab})")
                if prev_clause is not None and after_clause:
                    # provisos/explanations sitting between two clauses belong to the earlier clause
                    # (RTI Act s.8(1): two provisos between clauses (i) and (j))
                    kp = ke = 0
                    for u in after_clause:
                        if u.kind == "prov":
                            kp += 1
                            u.uid = f"{prev_clause.uid}:prov{kp}"
                            n_prov -= 1
                        else:
                            ke += 1
                            u.uid = f"{prev_clause.uid}:expl{ke}"
                            n_expl -= 1
                after_clause = []
                clause_sys, last_clause = cand_main, lab
                sub, sub_sys, last_sub = None, None, None
                cur = clause
                cur.lines.append(ln)
                continue

        # continuation line
        if cur is None:
            cur = sec
        cur.lines.append(ln)
    return Parsed(units=units, unassigned=unassigned, state_amendments=state_amendments)
