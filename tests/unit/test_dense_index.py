"""Exact FAISS search (DEC-025) with the shared filters; vectors are synthetic (no model needed)."""

from datetime import date
from pathlib import Path

import numpy as np
import pytest

from madhya_kanoon_saathi.retrieval.dense_index import DenseIndex, l2_normalise

DAY = date(2026, 11, 12)
META = [
    {"chunk_id": "IN.RTI2005:s8:ss1@en@2025-11-13", "status": "in_force", "applies_to": {"level": "national"}},
    {"chunk_id": "MP.MWVDAOCT2026:s1@hi@2026-10-01", "status": "in_force",
     "applies_to": {"level": "state", "states": ["MP"]}, "valid_to": "2027-03-31"},
    {"chunk_id": "IN.MTA2021:s2@en@nd-e83830bf", "status": "model_law", "applies_to": {"level": "national"}},
]  # fmt: skip
VECS = np.array([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.6, 0.8, 0.0]], dtype=np.float32)


def test_normalise() -> None:
    assert np.allclose(np.linalg.norm(l2_normalise(VECS), axis=1), 1.0)


def test_exact_cosine_order_and_filters() -> None:
    ix = DenseIndex.build(VECS, META)
    hits = ix.search_vector(np.array([0.0, 1.0, 0.0]), on=DAY)
    assert [h.chunk_id[:15] for h in hits] == [
        "MP.MWVDAOCT2026",
        "IN.MTA2021:s2@e",
        "IN.RTI2005:s8:s",
    ]
    assert hits[0].score == pytest.approx(1.0) and hits[1].score == pytest.approx(0.8)
    assert hits[1].flags == ["model_law"]
    later = ix.search_vector(
        np.array([0.0, 1.0, 0.0]), on=date(2027, 4, 1)
    )  # wage notification expired
    assert [h.chunk_id[:2] for h in later] == ["IN", "IN"]


def test_length_mismatch_rejected() -> None:
    with pytest.raises(ValueError):
        DenseIndex.build(VECS[:2], META)


def test_save_load(tmp_path: Path) -> None:
    ix = DenseIndex.build(VECS, META)
    ix.save(tmp_path / "d")
    back = DenseIndex.load(tmp_path / "d")
    q = np.array([1.0, 0.1, 0.0])
    assert [h.chunk_id for h in back.search_vector(q, on=DAY)] == [
        h.chunk_id for h in ix.search_vector(q, on=DAY)
    ]
