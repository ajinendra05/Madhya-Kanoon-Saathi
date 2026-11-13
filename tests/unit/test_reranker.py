"""Reranker logic with a fake ONNX session; real-model checks only with MKS_PARITY=1."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from tokenizers import Tokenizer, models, pre_tokenizers, processors

from madhya_kanoon_saathi.retrieval.hybrid import FusedHit, rerank_hits
from madhya_kanoon_saathi.retrieval.reranker import Reranker

TOK_FILE = Path("data/models/bge-reranker-v2-m3/tokenizer.json")


def toy_tokenizer() -> Tokenizer:
    """XLM-R-like ids: <s>=0, <pad>=1, </s>=2; whitespace words; same pair template."""
    vocab = {"<s>": 0, "<pad>": 1, "</s>": 2, "[UNK]": 3}
    for w in [
        "rent",
        "notice",
        "tenant",
        "eviction",
        "legal",
        "aid",
        "free",
        "who",
        "gets",
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
    ]:
        vocab.setdefault(w, len(vocab))
    tok = Tokenizer(models.WordLevel(vocab, unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.post_processor = processors.TemplateProcessing(
        single="<s> $A </s>",
        pair="<s> $A </s> </s> $B </s>",
        special_tokens=[("<s>", 0), ("</s>", 2)],
    )
    return tok


class FakeSession:
    """Logit = number of query-word ids that also occur in the passage part; records batches."""

    def __init__(self) -> None:
        self.batches: list[np.ndarray] = []

    def run(self, outputs: list[str], feeds: dict[str, np.ndarray]) -> list[Any]:
        assert outputs == ["logits"]
        ids, mask = feeds["input_ids"], feeds["attention_mask"]
        self.batches.append(ids)
        scores = []
        for row, m in zip(ids, mask, strict=True):
            seq = [int(x) for x, keep in zip(row, m, strict=True) if keep]
            first_end = seq.index(2)
            q = set(seq[1:first_end])
            p = set(seq[first_end + 2 : -1])
            scores.append([float(len(q & p))])
        return [np.array(scores, dtype=np.float32)]


def make(max_length: int = 64) -> tuple[Reranker, FakeSession]:
    s = FakeSession()
    return Reranker(s, toy_tokenizer(), "fake", max_length), s  # type: ignore[arg-type]


def test_pairs_follow_the_tokenizer_pair_template() -> None:
    r, s = make()
    r.score("free legal aid", ["legal aid", "rent notice"])
    tok = toy_tokenizer()
    want = {tuple(tok.encode("free legal aid", p).ids) for p in ["legal aid", "rent notice"]}
    got = {
        tuple(int(x) for x, m in zip(row, row != 1, strict=True) if m)
        for b in s.batches
        for row in b
    }
    assert got == want


def test_scores_in_input_order_and_rerank_sorts() -> None:
    r, _ = make()
    passages = ["rent notice", "free legal aid who gets", "legal aid"]
    assert list(r.score("who gets free legal aid", passages)) == [0.0, 5.0, 2.0]
    assert r.rerank("who gets free legal aid", list(zip("xyz", passages, strict=True)), top=2) == [
        ("y", 5.0),
        ("z", 2.0),
    ]


def test_padding_and_batches() -> None:
    r, s = make()
    r.score("a", ["a", "a b c d e f", "a b"], batch_size=2)
    assert len(s.batches) == 2
    assert all(row[-1] in (1, 2) for b in s.batches for row in b)  # padded with <pad>=1


def test_long_passage_truncated_keeps_closing_token() -> None:
    r, s = make(max_length=16)
    r.score("legal aid", ["a b c d e f g h a b c d e f g h"])
    row = [int(x) for x in s.batches[0][0]]
    assert len(row) == 16 and row[-1] == 2
    assert r.last_stats.truncated == 1 and r.last_stats.pairs == 1


def test_empty_and_too_long_query() -> None:
    r, _ = make(max_length=12)
    assert r.score("legal", []).shape == (0,)
    with pytest.raises(ValueError, match="query too long"):
        r.score("a b c d e f g h", ["a"])


def test_rerank_hits_keeps_rrf_fields_and_sets_score() -> None:
    r, _ = make()
    hits = [FusedHit("c1", 0.03, {"bm25": 1}), FusedHit("c2", 0.02, {"dense": 1}, ["draft"])]
    out = rerank_hits(r, "free legal aid", hits, {"c1": "rent notice", "c2": "free legal aid"}, k=1)
    assert [h.chunk_id for h in out] == ["c2"]
    assert out[0].rerank_score == 3.0 and out[0].flags == ["draft"] and out[0].ranks == {"dense": 1}
    with pytest.raises(KeyError):
        rerank_hits(r, "q", hits, {"c1": "x"}, k=1)


@pytest.mark.skipif(not TOK_FILE.exists(), reason="reranker tokenizer not downloaded")
def test_real_tokenizer_pair_matches_manual_construction() -> None:
    tok = Tokenizer.from_file(str(TOK_FILE))
    q, p = "मुफ्त कानूनी सहायता कौन ले सकता है?", "12. Criteria for giving legal services."
    manual = [*tok.encode(q).ids, tok.encode(q).ids[-1], *tok.encode(p).ids[1:]]
    assert manual == tok.encode(q, p).ids
    assert tok.token_to_id("<pad>") == 1


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("MKS_PARITY"), reason="set MKS_PARITY=1 to load the models")
@pytest.mark.parametrize("variant", ["fp32", "int8"])
def test_real_model_ranks_relevant_passage_first(variant: str) -> None:
    r = Reranker.load(variant)
    passages = [
        "The landlord shall not cut off or withhold any of the essential supplies or services",
        "12. Criteria for giving legal services.—Every person who has to file or defend a case "
        "shall be entitled to legal services under this Act if that person is a member of a "
        "Scheduled Caste or Scheduled Tribe",
    ]
    scores = r.score("मुफ्त कानूनी सहायता कौन ले सकता है?", passages)
    assert scores[1] > scores[0]
