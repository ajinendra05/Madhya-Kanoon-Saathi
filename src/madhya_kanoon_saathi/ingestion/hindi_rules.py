"""Hindi rules texts: parsing and structural alignment with the English text (W1.1b).

Spec: ``docs/specs/section_uid.md`` rule 2 ("Hindi chunks get uids by matching the English
structure position by position; never map Devanagari clause letters to Latin ones") and
``docs/specs/chunks.md``.

1. :func:`parse_hindi_rules` builds a provision tree from Hindi lines (OCR, :mod:`ocr_text`):
   rules "3. आवेदन फीस <dash> text", sub-rules "(1)", clauses in any printed numbering — Devanagari
   letters "(क)", Hindi number words "(एक)", roman "(i)" — provisos "परंतु", explanations
   "स्पष्टीकरण", forms "प्ररूप-एक" / appendix "परिशिष्ट", schedules "अनुसूची—एक". Labels are kept
   only to check the printed sequence; they never become uid segments.
2. :func:`align` gives every Hindi node the uid of its English counterpart:
   - rules and sub-rules by their **number** (printed digits are the same in both languages);
   - clauses, provisos and explanations by **position** among siblings of the same kind;
   - forms and schedules by order of appearance (the appendix to ``form_appendix``).
   Where the counts differ, the Hindi node keeps its own aligned uid and its whole subtree is
   kept as one unit (coarser, never wrong); each such case is reported.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from madhya_kanoon_saathi.common.section_uid import parent
from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import _ROMAN, Parsed, Unit, visible_text

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
HINDI_LETTERS = tuple(
    [
        "क",
        "ख",
        "ग",
        "घ",
        "ङ",
        "च",
        "छ",
        "ज",
        "झ",
        "ञ",
        "ट",
        "ठ",
        "ड",
        "ढ",
        "ण",
        "त",
        "थ",
        "द",
        "ध",
        "न",
        "प",
        "फ",
        "ब",
        "भ",
        "म",
        "य",
        "र",
        "ल",
        "व",
        "श",
        "ष",
        "स",
        "ह",
    ]
)
HINDI_NUMBERS = (
    ("एक",),
    ("दो",),
    ("तीन",),
    ("चार",),
    ("पांच", "पाँच"),
    ("छह", "छः", "छ:"),
    ("सात",),
    ("आठ",),
    ("नौ",),
    ("दस",),
    ("ग्यारह",),
    ("बारह",),
    ("तेरह",),
    ("चौदह",),
    ("पंद्रह", "पन्द्रह"),
    ("सोलह",),
    ("सत्रह",),
    ("अठारह",),
    ("उन्नीस",),
    ("बीस",),
)
_RULE = re.compile(r"^(\d{1,3})\s*\.\s*(\S.*)$")
_SUBRULE = re.compile(r"^\((\d{1,3})\)\s*(.*)$")
_ITEM = re.compile(r"^\(\s*([^\s()]{1,8})\s*\)\s*(.*)$")
# no \b: Python's word boundary does not fire after a vowel sign such as "ु"
_PROVISO = re.compile(r"^पर(न्|ं)तु(?=[\s,:]|$)")  # "परंतुक" (a proviso, as a noun) is not a start
_EXPLAN = re.compile(r"^स्पष्टीकरण(?=[\s.,:–—-]|$)")  # noqa: RUF001
# "(i) के परंतुक के अनुसरण में": a wrapped cross-reference, not a clause (IN.CPJR2021 p.2)
_XREF_TAIL = re.compile(r"^(के|की|का|में|से|द्वारा|अधीन|या|और|तथा|,)(?=[\s,]|$)")
# "शीर्षक –", "शीर्षक —", "शीर्षक. –", "शीर्षक - ", "शीर्षक -- (1)" (IN.CPECR2020 r.2), "शीर्षक:-"  # noqa: RUF003
_HEAD_DASH = re.compile(r"\s*\.?\s*[–—]\s*|\s+-{1,3}\s+|[.:]\s*-+\s*")  # noqa: RUF001
_FORM = re.compile(r"^(प्ररूप|प्रपत्र)\s*[-–—]?\s*(\S{1,8})?\s*$")  # noqa: RUF001
_APPENDIX = re.compile(r"^परिशिष्ट\s*[-–—]?\s*(\S{1,8})?\s*$")  # noqa: RUF001
_SCHEDULE = re.compile(r"^अनुसूची\s*[-–—]?\s*(\S{1,8})?\s*$")  # noqa: RUF001
_CHAPTER = re.compile(r"^अध्याय\s*[-–—]?\s*\S{1,8}\s*$")  # noqa: RUF001
_END = re.compile(
    r"^(फा\.\s*सं|मध्यप्रदेश\s+के\s+राज्यपाल\s+के\s+नाम\s+से|नियंत्रक,\s*शासकीय\s+मुद्रण|"
    r"\S.{0,40},\s*(संयुक्त|उप|अवर)\s*सचिव\s*$)"
)  # signature block and printer's line
_MAX_HEAD_WORDS = 14


@dataclass
class HNode:
    kind: str  # rule | ss | item | prov | expl | form | appendix | schedule
    label: str  # as printed ("3", "(1)", "(ख)", "परंतु", "प्ररूप-एक")
    num: int = 0  # rule / sub-rule number
    heading: str = ""
    chapter: str = ""
    lines: list[tuple[int, Line]] = field(default_factory=list)  # (document position, line)
    children: list[HNode] = field(default_factory=list)
    parent: HNode | None = None
    uid: str = ""

    def add(self, child: HNode) -> HNode:
        child.parent = self
        self.children.append(child)
        return child

    def subtree_lines(self) -> list[tuple[int, Line]]:
        out = list(self.lines)
        for c in self.children:
            out += c.subtree_lines()
        return sorted(out, key=lambda x: x[0])


@dataclass
class HParsed:
    roots: list[HNode]
    unassigned: list[Line]
    trailing: list[Line]


def item_system(label: str) -> tuple[str, int] | None:
    """(numbering system, 0-based position) of a printed clause label, or None."""
    if label in HINDI_LETTERS:
        return "hl", HINDI_LETTERS.index(label)
    for i, forms in enumerate(HINDI_NUMBERS):
        if label in forms:
            return "hw", i
    if label in _ROMAN:
        return "rom", _ROMAN[label] - 1
    if len(label) == 1 and "a" <= label <= "z":
        return "la", ord(label) - ord("a")
    return None


def _text(line: Line) -> str:
    t = visible_text(line)
    t = t[1:].lstrip() if t.startswith("[") else t
    return t.translate(_DEV_DIGITS)


def _split_heading(rest: str) -> tuple[str, str]:
    """("heading", "tail") when a dash ends a short heading, else ("", rest)."""
    if _SUBRULE.match(rest):
        return "", rest
    m = _HEAD_DASH.search(rest)
    if m and 0 < len(rest[: m.start()].split()) <= _MAX_HEAD_WORDS:
        return rest[: m.start()].strip(" ."), rest[m.end() :]
    return "", rest


def parse_hindi_rules(lines: Sequence[Line]) -> HParsed:
    """Parse Hindi rules lines (body lines only) into a provision tree."""
    roots: list[HNode] = []
    unassigned: list[Line] = []
    trailing: list[Line] = []
    rule: HNode | None = None
    ss: HNode | None = None
    clause: HNode | None = None
    cur: HNode | None = None
    block: HNode | None = None  # open form / appendix / schedule
    clause_sys: tuple[str, int] | None = None  # (system, last position)
    sub_sys: tuple[str, int] | None = None
    after_clause: list[HNode] = []
    last_rule = 0
    last_ss = 0
    chapter = ""
    pending_chapter = False
    signed = False

    def owner() -> HNode:
        assert rule is not None
        return ss if ss is not None else rule

    for pos, ln in enumerate(lines):
        if ln.kind != "body":
            continue
        t = _text(ln)
        m_form, m_app, m_sch = _FORM.match(t), _APPENDIX.match(t), _SCHEDULE.match(t)
        if (m_form or m_app or m_sch) and (rule is not None or block is not None):
            kind = "form" if m_form else "appendix" if m_app else "schedule"
            block = HNode(kind, t)
            roots.append(block)
            rule = ss = clause = None
            cur, signed = block, False
            block.lines.append((pos, ln))
            continue
        if _END.match(t):
            signed = True
        if signed:
            trailing.append(ln)
            continue
        if block is not None:
            block.lines.append((pos, ln))
            continue
        if _CHAPTER.match(t):
            pending_chapter = True
            chapter = t
            continue
        if pending_chapter:
            chapter, pending_chapter = f"{chapter} — {t}", False
            continue

        m_r = _RULE.match(t)
        if m_r:
            num = int(m_r.group(1))
            if (last_rule == 0 and num == 1) or (last_rule < num <= last_rule + 3):
                heading, tail = _split_heading(m_r.group(2))
                rule = HNode("rule", str(num), num=num, heading=heading, chapter=chapter)
                roots.append(rule)
                last_rule, last_ss = num, 0
                ss = clause = None
                clause_sys = sub_sys = None
                after_clause = []
                cur = rule
                m_ss = _SUBRULE.match(tail)
                if m_ss and m_ss.group(1) == "1":
                    ss = cur = rule.add(HNode("ss", "(1)", num=1))
                    last_ss = 1
                cur.lines.append((pos, ln))
                continue
        if rule is None:
            unassigned.append(ln)
            continue

        m_ss = _SUBRULE.match(t)
        if m_ss and int(m_ss.group(1)) == last_ss + 1:
            last_ss = int(m_ss.group(1))
            ss = cur = rule.add(HNode("ss", f"({last_ss})", num=last_ss))
            clause = None
            clause_sys = sub_sys = None
            after_clause = []
            cur.lines.append((pos, ln))
            continue

        if _PROVISO.match(t) or _EXPLAN.match(t):
            kind = "prov" if _PROVISO.match(t) else "expl"
            cur = owner().add(HNode(kind, t.split()[0]))
            if clause is not None:
                after_clause.append(cur)
            cur.lines.append((pos, ln))
            continue

        m_it = _ITEM.match(t)
        if m_it and _XREF_TAIL.match(m_it.group(2)):
            m_it = None
        sysp = item_system(m_it.group(1)) if m_it else None
        if sysp is not None and cur is not None:
            system, idx = sysp
            next_main = (clause_sys is None and idx == 0) or (
                clause_sys is not None
                and system == clause_sys[0]
                and clause_sys[1] < idx <= clause_sys[1] + 2
            )
            # a proviso or explanation blocks a new sub-list, not the next main clause
            # (IN.CPECR2020 r.5(3): proviso after (क), then (ख) ... (घ))
            next_sub = (
                cur.kind not in ("prov", "expl")
                and clause is not None
                and (
                    (
                        sub_sys is None
                        and idx == 0
                        and (clause_sys is None or system != clause_sys[0])
                    )
                    or (
                        sub_sys is not None
                        and system == sub_sys[0]
                        and sub_sys[1] < idx <= sub_sys[1] + 2
                    )
                )
            )
            if next_sub and not next_main:
                assert clause is not None
                cur = clause.add(HNode("item", m_it.group(1) if m_it else ""))
                sub_sys = (system, idx)
                cur.lines.append((pos, ln))
                continue
            if next_main:
                prev = clause
                clause = cur = owner().add(HNode("item", m_it.group(1) if m_it else ""))
                if prev is not None and after_clause:
                    # provisos between two clauses belong to the earlier clause (as in English)
                    o = owner()
                    for u in after_clause:
                        o.children.remove(u)
                        prev.add(u)
                after_clause = []
                clause_sys, sub_sys = (system, idx), None
                cur.lines.append((pos, ln))
                continue

        if cur is None:
            cur = rule
        cur.lines.append((pos, ln))
    return HParsed(roots=roots, unassigned=unassigned, trailing=trailing)


def _category(uid: str) -> str:
    seg = uid.rsplit(":", 1)[1]
    if seg.startswith("ss"):
        return "ss"
    if seg.startswith(("cl_", "clr_", "scl_", "scla_")):
        return "item"
    if seg.startswith("prov"):
        return "prov"
    if seg.startswith("expl"):
        return "expl"
    return "other"


def align(instrument_id: str, hp: HParsed, english: Parsed) -> tuple[Parsed, list[str]]:
    """Assign English uids to the Hindi tree; return Hindi units in document order + a report."""
    report: list[str] = []
    en_uids = [u.uid for u in english.units]
    kids: dict[str, list[str]] = {}
    for uid in en_uids:
        p = parent(uid)
        if p is not None:
            kids.setdefault(p, []).append(uid)
    out: list[Unit] = []

    def collapse(h: HNode, why: str) -> None:
        report.append(f"{h.uid}: kept whole in Hindi ({why})")
        h.lines = h.subtree_lines()
        h.children = []

    def walk(h: HNode, uid: str) -> None:
        h.uid = uid
        en_kids = kids.get(uid, [])
        pairs: list[tuple[HNode, str]] = []
        ok = True
        for cat in ("ss", "item", "prov", "expl"):
            hk = [c for c in h.children if c.kind == cat]
            ek = [e for e in en_kids if _category(e) == cat]
            if cat == "ss":
                ek_by_num = {int(re.sub(r"\D", "", e.rsplit(":", 1)[1])): e for e in ek}
                if sorted(c.num for c in hk) != sorted(ek_by_num):
                    ok = False
                    break
                pairs += [(c, ek_by_num[c.num]) for c in hk]
            elif len(hk) != len(ek):
                ok = False
                break
            else:
                pairs += list(zip(hk, ek, strict=True))
        other = [e for e in en_kids if _category(e) == "other"]
        if not ok or (other and h.children):
            collapse(h, f"Hindi and English sub-units differ under {uid}")
            return
        for c, e in pairs:
            walk(c, e)

    en_rules = {
        u.uid.rsplit(":", 1)[1]: u.uid for u in english.units if parent(u.uid) == instrument_id
    }
    en_forms = [u for u in en_rules.values() if ":form_" in u and not u.endswith("appendix")]
    en_sched = [u for u in en_rules.values() if ":sch" in u]
    blocks = {"form": iter(en_forms), "schedule": iter(en_sched)}
    for h in hp.roots:
        if h.kind == "rule":
            uid = en_rules.get(f"r{h.num}", f"{instrument_id}:r{h.num}")
            if uid not in en_uids:
                h.uid = uid
                collapse(h, "no English rule with this number")
            else:
                walk(h, uid)
        elif h.kind == "appendix":
            uid = f"{instrument_id}:form_appendix"
            if uid not in en_uids:
                report.append(f"{h.label}: no English appendix; not chunked")
                continue
            h.uid = uid
        else:
            nxt = next(blocks[h.kind], None)
            if nxt is None:
                report.append(f"{h.label}: no English {h.kind} at this position; not chunked")
                continue
            h.uid = nxt

    def emit(h: HNode) -> None:
        if not h.uid:
            return
        kind = {
            "rule": "section",
            "form": "schedule",
            "appendix": "schedule",
            "item": "clause",
        }.get(h.kind, h.kind)
        u = Unit(
            uid=h.uid,
            kind=kind,
            label=h.label,
            heading=h.heading,
            chapter=h.chapter,
            lines=[ln for _, ln in sorted(h.lines, key=lambda x: x[0])],
        )
        u.para_restart = h.kind in ("form", "appendix", "schedule")
        out.append(u)
        for c in h.children:
            emit(c)

    for h in hp.roots:
        emit(h)
    return Parsed(units=out, unassigned=list(hp.unassigned), trailing=list(hp.trailing)), report
