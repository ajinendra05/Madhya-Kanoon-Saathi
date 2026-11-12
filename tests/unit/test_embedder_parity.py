"""Embedding parity (DEC-022): vectors computed here must match the reference written at index build.

Run explicitly (loads a 0.6-2.3 GB model):
    MKS_PARITY=1 uv run pytest -m slow tests/unit/test_embedder_parity.py
Later the same test runs inside the Lambda image (CI), so build-time and query-time vectors agree.
"""

import json
import os
from pathlib import Path

import numpy as np
import pytest

REC = Path("data/parsed_manifest")
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("MKS_PARITY"), reason="set MKS_PARITY=1 to load the models"
    ),
]


@pytest.mark.parametrize("variant", ["int8", "fp32"])
def test_vectors_match_build_reference(variant: str) -> None:
    from madhya_kanoon_saathi.retrieval.embedder import Embedder

    ref_file = REC / f"parity_{variant}.json"
    if not ref_file.exists():
        pytest.skip(f"no reference yet: run scripts/build_dense.py {variant}")
    ref = json.loads(ref_file.read_text(encoding="utf-8"))
    got = Embedder.load(variant).encode(ref["sentences"])
    want = np.asarray(ref["vectors"], dtype=np.float32)
    cos = (got * want).sum(axis=1)
    assert cos.min() >= 0.9999, cos
    assert float(np.abs(got - want).max()) <= 1e-3
