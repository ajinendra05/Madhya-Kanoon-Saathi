"""Redaction before anything is stored or logged (DEC-029, DEC-033 item 4, DEC-076).

``redact(text)`` replaces, in place:

- **PII** (fixed patterns, most specific first): card number → ``[CARD]``, Aadhaar → ``[AADHAAR]``,
  phone → ``[PHONE]``, e-mail → ``[EMAIL]``, UPI id → ``[UPI]``, PAN → ``[PAN]``, other long
  digit runs (bank account) → ``[ACCOUNT]``;
- **sensitive categories** a user may volunteer: caste/tribe category → ``[CASTE]``, religion →
  ``[RELIGION]``, disability → ``[DISABILITY]``, health condition → ``[HEALTH]``.

Only the specific *value* is removed, never the topic: "जाति प्रमाण पत्र", "SC/ST Act", "Hindu
Succession Act", "disability certificate" stay, because they name a law or a service. Ambiguous
cases are redacted (privacy is the safe direction). Known gap: specific caste and community names
are not in the v1 lists (OPEN_QUESTIONS). The text used *within* a session is not changed; only
what is written to logs, traces and DynamoDB passes through here.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

# Devanagari digits are read as ASCII for detection (the replaced span keeps its position)
_DIGITS = "[0-9०-९]"  # noqa: RUF001
_SEP = r"[ \-]?"

_LAW_OR_SERVICE = (
    # "SC/ST Act": skip chained categories before the law/service word
    r"(?![ \-/]*(?:(?:sc|st|obc)\b[ \-/]*)*"
    r"(act|एक्ट|अधिनियम|law|लॉ|kanoon|कानून|certificate|सर्टिफिकेट|प्रमाण|"
    r"marriage act|succession|personal law|पर्सनल|विवाह अधिनियम|उत्तराधिकार|आरक्षण|reservation|"
    r"scheme|योजना|hostel|छात्रावास|scholarship|छात्रवृत्ति|commission|आयोग|thana|थाना))"
)

_PII: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", re.compile(r"\b[\w.+\-]+@[\w\-]+(\.[\w\-]+)+\b")),
    ("UPI", re.compile(r"\b[\w.\-]{2,}@[A-Za-z]{2,20}(?![\w.@])")),
    ("CARD", re.compile(rf"(?<![0-9०-९])(?:{_DIGITS}{{4}}{_SEP}){{3}}{_DIGITS}{{4}}(?![0-9०-९])")),  # noqa: RUF001
    ("AADHAAR", re.compile(rf"(?<![0-9०-९])[2-9२-९]{_DIGITS}{{3}}{_SEP}{_DIGITS}{{4}}{_SEP}{_DIGITS}{{4}}(?![0-9०-९])")),  # noqa: RUF001,E501
    ("PHONE", re.compile(rf"(?<![0-9०-९])(?:\+?91{_SEP}|0)?[6-9६-९]{_DIGITS}{{4}}{_SEP}{_DIGITS}{{5}}(?![0-9०-९])")),  # noqa: RUF001,E501
    ("PAN", re.compile(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b")),
    ("ACCOUNT", re.compile(rf"(?<![0-9०-९]){_DIGITS}{{9,18}}(?![0-9०-९])")),  # noqa: RUF001
)  # fmt: skip

_SENSITIVE: dict[str, tuple[str, ...]] = {
    "CASTE": (
        r"\b(SC|ST|OBC)\b" + _LAW_OR_SERVICE,
        r"दलित", r"आदिवासी" + _LAW_OR_SERVICE, r"अनुसूचित (जन)?जाति" + _LAW_OR_SERVICE,
        r"(अन्य )?पिछड(ा|े|ी) वर्ग" + _LAW_OR_SERVICE, r"हरिजन",
        r"\b(dalit|adivasi|harijan)\b", r"\bscheduled (caste|tribe)s?\b" + _LAW_OR_SERVICE,
        r"\b(backward class|other backward)\b" + _LAW_OR_SERVICE,
    ),
    "RELIGION": (
        r"(हिंदू|हिन्दू|मुस्लिम|मुसलमान|इस्लाम|ईसाई|क्रिश्चियन|सिख|जैन|बौद्ध|पारसी)" + _LAW_OR_SERVICE,
        r"\b(hindu|muslim|musalman|islam|islamic|christian|isai|sikh|jain|buddhist|parsi)\b"
        + _LAW_OR_SERVICE,
    ),
    "DISABILITY": (
        r"विकलांग(?!ता)" + _LAW_OR_SERVICE, r"दिव्यांग(?!ता)" + _LAW_OR_SERVICE, r"अपंग",
        r"नेत्रहीन", r"दृष्टिबाधित", r"(अंधा|अंधी|बहरा|बहरी|गूंगा|गूंगी)", r"पोलियो",
        r"\b(disabled|handicapped|blind|deaf|mute|wheelchair|polio|paralys\w*)\b",
        r"\b(viklang|divyang)\b" + _LAW_OR_SERVICE,
    ),
    "HEALTH": (
        r"(एचआईवी|एड्स|कैंसर|टीबी|क्षय रोग|मधुमेह|डायबिटीज|मिर्गी|डिप्रेशन|अवसाद|मानसिक (रोग|बीमारी)|"
        r"गर्भवती|गर्भपात|डायलिसिस|हेपेटाइटिस|कुष्ठ)",
        r"\b(hiv|aids|cancer|tb|tuberculosis|diabetes|diabetic|epilep\w*|depression|"
        r"schizophren\w*|bipolar|pregnant|pregnancy|abortion|dialysis|hepatitis|leprosy)\b",
    ),
}  # fmt: skip

_COMPILED = {k: tuple(re.compile(p, re.IGNORECASE) for p in pats) for k, pats in _SENSITIVE.items()}


@dataclass
class Redacted:
    text: str
    found: Counter[str] = field(default_factory=Counter)  # placeholder -> count

    @property
    def sensitive(self) -> bool:
        return any(k in self.found for k in _SENSITIVE)


def redact(text: str) -> Redacted:
    """Text safe to store or log, and what was replaced (counts only, never the values)."""
    out = unicodedata.normalize("NFC", text)
    found: Counter[str] = Counter()
    for label, pat in _PII:
        out, n = pat.subn(f"[{label}]", out)
        found[label] += n
    for label, pats in _COMPILED.items():
        for pat in pats:
            out, n = pat.subn(f"[{label}]", out)
            found[label] += n
    return Redacted(text=out, found=Counter({k: v for k, v in found.items() if v}))
