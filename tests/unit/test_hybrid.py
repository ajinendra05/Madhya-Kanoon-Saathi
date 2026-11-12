"""RRF fusion (no models needed)."""

import pytest

from madhya_kanoon_saathi.retrieval.bm25_index import Hit
from madhya_kanoon_saathi.retrieval.hybrid import RRF_K, rrf


def hits(*ids: str) -> list[Hit]:
    return [Hit(i, 0.0) for i in ids]


def test_rrf_scores_and_order() -> None:
    fused = rrf({"bm25": hits("a", "b", "c"), "dense": hits("b", "d", "a")})
    by_id = {f.chunk_id: f for f in fused}
    assert by_id["b"].score == pytest.approx(1 / (RRF_K + 2) + 1 / (RRF_K + 1))
    assert by_id["a"].score == pytest.approx(1 / (RRF_K + 1) + 1 / (RRF_K + 3))
    assert [f.chunk_id for f in fused][:2] == ["b", "a"]  # found by both beats found by one
    assert by_id["d"].ranks == {"dense": 2} and by_id["a"].ranks == {"bm25": 1, "dense": 3}


def test_rrf_limit_and_flags() -> None:
    fused = rrf({"bm25": [Hit("x", 1.0, ["draft"])], "dense": hits("y", "z")}, limit=2)
    assert len(fused) == 2 and fused[0].chunk_id == "x" and fused[0].flags == ["draft"]


def test_rrf_empty() -> None:
    assert rrf({"bm25": [], "dense": []}) == []
