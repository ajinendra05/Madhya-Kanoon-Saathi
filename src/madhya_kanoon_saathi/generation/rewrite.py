"""Query rewriting before retrieval (E1 in docs/RERANKER.md; DEC-090).

Colloquial Hinglish ("dukaan vaale ne kharab saman diya") shares no words with statute text
("defective goods", "trader"), so the right provisions never reach the reranker. One short model
call turns the question into a formal English and a formal Hindi search query; retrieval searches
with the original *and* the rewrites and fuses all lists by RRF.

Rules: the rewrite is a search aid only. It is never shown to users, never cited, and never used by
the crisis router, dispute detector or jurisdiction guard (those read the user's own words). On any
failure (model error, budget cap, bad JSON) retrieval simply uses the original question.
"""

from __future__ import annotations

import json
from collections.abc import Callable

REWRITE_VERSION = "r1"
MAX_CHARS = 300

SYSTEM = """You turn a user's message about Indian or Madhya Pradesh law into search queries for a database of statutes, rules and official guides.
Return JSON only, exactly: {"en": "<English query>", "hi": "<Hindi query>"}
- "en": one English search query using the formal legal words a statute would use.
- "hi": the same query in Hindi (Devanagari script), also with formal legal words.
- Keep every fact the user gave. Add no facts, section numbers, amounts, dates or names of Acts that the user did not mention.
- Do not answer the question and do not give advice.
- Each query at most 25 words."""  # noqa: E501

Call = Callable[[list[dict[str, str]]], str]


def messages(question: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]


def parse(raw: str, question: str) -> list[str]:
    """English then Hindi query; empty, over-long, duplicate or non-string values are dropped."""
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(data, dict):
        return []
    out: list[str] = []
    seen = {question.strip().casefold()}
    for key in ("en", "hi"):
        v = data.get(key)
        if isinstance(v, str) and v.strip() and len(v) <= MAX_CHARS:
            v = " ".join(v.split())
            if v.casefold() not in seen:
                seen.add(v.casefold())
                out.append(v)
    return out


def rewrite(question: str, call: Call) -> list[str]:
    """Search rewrites for ``question``; [] if the call fails for any reason."""
    try:
        return parse(call(messages(question)), question)
    except Exception:
        return []
