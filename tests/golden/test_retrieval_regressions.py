"""Golden regression cases from S21 / DEC-067, run on the real indexes and int8 models.

Needs the git-ignored build outputs (chunks, indexes, models); skipped when they are missing.
Run with: ``uv run pytest -m golden tests/golden``. Each row checks the final top-6 that the
generator would see (``search_reranked``), on a fixed law date so the result is reproducible.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from madhya_kanoon_saathi.common.section_uid import covers

GOLDEN = Path("data/golden/v0.1-seed/golden_set_v0.1_seed.jsonl")
NEEDED = [
    Path("data/parsed/chunks.jsonl"),
    Path("data/index/bm25"),
    Path("data/index/dense-int8"),
    Path("data/parsed_manifest/models.json"),
]
ON = date(2026, 11, 14)

pytestmark = [
    pytest.mark.golden,
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(p.exists() for p in NEEDED), reason="indexes/models not built locally"
    ),
]


@pytest.fixture(scope="module")
def retriever() -> Any:
    from madhya_kanoon_saathi.retrieval.bm25_index import Bm25Index
    from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex
    from madhya_kanoon_saathi.retrieval.embedder import Embedder
    from madhya_kanoon_saathi.retrieval.hybrid import HybridRetriever, passages_from_chunks
    from madhya_kanoon_saathi.retrieval.reranker import Reranker

    chunks = [
        json.loads(x)
        for x in Path("data/parsed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    manifest = json.loads(Path("data/corpus_manifest.json").read_text(encoding="utf-8"))
    titles = {
        i["instrument_id"]: (i.get("title_en"), i.get("title_hi")) for i in manifest["instruments"]
    }
    return HybridRetriever(
        Bm25Index.load(Path("data/index/bm25")),
        DenseIndex.load(Path("data/index/dense-int8")),
        Embedder.load("int8"),
        Reranker.load("int8"),
        passages_from_chunks(chunks, titles),
    )


def row(rid: str) -> dict[str, Any]:
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["id"] == rid:
            return r
    raise KeyError(rid)


def top6(retriever: Any, rid: str) -> list[str]:
    hits = retriever.search_reranked(row(rid)["raw_question_redacted"], k=6, on=ON)
    return [h.chunk_id.split("@")[0] for h in hits]


def test_gs007_in_force_tpa_ranks_above_model_tenancy_act(retriever: Any) -> None:
    """Monthly-tenancy notice: TPA s.106(1) first, not the (non-binding) MTA (DEC-067 B)."""
    uids = top6(retriever, "GS-007")
    assert covers(uids[0], "IN.TPA1882:s106:ss1"), uids


def test_gs057_negligence_finds_deficiency_definition(retriever: Any) -> None:
    """Hospital negligence: CPA s.2(11) 'deficiency' (incl. negligence) in the top 6 (DEC-067 A)."""
    expected = [c["section_uid"] for c in row("GS-057")["expected_clauses"]]
    assert "IN.CPA2019:s2:ss11" in expected
    uids = top6(retriever, "GS-057")
    assert any(covers(u, "IN.CPA2019:s2:ss11") for u in uids), uids


@pytest.mark.xfail(
    strict=True,
    reason="vocabulary gap salary -> personal information; W2 query rewriting (DEC-067)",
)
def test_gs075_neighbour_salary_finds_rti_personal_information(retriever: Any) -> None:
    uids = top6(retriever, "GS-075")
    assert any(covers(u, "IN.RTI2005:s8:ss1:cl_j") for u in uids), uids
