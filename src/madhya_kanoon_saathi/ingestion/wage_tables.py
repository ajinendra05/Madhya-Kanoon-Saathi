"""MP minimum-wage notifications (Hindi, OCR): schedules and the wage arithmetic gate (W1.1b).

DEC-050 (state official schedule-specific rates with a qualification), DEC-071 item 2 (every wage
row must pass an arithmetic check or the build fails), DEC-072 (``sch_<x>`` uids for
Devanagari-lettered schedules). Shaped on ``MP.MWVDAOCT2026@hi@1`` (Labour Commissioner, Indore,
30.09.2026).

- A schedule starts at "अनुसूची - अ (खण्ड - ब)", "अनुसूची -च", "अनुसूची - द (कृषि नियोजन)" or
  "(खण्ड-अ - अनुसूची-अ)"; its uid is ``sch_<letters>`` with the खण्ड (part) letter appended when
  the label carries one. A short title line such as "बीडी नियोजन" and the text after it belong to
  the next schedule. The Labour Commissioner's signature ends the text.
- Each schedule is one unit chunked by size (``para_restart``), never split into rows.
- :func:`check_wage_rows` re-computes every wage row: base + VDA = total (monthly, daily), monthly
  ÷ day basis = daily (the basis is read from the schedule's own "(26 दिन के मान से)"), and the
  rounded daily rate = daily total rounded half up (Explanation 2 of the notification).
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence

from madhya_kanoon_saathi.ingestion.ocr_text import decode
from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import Parsed, Unit

TRANSLIT = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu", "ए": "e", "ऐ": "ai", "ओ": "o",
    "औ": "au", "क": "ka", "ख": "kha", "ग": "ga", "घ": "gha", "ङ": "nga", "च": "cha", "छ": "chha",
    "ज": "ja", "झ": "jha", "ञ": "nya", "ट": "tta", "ठ": "ttha", "ड": "dda", "ढ": "ddha", "ण": "nna",
    "त": "ta", "थ": "tha", "द": "da", "ध": "dha", "न": "na", "प": "pa", "फ": "pha", "ब": "ba",
    "भ": "bha", "म": "ma", "य": "ya", "र": "ra", "ल": "la", "व": "va", "श": "sha", "ष": "ssa",
    "स": "sa", "ह": "ha",
}  # fmt: skip
_DASH = r"\s*[-–—]?\s*"  # noqa: RUF001
_SCHEDULE = re.compile(rf"^अनुसूची{_DASH}(?P<label>[^\s()]+)\s*(\((?P<paren>[^)]*)\))?\s*$")
_PART_FIRST = re.compile(
    rf"^\(?\s*खण्ड{_DASH}(?P<part>[^\s()-]+){_DASH}अनुसूची{_DASH}(?P<label>[^\s()]+?)\s*\)?\s*$"
)
_PART_IN_PAREN = re.compile(rf"^खण्ड{_DASH}(?P<part>\S+)$")
_TITLE = re.compile(r"^\S+\s+नियोजन$")  # "बीडी नियोजन": introduces the next schedule
_SIGNATURE = re.compile(r"^श्रमायुक्त\s*,?$")
_BASIS = re.compile(r"\(\s*(\d{2})\s*दिन\s+के\s+मान\s+से\s*\)")
_NUMBER = re.compile(r"^(?:रू?ु?पये\s*)?(\d+(?:\.\d+)?)$")


def translit(label: str) -> str:
    """Fixed letter-by-letter transliteration of a Devanagari label (spec table)."""
    out = []
    for ch in label:
        if ch not in TRANSLIT:
            raise ValueError(f"no transliteration for {ch!r} in schedule label {label!r}")
        out.append(TRANSLIT[ch])
    return "".join(out)


def schedule_uid(instrument_id: str, text: str) -> tuple[str, str] | None:
    """(uid, title) if the line starts a schedule, else None."""
    t = decode(text).strip()
    m = _PART_FIRST.match(t)
    if m:
        return f"{instrument_id}:sch_{translit(m['label'])}_{translit(m['part'])}", ""
    m = _SCHEDULE.match(t)
    if not m:
        return None
    paren = (m["paren"] or "").strip()
    part = _PART_IN_PAREN.match(paren)
    if part:
        return f"{instrument_id}:sch_{translit(m['label'])}_{translit(part['part'])}", ""
    return f"{instrument_id}:sch_{translit(m['label'])}", paren


def parse_wage_notification(instrument_id: str, lines: Sequence[Line]) -> Parsed:
    """Schedules of a wage notification as units (Hindi body lines from :mod:`ocr_text`)."""
    units: list[Unit] = []
    unassigned: list[Line] = []
    trailing: list[Line] = []
    pending: list[Line] = []
    for i, ln in enumerate(lines):
        if ln.kind != "body":
            continue
        t = decode(ln.text).strip()
        if _SIGNATURE.match(t):
            # the name line in brackets before "श्रमायुक्त," is part of the signature
            if units and units[-1].lines and units[-1].lines[-1] is lines[i - 1]:
                trailing.append(units[-1].lines.pop())
            trailing += [x for x in lines[i:] if x.kind == "body"]
            break
        head = schedule_uid(instrument_id, ln.text)
        if head is not None:
            uid, title = head
            u = Unit(uid=uid, kind="schedule", label=t, heading=title, lines=[*pending, ln])
            u.para_restart = True
            units.append(u)
            pending = []
            continue
        if _TITLE.match(t) or pending:
            pending.append(ln)
            continue
        if not units:
            unassigned.append(ln)
            continue
        units[-1].lines.append(ln)
        if not units[-1].heading and not t.startswith("|") and len(units[-1].lines) == 2:
            units[-1].heading = t  # "किसी स्लेट पेंसिल निर्माण शाला में नियोजन"
    if pending:
        unassigned += pending
    seen: set[str] = set()
    for u in units:
        if u.uid in seen:
            raise ValueError(f"two schedules map to {u.uid}")
        seen.add(u.uid)
    return Parsed(units=units, unassigned=unassigned, trailing=trailing)


def _num(cell: str) -> float | None:
    m = _NUMBER.match(cell.replace(",", "").strip())
    return float(m.group(1)) if m else None


def _round_half_up(x: float) -> int:
    return math.floor(x + 0.5 + 1e-9)


def check_wage_rows(unit: Unit) -> tuple[list[str], int]:
    """Arithmetic gate for one schedule: (errors, rows checked)."""
    text = "\n".join(decode(ln.text) for ln in unit.lines)
    m_basis = _BASIS.search(text)
    basis = int(m_basis.group(1)) if m_basis else None
    errors: list[str] = []
    checked = 0
    for ln in unit.lines:
        t = decode(ln.text).strip()
        if not t.startswith("|") or re.fullmatch(r"[|\s:-]+", t):
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        nums = [_num(c) for c in cells[1:]]
        if not any(n is not None for n in nums):
            continue  # header or group row ("लिपिकीय वर्ग")
        where = f"{unit.uid} p.{ln.page} row {cells[0][:30]!r}"
        if len(cells) == 8 and all(n is not None for n in nums):
            bm, bd, vm, vd, tm, td, ru = (float(n) for n in nums if n is not None)
            if basis is None:
                errors.append(f"{where}: no '(NN दिन के मान से)' day basis in the schedule")
                continue
            checks = [
                ("base + VDA = total (monthly)", abs(bm + vm - tm) < 0.005),
                ("base + VDA = total (daily)", abs(bd + vd - td) < 0.011),
                (f"monthly base / {basis} = daily base", abs(bm / basis - bd) < 0.0051),
                (f"monthly VDA / {basis} = daily VDA", abs(vm / basis - vd) < 0.0051),
                ("rounded daily = daily total rounded half up", _round_half_up(td) == ru),
            ]
        elif len(cells) == 4 and all(n is not None for n in nums):
            base, vda, total = (float(n) for n in nums if n is not None)
            checks = [("base + VDA = total", abs(base + vda - total) < 0.005)]
        else:
            errors.append(f"{where}: unrecognised wage row ({len(cells)} cells)")
            continue
        checked += 1
        errors += [f"{where}: fails {name}" for name, ok in checks if not ok]
    return errors, checked
