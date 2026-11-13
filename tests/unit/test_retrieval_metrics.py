"""Retrieval metrics (DEC-065) on hand-worked examples with real uids."""

import math

import pytest

from madhya_kanoon_saathi.eval.retrieval_metrics import (
    RowScore,
    lenient,
    score_row,
    strict,
    summarise,
)

S81 = "IN.RTI2005:s8:ss1"
S81J = "IN.RTI2005:s8:ss1:cl_j"
CPA = "IN.CPA2019:s8:ss1"


def test_matchers() -> None:
    assert strict(S81, S81J) and lenient(S81, S81J)  # chunk contains the expected clause
    assert not strict(S81J, S81) and lenient(S81J, S81)  # chunk is only part of it
    assert not lenient(CPA, S81)  # same numbers, different Act
    assert strict("IN.RTI2005", S81J)  # act-level chunk/uid covers everything in the Act


def test_first_rank_hit() -> None:
    s = score_row([S81, CPA], [S81J], strict)
    assert s == RowScore(1.0, 1.0, 1.0)


def test_hit_at_rank_three_and_miss_under_strict() -> None:
    s = score_row([CPA, "IN.CPA2019:s2", S81J], [S81], lenient)
    assert s.recall == 1.0 and s.mrr == pytest.approx(1 / 3)
    assert s.ndcg == pytest.approx(1 / math.log2(4))
    assert score_row([CPA, "IN.CPA2019:s2", S81J], [S81], strict) == RowScore(0.0, 0.0, 0.0)


def test_two_expected_partial_and_no_double_gain() -> None:
    exp = ["IN.LSA1987:s12", "IN.LSA1987:s13"]
    got = ["IN.LSA1987:s12", "IN.LSA1987:s12", CPA]
    s = score_row(got, exp, strict)
    assert s.recall == 0.5 and s.mrr == 1.0
    assert s.ndcg == pytest.approx(1.0 / (1.0 + 1 / math.log2(3)))  # second s12 chunk adds nothing


def test_cutoff_k() -> None:
    got = [CPA] * 10 + [S81J]
    assert score_row(got, [S81J], strict, k=10).recall == 0.0
    assert score_row(got, [S81J], strict, k=11).recall == 1.0


def test_empty_expected_rejected_and_summary() -> None:
    with pytest.raises(ValueError):
        score_row([S81], [], strict)
    assert summarise([]).rows == 0
    m = summarise([RowScore(1.0, 1.0, 1.0), RowScore(0.0, 0.0, 0.0)])
    assert (m.rows, m.recall, m.mrr, m.ndcg) == (2, 0.5, 0.5, 0.5)
