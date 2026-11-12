"""BGE-M3 dense embeddings with onnxruntime (DEC-004, DEC-021, DEC-022, DEC-060).

Verified 2026-11-12 on BAAI/bge-m3 revision 5617a9f6:
- ONNX inputs ``input_ids``, ``attention_mask`` (int64); output ``sentence_embedding``
  (1024-d) equals the L2-normalised [CLS] token vector (cosine 1.0 with
  ``token_embeddings[:, 0]``), which is BGE-M3's dense representation.
- Queries need **no instruction prefix** (model card README line 85, same revision).
- The tokenizer (``tokenizer.json``, loaded with the ``tokenizers`` library, no torch) adds
  <s> ... </s>.

The same class serves the index build and query time; ``load`` refuses model files whose sha256
differs from data/parsed_manifest/models.json (DEC-022 checksum pinning).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

RECORD = Path("data/parsed_manifest/models.json")
VARIANTS = {"fp32": ("bge-m3-fp32", "onnx/model.onnx", "onnx/tokenizer.json"),
            "int8": ("bge-m3-int8", "model.int8.onnx", "tokenizer.json")}  # fmt: skip
PAD_ID = 1  # XLM-R <pad> (config.json pad_token_id)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


EMBED_FORMAT = "title / heading path joined with > / text, one per line (DEC-061)"


def embed_text(
    chunk: Mapping[str, Any], titles: Mapping[str, tuple[str | None, str | None]]
) -> str:
    """Text given to the model for a chunk (DEC-061); stored chunk text is unchanged.

    Title in the chunk's language when the manifest has it, else English; queries get no prefix.
    """
    en, hi = titles.get(chunk["instrument_id"], (None, None))
    title = (hi if chunk.get("lang") == "hi" and hi else en) or ""
    path = " > ".join(chunk.get("path") or [])
    return "\n".join(p for p in (title, path, chunk["text"]) if p)


@dataclass
class EncodeStats:
    texts: int
    truncated: int


class Embedder:
    def __init__(
        self, session: ort.InferenceSession, tokenizer: Tokenizer, variant: str, max_length: int
    ) -> None:
        self.session = session
        self.tokenizer = tokenizer
        self.variant = variant
        self.max_length = max_length
        self.last_stats = EncodeStats(0, 0)

    @classmethod
    def load(
        cls,
        variant: str = "int8",
        *,
        verify: bool = True,
        max_length: int = 1024,
        threads: int | None = None,
    ) -> Embedder:
        key, model_file, tok_file = VARIANTS[variant]
        entry = json.loads(RECORD.read_text(encoding="utf-8"))[key]
        folder = Path(entry["dir"])
        if verify:
            for f in entry["files"]:
                if _sha256(folder / f["file"]) != f["sha256"]:
                    raise RuntimeError(f"{variant}: checksum mismatch for {f['file']} (DEC-022)")
        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        session = ort.InferenceSession(
            str(folder / model_file), opts, providers=["CPUExecutionProvider"]
        )
        tok = Tokenizer.from_file(str(folder / tok_file))
        tok.no_padding()
        tok.no_truncation()
        return cls(session, tok, variant, max_length)

    def encode(self, texts: Sequence[str], batch_size: int = 16) -> np.ndarray:
        """L2-normalised float32 vectors, one per text, in input order."""
        encs = self.tokenizer.encode_batch(list(texts))
        truncated = sum(len(e.ids) > self.max_length for e in encs)
        order = np.argsort([len(e.ids) for e in encs], kind="stable")
        out = np.zeros((len(texts), 1024), dtype=np.float32)
        for start in range(0, len(order), batch_size):
            idx = order[start : start + batch_size]
            seqs = [encs[i].ids[: self.max_length] for i in idx]
            if any(len(s) == self.max_length for s in seqs):
                for s in seqs:  # keep the closing </s> on truncated sequences
                    if len(s) == self.max_length:
                        s[-1] = 2
            width = max(len(s) for s in seqs)
            ids = np.full((len(seqs), width), PAD_ID, dtype=np.int64)
            mask = np.zeros((len(seqs), width), dtype=np.int64)
            for r, s in enumerate(seqs):
                ids[r, : len(s)] = s
                mask[r, : len(s)] = 1
            (vecs,) = self.session.run(
                ["sentence_embedding"], {"input_ids": ids, "attention_mask": mask}
            )
            out[idx] = vecs
        self.last_stats = EncodeStats(len(texts), int(truncated))
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        normalised: np.ndarray = out / np.maximum(norms, 1e-12)
        return normalised
