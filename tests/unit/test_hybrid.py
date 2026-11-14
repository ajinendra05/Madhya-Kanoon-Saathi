"""RRF fusion (no models needed)."""

import pytest

from madhya_kanoon_saathi.retrieval.bm25_index import Hit
from madhya_kanoon_saathi.retrieval.filters import NOT_IN_FORCE
from madhya_kanoon_saathi.retrieval.hybrid import RRF_K, FusedHit, in_force_first, rerank_hits, rrf


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


# ---------------------------------------------------------------- in-force ordering (DEC-067)
class FakeReranker:
    """Scores passages by a fixed table; mimics Reranker.rerank (best first, stable ties)."""

    def __init__(self, scores: dict[str, float]) -> None:
        self.scores = scores

    def rerank(
        self, query: str, items: list[tuple[str, str]], top: int = 6
    ) -> list[tuple[str, float]]:
        ranked = sorted(items, key=lambda it: -self.scores[it[0]])
        return [(cid, self.scores[cid]) for cid, _ in ranked[:top]]


def fused(cid: str, *flags: str) -> FusedHit:
    return FusedHit(cid, 0.0, flags=list(flags))


def test_in_force_first_is_a_stable_partition() -> None:
    hs = [fused("mta1", "model_law"), fused("tpa"), fused("draft1", "draft"), fused("cpa")]
    assert [h.chunk_id for h in in_force_first(hs)] == ["tpa", "cpa", "mta1", "draft1"]


def test_sub_judice_is_in_force_and_not_demoted() -> None:
    hs = [fused("sj", "sub_judice_flag"), fused("act")]
    assert [h.chunk_id for h in in_force_first(hs)] == ["sj", "act"]
    assert "sub_judice_flag" not in NOT_IN_FORCE
    assert {"draft", "model_law", "enacted_not_commenced"} <= NOT_IN_FORCE


def test_rerank_hits_demotes_before_cutting_k() -> None:
    # GS-007 pattern: model-law chunks outscore the in-force TPA chunk, which sits outside top-2
    hits = [fused("mta29", "model_law"), fused("mta15", "model_law"), fused("tpa106"), fused("x")]
    rr = FakeReranker({"mta29": 1.0, "mta15": 0.5, "tpa106": -2.0, "x": -3.0})
    passages = {h.chunk_id: h.chunk_id for h in hits}
    best = rerank_hits(rr, "q", hits, passages, k=2)  # type: ignore[arg-type]
    assert [h.chunk_id for h in best] == ["tpa106", "x"]
    assert best[0].rerank_score == -2.0


def test_rerank_hits_keeps_not_in_force_when_nothing_else() -> None:
    hits = [fused("mta29", "model_law"), fused("mta15", "model_law")]
    rr = FakeReranker({"mta29": 0.1, "mta15": 0.9})
    best = rerank_hits(rr, "q", hits, {"mta29": "a", "mta15": "b"}, k=6)  # type: ignore[arg-type]
    assert [h.chunk_id for h in best] == ["mta15", "mta29"]
