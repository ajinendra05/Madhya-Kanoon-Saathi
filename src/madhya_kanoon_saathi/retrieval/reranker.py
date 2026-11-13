"""Cross-encoder reranking with bge-reranker-v2-m3 on onnxruntime (DEC-005, DEC-021, DEC-062).

A cross-encoder reads the question and one passage *together* and outputs one relevance logit
(higher = more relevant; only the order matters, the scale is not a probability). It is far more
accurate than comparing two separately made vectors, but costs one model run per passage, so it
only re-sorts the small fused pool (top-40, or top-20 when latency needs it, DEC-021).

Verified 2026-11-13 on the Colab export of BAAI/bge-reranker-v2-m3 revision 953dc6f6
(data/models/bge-reranker-v2-m3/export_info.json): inputs ``input_ids``, ``attention_mask``
(int64), output ``logits`` (batch, 1); ONNX vs PyTorch max abs diff 4.3e-6 on 4 pairs.
The pair is tokenised by ``tokenizer.json`` as ``<s> query </s></s> passage </s>``.

``load`` refuses model files whose sha256 differs from data/parsed_manifest/models.json.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

RECORD = Path("data/parsed_manifest/models.json")
VARIANTS = {"fp32": ("bge-reranker-v2-m3-fp32", "model.onnx"),
            "int8": ("bge-reranker-v2-m3-int8", "model.int8.onnx")}  # fmt: skip
MAX_LENGTH = 1024  # question + passage tokens; longer passages lose their tail (counted in stats)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@dataclass
class RerankStats:
    pairs: int
    truncated: int


class Reranker:
    def __init__(
        self, session: ort.InferenceSession, tokenizer: Tokenizer, variant: str, max_length: int
    ) -> None:
        pad = tokenizer.token_to_id("<pad>")
        if pad is None:
            raise ValueError("tokenizer has no <pad> token")
        self.session = session
        self.tokenizer = tokenizer
        self.variant = variant
        self.max_length = max_length
        self.pad_id = pad
        self.last_stats = RerankStats(0, 0)

    @classmethod
    def load(
        cls,
        variant: str = "int8",
        *,
        verify: bool = True,
        max_length: int = MAX_LENGTH,
        threads: int | None = None,
    ) -> Reranker:
        key, model_file = VARIANTS[variant]
        entry = json.loads(RECORD.read_text(encoding="utf-8"))[key]
        folder = Path(entry["dir"])
        if verify:
            for f in entry["files"]:
                if _sha256(folder / f["file"]) != f["sha256"]:
                    raise RuntimeError(f"{variant}: checksum mismatch for {f['file']}")
        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        session = ort.InferenceSession(
            str(folder / model_file), opts, providers=["CPUExecutionProvider"]
        )
        tok = Tokenizer.from_file(str(folder / "tokenizer.json"))
        tok.no_padding()
        tok.no_truncation()
        return cls(session, tok, variant, max_length)

    def score(self, query: str, passages: Sequence[str], batch_size: int = 1) -> np.ndarray:
        """One logit per passage, in input order.

        batch_size 1 is fastest on CPU (measured 2026-11-13, i5-1155G7, 20 passages: 5.4 s at 1,
        6.2 s at 8, 13.9 s at 20): padding a batch to its longest pair wastes work.
        """
        if not passages:
            return np.zeros(0, dtype=np.float32)
        q_ids = self.tokenizer.encode(query).ids  # <s> q </s>
        p_encs = self.tokenizer.encode_batch(list(passages))  # <s> p </s> each
        room = self.max_length - len(q_ids) - 1  # pair = <s> q </s> + </s> p </s>
        if room < 8:
            raise ValueError("query too long for the reranker window")
        seqs: list[list[int]] = []
        truncated = 0
        for e in p_encs:
            body = e.ids[1:]  # drop <s>; keep p ... </s>
            if len(body) > room:
                truncated += 1
                body = [*body[: room - 1], body[-1]]  # keep the closing </s>
            seqs.append([*q_ids, q_ids[-1], *body])
        order = np.argsort([len(s) for s in seqs], kind="stable")
        out = np.zeros(len(seqs), dtype=np.float32)
        for start in range(0, len(order), batch_size):
            idx = order[start : start + batch_size]
            width = max(len(seqs[i]) for i in idx)
            ids = np.full((len(idx), width), self.pad_id, dtype=np.int64)
            mask = np.zeros((len(idx), width), dtype=np.int64)
            for r, i in enumerate(idx):
                ids[r, : len(seqs[i])] = seqs[i]
                mask[r, : len(seqs[i])] = 1
            (logits,) = self.session.run(["logits"], {"input_ids": ids, "attention_mask": mask})
            out[idx] = np.asarray(logits, dtype=np.float32).reshape(-1)
        self.last_stats = RerankStats(len(seqs), truncated)
        return out

    def rerank(
        self, query: str, items: Sequence[tuple[str, str]], top: int = 6
    ) -> list[tuple[str, float]]:
        """(id, passage) pairs -> best ``top`` as (id, logit); ties keep input order."""
        scores = self.score(query, [text for _, text in items])
        order = np.argsort(-scores, kind="stable")[:top]
        return [(items[i][0], float(scores[i])) for i in order]
