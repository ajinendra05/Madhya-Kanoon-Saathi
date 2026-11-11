"""Hindi-aware BM25 tokeniser (DEC-026). The same code runs at index time and at query time.

Steps, in order:
1. Shared normaliser with nukta folding (DEC-054: comparison keys are folded).
2. Devanagari digits -> ASCII ("धारा ३३(१)" -> "धारा 33(1)").
3. Latin text lowercased.
4. Section references become one token plus their parts, after a single keyword token:
   "section 18(2)(f)" / "s. 18(2)(f)" / "धारा 18(2)(f)" / "dhara 18(2)(f)" ->
   ``section s18 s18_2 s18_2_f``. A bare reference with at least one bracket ("8(1)(j)") gives the
   same parts without the keyword. Clause letters stay in their own script (a Hindi letter is never
   mapped to a Latin one, DEC-040).
5. धारा / section / sec / s. / dhara alone also map to the one keyword token ``section``.
6. Words = runs of Latin letters, digits and Devanagari letters/marks (danda excluded).
7. A small Hindi/English stop-word list is removed. Legal words such as "not", "no", "shall",
   "नहीं" are kept on purpose.

``provision_tokens(section_uid)`` gives the reference tokens of a chunk's own provision
(``IN.RTI2005:s8:ss1:cl_j`` -> ``s8 s8_1 s8_1_j``) so a query for "8(1)(j)" can match the chunk even
when its text never repeats its own number.
"""

from __future__ import annotations

import re

from madhya_kanoon_saathi.common.normalize import normalize

KEYWORD = "section"
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_KEYWORDS = r"(?:section|sec|s|dhara|धारा)"
_PART = r"\(\s*([0-9a-zऀ-ॣ०-ॿ]{1,6})\s*\)"
_REF_KW = re.compile(
    rf"(?<![0-9a-zऀ-ॿ]){_KEYWORDS}\s*\.?\s*(\d{{1,4}}[a-z]{{0,2}})((?:\s*{_PART})*)"
)
_REF_BARE = re.compile(rf"(?<![0-9a-zऀ-ॿ.])(\d{{1,4}}[a-z]{{0,2}})((?:\s*{_PART})+)")
_PARTS = re.compile(_PART)
_WORD = re.compile(r"[0-9a-zऀ-ॣ०-ॿ]+")
_KEYWORD_WORDS = {"section", "sec", "dhara", "धारा"}  # "s" alone is too common to map

STOPWORDS_EN = frozenset(
    [
        "a",
        "an",
        "the",
        "of",
        "and",
        "or",
        "to",
        "in",
        "on",
        "at",
        "by",
        "for",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "with",
        "which",
        "who",
        "whom",
        "whose",
        "any",
        "such",
        "than",
        "into",
        "upon",
        "under",
    ]
)
STOPWORDS_HI = frozenset(
    [
        "का",
        "की",
        "के",
        "को",
        "में",
        "से",
        "पर",
        "और",
        "है",
        "हैं",
        "था",
        "थे",
        "थी",
        "या",
        "यह",
        "ये",
        "वह",
        "वे",
        "एक",
        "इस",
        "उस",
        "इन",
        "उन",
        "भी",
        "तो",
        "ही",
        "लिए",
        "द्वारा",
        "तथा",
        "एवं",
        "अथवा",
        "जो",
        "जिस",
        "जिन",
    ]
)
STOPWORDS = STOPWORDS_EN | STOPWORDS_HI


def _ref_tokens(num: str, parts_text: str) -> list[str]:
    out = [f"s{num}"]
    acc = f"s{num}"
    for p in _PARTS.findall(parts_text):
        acc = f"{acc}_{p}"
        out.append(acc)
    return out


def prepare(text: str) -> str:
    """Steps 1-3: normalise, ASCII digits, lowercase."""
    return normalize(text, fold_nukta=True).translate(_DEV_DIGITS).lower()


def tokenize(text: str) -> list[str]:
    s = prepare(text)
    out: list[str] = []
    pos = 0
    spans: list[tuple[int, int, list[str]]] = []
    for m in _REF_KW.finditer(s):
        spans.append((m.start(), m.end(), [KEYWORD, *_ref_tokens(m.group(1), m.group(2))]))
    taken = [(a, b) for a, b, _ in spans]
    for m in _REF_BARE.finditer(s):
        if not any(a <= m.start() < b for a, b in taken):
            spans.append((m.start(), m.end(), _ref_tokens(m.group(1), m.group(2))))
    for a, b, toks in sorted(spans):
        out += _words(s[pos:a])
        out += toks
        pos = b
    out += _words(s[pos:])
    return out


def _words(s: str) -> list[str]:
    toks = []
    for w in _WORD.findall(s):
        if w in _KEYWORD_WORDS:
            toks.append(KEYWORD)
        elif w not in STOPWORDS:
            toks.append(w)
    return toks


def provision_tokens(section_uid: str) -> list[str]:
    """Reference tokens of a chunk's own provision, matching what tokenize() makes of a citation."""
    segs = section_uid.split(":")[1:]
    if not segs:
        return []
    head = segs[0]
    m = re.match(r"^(s|r|para|sch|reg)(\d+[A-Za-z]{0,2})$", head)
    if not m:
        return []
    base = (m.group(1) if m.group(1) != "s" else "s") + m.group(2).lower()
    out = [base]
    acc = base
    for seg in segs[1:]:
        if seg.startswith(("prov", "expl")):
            break
        label = re.sub(r"^(ss|sp|cl_|clr_|scl_|scla_|para)", "", seg).lower()
        acc = f"{acc}_{label}"
        out.append(acc)
    return out
