"""Deterministic citation validator (generation rules; DEC-054; plan §6).

Output contract of the generator::

    {"answer_blocks": [{"text": str, "citations": [{"chunk_id": str, "quote": str}]}],
     "abstain": bool, "abstain_reason": str | null, "escalation": str | null}

A block is **supported** only if it has at least one citation and every citation:

1. names a ``chunk_id`` that is in the retrieved context given to the generator;
2. has a quote of at least ``MIN_QUOTE_WORDS`` words that is an exact substring of that chunk's
   canonical text after the shared normaliser on both sides (NFC, invisible characters removed,
   nukta folded; whitespace collapsed), so a dropped nukta or a line break never fails a correct
   quote and a paraphrase never passes.

Policy (applied by :func:`decide`): first attempt valid → use it; otherwise retry once; on the
retry keep only supported blocks; abstain if none remain. Never weaken these checks to make a test
pass ("I don't trust the model to cite correctly; I verify it deterministically").
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from madhya_kanoon_saathi.common.normalize import normalize

MIN_QUOTE_WORDS = 3


def _key(text: str) -> str:
    return " ".join(normalize(text, fold_nukta=True).split())


@dataclass
class Validation:
    supported: list[dict[str, Any]] = field(default_factory=list)  # blocks that pass
    dropped: list[tuple[dict[str, Any], str]] = field(default_factory=list)  # (block, reason)
    errors: list[str] = field(default_factory=list)  # contract errors

    @property
    def all_supported(self) -> bool:
        return not self.dropped and not self.errors and bool(self.supported)


def check_citation(cit: Any, context: Mapping[str, str]) -> str | None:
    """Reason a citation fails, or None if it is supported."""
    if not isinstance(cit, dict) or not isinstance(cit.get("chunk_id"), str):
        return "citation without chunk_id"
    cid, quote = cit["chunk_id"], cit.get("quote")
    if cid not in context:
        return f"chunk_id {cid} not in retrieved context"
    if not isinstance(quote, str) or len(quote.split()) < MIN_QUOTE_WORDS:
        return f"quote for {cid} shorter than {MIN_QUOTE_WORDS} words"
    if _key(quote) not in _key(context[cid]):
        return f"quote not found verbatim in {cid}"
    return None


def validate(answer: Any, context: Mapping[str, str]) -> Validation:
    """Check one generator output against the retrieved context (chunk_id -> canonical text)."""
    v = Validation()
    if not isinstance(answer, dict):
        v.errors.append("answer is not a JSON object")
        return v
    blocks = answer.get("answer_blocks")
    if answer.get("abstain") is True:
        return v  # an abstention needs no citations
    if not isinstance(blocks, list) or not blocks:
        v.errors.append("answer_blocks missing or empty while abstain is false")
        return v
    for b in blocks:
        if not isinstance(b, dict) or not isinstance(b.get("text"), str) or not b["text"].strip():
            v.dropped.append((b, "block without text"))
            continue
        cits = b.get("citations")
        if not isinstance(cits, list) or not cits:
            v.dropped.append((b, "claim without citation"))
            continue
        reasons = [r for r in (check_citation(c, context) for c in cits) if r]
        if reasons:
            v.dropped.append((b, "; ".join(reasons)))
        else:
            v.supported.append(b)
    return v


@dataclass(frozen=True)
class Decision:
    blocks: list[dict[str, Any]]
    abstain: bool
    reason: str | None
    attempts: int


def decide(first: Validation, retry: Validation | None = None) -> Decision:
    """Apply the policy: valid first answer → use; else the retry, minus unsupported blocks;
    nothing left → abstain. ``retry`` is None when the first answer was valid or abstained."""
    if first.all_supported:
        return Decision(first.supported, False, None, 1)
    if retry is None:
        return Decision([], True, "first answer unsupported and no retry made", 1)
    if retry.supported:
        return Decision(retry.supported, False, None, 2)
    return Decision([], True, "no claim could be verified against the retrieved law", 2)
