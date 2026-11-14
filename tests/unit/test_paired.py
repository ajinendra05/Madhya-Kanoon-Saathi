"""Paired int8-vs-fp32 comparison (DEC-021, DEC-066 step 5)."""

import pytest

from madhya_kanoon_saathi.eval.paired import (
    PairRow,
    accepted,
    bootstrap_ci,
    compare,
    compare_slice,
    verdict,
)


def row(rid: str, sl: str, a: int, b: int, exp: int = 1, verified: bool = True) -> PairRow:
    return PairRow(rid, sl, verified, exp, a, b)


def test_counts_and_disagreements() -> None:
    rows = [
        row("1", "hi", 1, 1),
        row("2", "hi", 0, 1),
        row("3", "hi", 2, 1, exp=2),
        row("4", "hi", 0, 0),
    ]
    r = compare_slice("hi", rows, min_verified=1)
    assert (r.questions, r.clauses, r.hits_a, r.hits_b) == (4, 5, 3, 3)
    assert (r.a_better, r.b_better) == (1, 1)
    assert r.recall_a == pytest.approx((1 + 0 + 1 + 0) / 4)
    assert r.recall_b == pytest.approx((1 + 1 + 0.5 + 0) / 4)
    assert r.diff == pytest.approx(r.recall_a - r.recall_b)


def test_bootstrap_ci_brackets_the_mean_and_is_reproducible() -> None:
    diffs = [0.0] * 20 + [-1.0] * 2 + [1.0]
    low, high = bootstrap_ci(diffs)
    mean = sum(diffs) / len(diffs)
    assert low <= mean <= high and low < 0 < high
    assert bootstrap_ci(diffs) == (low, high)  # fixed seed


def test_bootstrap_ci_identical_configs_is_zero() -> None:
    assert bootstrap_ci([0.0] * 30) == (0.0, 0.0)
    assert bootstrap_ci([]) == (0.0, 0.0)


def test_verdict_rules() -> None:
    assert verdict(-0.02, 50) == "pass"  # exactly at the DEC-021 tolerance
    assert verdict(-0.0201, 50) == "fail"
    assert verdict(0.1, 49) == "insufficient_sample"
    assert verdict(None, 0) == "insufficient_sample"


def test_unverified_rows_never_decide() -> None:
    # 60 unverified rows where a is far worse: still insufficient_sample, not fail
    rows = [row(str(i), "en", 0, 1, verified=False) for i in range(60)]
    r = compare_slice("en", rows)
    assert r.verdict == "insufficient_sample" and r.verified == 0 and r.verified_diff is None
    assert r.diff == pytest.approx(-1.0)


def test_verdict_uses_verified_rows_only() -> None:
    rows = [row(f"v{i}", "en", 1, 1) for i in range(50)] + [
        row(f"u{i}", "en", 0, 1, verified=False) for i in range(10)
    ]
    r = compare_slice("en", rows)
    assert r.verified_diff == 0.0 and r.verdict == "pass"
    assert r.diff < 0  # the unverified rows still show in the exploratory numbers


def test_compare_slices_and_overall_decision() -> None:
    rows = [row(f"e{i}", "en", 1, 1) for i in range(50)] + [
        row(f"h{i}", "hi", 1, 1) for i in range(10)
    ]
    res = compare(rows)
    assert [r.name for r in res] == ["overall", "en", "hi"]
    assert [r.verdict for r in res] == ["pass", "pass", "insufficient_sample"]
    assert accepted(res) == "insufficient_sample"
    worse = [row(f"h{i}", "hi", 0, 1) for i in range(50)]
    assert accepted(compare(rows[:50] + worse)) == "fail"
    assert accepted(compare(rows[:50])) == "pass"
