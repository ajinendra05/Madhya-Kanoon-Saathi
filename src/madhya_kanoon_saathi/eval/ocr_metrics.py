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

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from madhya_kanoon_saathi.common.normalize import normalize


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
