"""Paired comparison of two retrieval configs on the same golden rows (DEC-021, DEC-066 step 5).

Used for the int8-vs-fp32 decision: int8 is accepted only if its Recall@10 is no more than
``TOLERANCE`` below fp32, overall and per language (DEC-021). DEC-066 adds:
- per slice: questions, clause hits/misses per config, and paired disagreements
  (rows where one config recalls more than the other);
- a paired bootstrap confidence interval for the mean difference (resample rows, keep pairs);
- a slice with fewer than ``MIN_VERIFIED`` verified questions gets ``insufficient_sample``
  instead of pass/fail; pass/fail is computed on the verified rows only.

Paired bootstrap: draw n rows with replacement, average the per-row differences a - b, repeat;
the 2.5th and 97.5th percentiles give a 95% interval. Pairing removes the between-question
variance that both configs share, so the interval is much tighter than comparing two means.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

TOLERANCE = 0.02  # DEC-021: a may be at most 0.02 below b
MIN_VERIFIED = 50  # DEC-066 item 6: verified questions per slice before pass/fail
N_BOOT = 10_000
SEED = 20261114  # fixed, so reports are reproducible


@dataclass(frozen=True)
class PairRow:
    """One golden row scored by both configs (recall in [0, 1]; hits = expected clauses found)."""

    row_id: str
    slice: str
    verified: bool
    expected: int
    hits_a: int
    hits_b: int

    @property
    def recall_a(self) -> float:
        return self.hits_a / self.expected

    @property
    def recall_b(self) -> float:
        return self.hits_b / self.expected


@dataclass(frozen=True)
class SliceResult:
    name: str
    questions: int
    verified: int
    clauses: int
    hits_a: int
    hits_b: int
    recall_a: float
    recall_b: float
    diff: float  # mean(recall_a - recall_b) over all rows of the slice
    ci_low: float
    ci_high: float
    a_better: int  # rows where a recalls more than b
    b_better: int
    verdict: str  # pass | fail | insufficient_sample
    verified_diff: float | None  # the diff the verdict uses (verified rows only)


def bootstrap_ci(
    diffs: Sequence[float], n_boot: int = N_BOOT, seed: int = SEED, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile CI of the mean of paired differences; (0, 0) for an empty slice."""
    d = np.asarray(diffs, dtype=np.float64)
    if d.size == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, d.size, size=(n_boot, d.size))].mean(axis=1)
    low, high = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return (float(low), float(high))


def verdict(
    verified_diff: float | None,
    n_verified: int,
    min_verified: int = MIN_VERIFIED,
    tolerance: float = TOLERANCE,
) -> str:
    if verified_diff is None or n_verified < min_verified:
        return "insufficient_sample"
    return "pass" if verified_diff >= -tolerance - 1e-12 else "fail"


def compare_slice(
    name: str, rows: Sequence[PairRow], min_verified: int = MIN_VERIFIED
) -> SliceResult:
    diffs = [r.recall_a - r.recall_b for r in rows]
    ver = [r.recall_a - r.recall_b for r in rows if r.verified]
    n = len(rows)
    low, high = bootstrap_ci(diffs)
    vdiff = sum(ver) / len(ver) if ver else None
    return SliceResult(
        name=name,
        questions=n,
        verified=len(ver),
        clauses=sum(r.expected for r in rows),
        hits_a=sum(r.hits_a for r in rows),
        hits_b=sum(r.hits_b for r in rows),
        recall_a=sum(r.recall_a for r in rows) / n if n else 0.0,
        recall_b=sum(r.recall_b for r in rows) / n if n else 0.0,
        diff=sum(diffs) / n if n else 0.0,
        ci_low=low,
        ci_high=high,
        a_better=sum(d > 0 for d in diffs),
        b_better=sum(d < 0 for d in diffs),
        verdict=verdict(vdiff, len(ver), min_verified),
        verified_diff=vdiff,
    )


def compare(rows: Sequence[PairRow], min_verified: int = MIN_VERIFIED) -> list[SliceResult]:
    """Overall first, then one result per slice (sorted by name)."""
    out = [compare_slice("overall", rows, min_verified)]
    for name in sorted({r.slice for r in rows}):
        out.append(compare_slice(name, [r for r in rows if r.slice == name], min_verified))
    return out


def accepted(results: Sequence[SliceResult]) -> str:
    """DEC-021 decision over all slices: pass only if every slice passes."""
    verdicts = {r.verdict for r in results}
    if "fail" in verdicts:
        return "fail"
    if verdicts == {"pass"}:
        return "pass"
    return "insufficient_sample"
