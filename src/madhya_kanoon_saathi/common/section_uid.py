"""Stable IDs for units of law (DEC-040). Spec: ``docs/specs/section_uid.md``.

A ``section_uid`` names a *provision* (not one language or version of its text)::

    IN.RTI2005:s8:ss1:cl_j      central RTI Act, s.8(1)(j)
    MP.ACA1961:s12:ss1:cl_a     MP Accommodation Control Act, s.12(1)(a)
    IN.RTIR2012:r4              a rule in a set of rules
    IN.RTI2005                  the whole instrument

A ``chunk_id`` names one stored text version: ``<section_uid>@<lang>@<version>[~n]``, where version
is the legal start date or ``nd-<8 hex of the document sha256>`` when no legal date is known, and
``~n`` (n >= 2) marks a later piece of one over-long clause (DEC-055).

Canonical uids are ASCII only. Turning a free-text reference (English or Hindi) into a uid is the
tokeniser's job (DEC-026), not this module's. Hindi clause letters are aligned structurally with
the English text, never transliterated (DEC-040 point 3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

JURISDICTIONS: frozenset[str] = frozenset({"IN", "MP"})
CHUNK_LANGUAGES: frozenset[str] = frozenset({"hi", "en"})

# Instrument code: uppercase letters/digits, starting with a letter, ending in a 4-digit year.
_INSTRUMENT_RE = re.compile(r"^(?P<jur>[A-Z]{2})\.(?P<code>[A-Z][A-Z0-9]*?)(?P<year>[0-9]{4})$")

# Canonical lowercase roman numeral 1-3999 (no "iiii", "vx", "ic" ...). The lookahead forbids "".
_ROMAN = r"(?=[ivxlcdm])m{0,3}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})"

# Segment kinds -> (regex, level). Level 0 = top-level unit of the instrument; higher = deeper.
# Clauses and sub-clauses keep the numbering system printed in the source (DEC-045 item 7):
#   cl_<letters>  alphabetic clause (a), (j), (ja)    clr_<roman>  roman clause (vii)
#   scl_<roman>   roman sub-clause (ii)               scla_<letters> alphabetic sub-clause (b)
# The kind, not the value, says which system is used, so "(i)" as a letter is cl_i and as a
# numeral is clr_i; they are different uids.
_TOP, _SUB, _CLAUSE, _SUBCLAUSE, _NOTE = 0, 1, 2, 3, 4
_CLAUSE_KINDS = frozenset({"cl", "clr"})
_SEGMENTS: tuple[tuple[str, re.Pattern[str], int], ...] = (
    ("ss", re.compile(r"^ss[1-9][0-9]*[A-Z]{0,2}$"), _SUB),
    ("scl", re.compile(rf"^scl_{_ROMAN}$"), _SUBCLAUSE),
    ("scla", re.compile(r"^scla_[a-z]{1,3}$"), _SUBCLAUSE),
    ("clr", re.compile(rf"^clr_{_ROMAN}$"), _CLAUSE),
    ("cl", re.compile(r"^cl_[a-z]{1,3}$"), _CLAUSE),
    ("prov", re.compile(r"^prov[1-9][0-9]*$"), _NOTE),
    ("expl", re.compile(r"^expl[1-9][0-9]*$"), _NOTE),
    ("reg", re.compile(r"^reg[1-9][0-9]*[A-Z]{0,2}$"), _TOP),
    ("para", re.compile(r"^para[1-9][0-9]*[A-Z]{0,2}$"), _TOP),
    ("sch", re.compile(r"^sch[1-9][0-9]*[A-Z]?$"), _TOP),
    ("form", re.compile(r"^form_[a-z0-9]+$"), _TOP),
    ("s", re.compile(r"^s[1-9][0-9]*[A-Z]{0,2}$"), _TOP),
    ("r", re.compile(r"^r[1-9][0-9]*[A-Z]{0,2}$"), _TOP),
)

_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class InvalidSectionUidError(ValueError):
    """Raised when a string is not a canonical section_uid or chunk_id."""


def _segment_kind(segment: str) -> tuple[str, int]:
    for kind, pattern, level in _SEGMENTS:
        if pattern.match(segment):
            return kind, level
    raise InvalidSectionUidError(f"unknown segment {segment!r}")


@dataclass(frozen=True, slots=True)
class SectionUid:
    """A parsed section_uid. Build with :func:`parse`; ``str()`` gives the canonical form."""

    jurisdiction: str
    instrument_code: str  # code + year, e.g. "RTI2005"
    segments: tuple[str, ...] = ()

    @property
    def instrument_id(self) -> str:
        return f"{self.jurisdiction}.{self.instrument_code}"

    @property
    def year(self) -> int:
        return int(self.instrument_code[-4:])

    def __str__(self) -> str:
        return ":".join((self.instrument_id, *self.segments))


def parse(text: str) -> SectionUid:
    """Parse and validate a canonical section_uid. Raises InvalidSectionUidError."""
    if not text or not text.isascii() or text != text.strip():
        raise InvalidSectionUidError(f"not a canonical ASCII uid: {text!r}")
    head, *segments = text.split(":")
    match = _INSTRUMENT_RE.match(head)
    if match is None:
        raise InvalidSectionUidError(f"bad instrument id {head!r} (want e.g. 'IN.RTI2005')")
    jurisdiction = match["jur"]
    if jurisdiction not in JURISDICTIONS:
        raise InvalidSectionUidError(f"unknown jurisdiction {jurisdiction!r}")

    previous: tuple[str, int] | None = None
    for segment in segments:
        kind, level = _segment_kind(segment)
        if previous is None:
            if level != _TOP:
                raise InvalidSectionUidError(f"{segment!r} cannot be the first segment")
        else:
            prev_kind, prev_level = previous
            if prev_level == _NOTE:
                raise InvalidSectionUidError("a proviso/explanation must be the last segment")
            # The one top-level-under-top-level case: paragraphs inside a schedule.
            schedule_paragraph = prev_kind == "sch" and kind == "para"
            if level <= prev_level and not schedule_paragraph:
                raise InvalidSectionUidError(f"{segment!r} cannot follow {prev_kind!r}")
            if level == _SUBCLAUSE and prev_kind not in _CLAUSE_KINDS:
                raise InvalidSectionUidError("a sub-clause must follow a clause")
        previous = (kind, level)

    return SectionUid(jurisdiction, match["code"] + match["year"], tuple(segments))


def is_valid(text: str) -> bool:
    try:
        parse(text)
    except InvalidSectionUidError:
        return False
    return True


def parent(uid: str) -> str | None:
    """Parent provision computed from the uid itself (None for a whole instrument)."""
    parsed = parse(uid)
    if not parsed.segments:
        return None
    return str(SectionUid(parsed.jurisdiction, parsed.instrument_code, parsed.segments[:-1]))


def ancestors(uid: str) -> list[str]:
    """All ancestors, nearest first, ending with the instrument id."""
    result: list[str] = []
    current = parent(uid)
    while current is not None:
        result.append(current)
        current = parent(current)
    return result


def covers(retrieved: str, expected: str) -> bool:
    """Eval rule (DEC-040 point 4): equal to, or an ancestor of, the expected unit."""
    a, b = parse(retrieved), parse(expected)
    if a.instrument_id != b.instrument_id:
        return False
    return b.segments[: len(a.segments)] == a.segments


def belongs_to(uid: str, instrument_id: str) -> bool:
    return parse(uid).instrument_id == instrument_id


_UNDATED_RE = re.compile(r"^nd-[0-9a-f]{8}$")
_PART_RE = re.compile(r"^[1-9][0-9]*$")


@dataclass(frozen=True)
class ChunkId:
    """Parsed ``chunk_id`` (DEC-040, DEC-055 item 7d and item 3).

    ``version`` is the legal date the text version starts, or ``"nd-<8 hex>"`` (first 8 hex
    digits of the document sha256) when no legal date is known. ``part`` is set only when one
    clause was too long and had to be split (``~n`` suffix).
    """

    uid: SectionUid
    lang: str
    version: date | str
    part: int | None = None


def make_chunk_id(uid: str, lang: str, version: date | str, part: int | None = None) -> str:
    """``<section_uid>@<lang>@<YYYY-MM-DD | nd-xxxxxxxx>[~n]``. Validates every part."""
    parse(uid)
    if lang not in CHUNK_LANGUAGES:
        raise InvalidSectionUidError(f"unknown chunk language {lang!r}")
    if isinstance(version, date):
        ver = version.isoformat()
    elif _UNDATED_RE.match(version):
        ver = version
    else:
        raise InvalidSectionUidError(f"version must be a date or nd-<8 hex>: {version!r}")
    if part is not None and part < 2:
        raise InvalidSectionUidError("part suffix starts at 2 (the first piece has none)")
    return f"{uid}@{lang}@{ver}" + (f"~{part}" if part is not None else "")


def parse_chunk_id(chunk_id: str) -> ChunkId:
    parts = chunk_id.split("@")
    if len(parts) != 3:
        raise InvalidSectionUidError(f"chunk_id needs uid@lang@version: {chunk_id!r}")
    uid, lang, ver = parts
    part: int | None = None
    if "~" in ver:
        ver, _, n = ver.partition("~")
        if not _PART_RE.match(n) or int(n) < 2:
            raise InvalidSectionUidError(f"bad part suffix {n!r}")
        part = int(n)
    if lang not in CHUNK_LANGUAGES:
        raise InvalidSectionUidError(f"unknown chunk language {lang!r}")
    version: date | str
    if _UNDATED_RE.match(ver):
        version = ver
    else:
        if not _DATE_RE.match(ver):
            raise InvalidSectionUidError(f"bad version {ver!r}")
        try:
            version = date.fromisoformat(ver)
        except ValueError as exc:
            raise InvalidSectionUidError(f"bad date {ver!r}") from exc
    return ChunkId(parse(uid), lang, version, part)
