"""Deterministic retrieval metrics (plan §7, DEC-065). No LLM, so they run in CI.

Per golden row: ``expected`` = provision uids the answer needs, ``retrieved`` = ranked
section_uids of the returned chunks. A chunk *matches* an expected uid when
- strict (DEC-040): ``covers(chunk, expected)``: the chunk is the provision or contains it;
- lenient: strict, or the chunk is a part of the expected provision (descendant).

Metrics are averaged over rows:
- Recall@k: share of expected uids matched by some top-k chunk.
- MRR@k: 1 / rank of the first chunk matching any expected uid (0 if none in the top k).
- nDCG@k: binary gain; a chunk gains only if it matches an expected uid not matched higher up,
  so several chunks of one provision do not inflate the score. IDCG = min(|expected|, k) hits.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from madhya_kanoon_saathi.common.section_uid import covers

Matcher = Callable[[str, str], bool]  # (retrieved, expected) -> match


def strict(retrieved: str, expected: str) -> bool:
    return covers(retrieved, expected)


def lenient(retrieved: str, expected: str) -> bool:
    return covers(retrieved, expected) or covers(expected, retrieved)


MATCHERS: dict[str, Matcher] = {"strict": strict, "lenient": lenient}


@dataclass(frozen=True)
class RowScore:
    recall: float
    mrr: float
    ndcg: float


def score_row(
    retrieved: Sequence[str], expected: Sequence[str], match: Matcher, k: int = 10
) -> RowScore:
    if not expected:
        raise ValueError("a row needs at least one expected uid")
    top = list(retrieved[:k])
    matched: set[str] = set()
    first_rank = 0
    dcg = 0.0
    for rank, uid in enumerate(top, start=1):
        hits = [e for e in expected if match(uid, e)]
        if hits and not first_rank:
            first_rank = rank
        new = [e for e in hits if e not in matched]
        if new:
            matched.update(new)
            dcg += 1.0 / math.log2(rank + 1)
    ideal = sum(1.0 / math.log2(r + 1) for r in range(1, min(len(set(expected)), k) + 1))
    return RowScore(
        recall=len(matched) / len(set(expected)),
        mrr=1.0 / first_rank if first_rank else 0.0,
        ndcg=dcg / ideal,
    )


@dataclass(frozen=True)
class Summary:
    rows: int
    recall: float
    mrr: float
    ndcg: float


def summarise(scores: Sequence[RowScore]) -> Summary:
    n = len(scores)
    if n == 0:
        return Summary(0, 0.0, 0.0, 0.0)
    return Summary(
        n,
        sum(s.recall for s in scores) / n,
        sum(s.mrr for s in scores) / n,
        sum(s.ndcg for s in scores) / n,
    )
