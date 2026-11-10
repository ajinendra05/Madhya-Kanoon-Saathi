"""OCR metrics for the W0.5 bake-off (DEC-014, DEC-053): character and word error rate.

CER = character edit distance between hypothesis and reference / number of reference characters.
WER = the same over whitespace-separated words. Both can exceed 1.0 when the hypothesis is
much longer than the reference.

Characters are Unicode code points after NFC, so a Devanagari matra or virama counts as one
character (the usual convention for Indic CER). Each metric is reported twice (DEC-053): on raw
text with only whitespace collapsed, and on the shared normaliser's comparison form (nukta
folded, invisibles removed).
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from madhya_kanoon_saathi.common.normalize import normalize

SP_MARK = "▁"
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_TAG = re.compile(r"<[^>]+>")
_MD_PREFIX = re.compile(r"^\s{0,3}(#{1,6}\s+|>\s?|[-*+]\s+(?=\S))")
_EMPHASIS = re.compile(r"(\*\*|__|\*|`)")


def plain_text(markup: str) -> str:
    """Strip Markdown/HTML markup from engine output so all engines are scored as plain text.

    Ground-truth convention (data/ocr_gt/README.md): reading order, one table row per line,
    cells separated by spaces. So table pipes and separator rows are dropped, HTML cell/row
    tags become spaces/newlines, headings/emphasis/list markers are removed, entities decoded.
    U+2581 (the SentencePiece word marker that Bodhan IndicOCR leaves in its output instead of
    spaces, seen 2026-11-10) becomes a space first.
    """
    s = markup.replace(SP_MARK, " ")
    s = re.sub(r"(?i)<br\s*/?>|</(tr|p|div|h\d|li)>", "\n", s)
    s = re.sub(r"(?i)</t[dh]>", " ", s)
    s = html.unescape(_TAG.sub("", s))
    lines = []
    for line in s.splitlines():
        if _TABLE_RULE.match(line):
            continue
        line = _MD_PREFIX.sub("", line)
        line = _EMPHASIS.sub("", line.replace("|", " "))
        lines.append(" ".join(line.split()))
    return "\n".join(x for x in lines if x)


def edit_distance(ref: Sequence[str], hyp: Sequence[str]) -> int:
    """Levenshtein distance (unit costs) with two rolling rows: O(len(ref) * len(hyp)) time."""
    if len(ref) < len(hyp):
        ref, hyp = hyp, ref
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1]


def _raw(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def _norm(text: str) -> str:
    return normalize(text, collapse_space=True)


def error_rate(ref: Sequence[str], hyp: Sequence[str]) -> float:
    """Edit distance / len(ref). An empty reference gives 0.0 for an empty hypothesis, else 1.0."""
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)


@dataclass(frozen=True)
class OcrScores:
    cer_raw: float
    wer_raw: float
    cer_norm: float
    wer_norm: float
    ref_chars: int
    ref_words: int


def score(reference: str, hypothesis: str) -> OcrScores:
    """CER and WER of `hypothesis` against `reference`, raw and normalised."""
    r_raw, h_raw = _raw(reference), _raw(hypothesis)
    r_norm, h_norm = _norm(reference), _norm(hypothesis)
    return OcrScores(
        cer_raw=error_rate(r_raw, h_raw),
        wer_raw=error_rate(r_raw.split(), h_raw.split()),
        cer_norm=error_rate(r_norm, h_norm),
        wer_norm=error_rate(r_norm.split(), h_norm.split()),
        ref_chars=len(r_raw),
        ref_words=len(r_raw.split()),
    )
