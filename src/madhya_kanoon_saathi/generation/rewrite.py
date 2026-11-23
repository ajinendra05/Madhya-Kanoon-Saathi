"""Query rewriting before retrieval (E1 in docs/RERANKER.md; DEC-090, DEC-091).

Colloquial Hinglish ("dukaan vaale ne kharab saman diya") shares no words with statute text
("defective goods", "trader"), so the right provisions never reach the reranker. One short model
call turns the question into a formal English and a formal Hindi search query; retrieval searches
with the original *and* the rewrites and fuses all lists by RRF.

Prompt r1 is in use (DEC-093): on 50 golden questions it beat r2 (R@6 0.713 vs 0.563). The r2
machinery stays for later experiments: if a reply carries an ``acts`` list, each name is matched
against the instruments we index (official title or alias, :func:`act_catalog`) and only matches
are used; r1 does not ask for that list, so nothing is appended today.

Rules: the rewrite is a search aid only. It is never shown to users, never cited, and never used by
the crisis router, dispute detector or jurisdiction guard (those read the user's own words). On any
failure (model error, budget cap, bad JSON) retrieval simply uses the original question.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from madhya_kanoon_saathi.common.normalize import normalize

REWRITE_VERSION = "r1"  # DEC-093: r1 kept (r2 measured worse)
MAX_CHARS = 300
MAX_ACTS = 3

SYSTEM = """You turn a user's message about Indian or Madhya Pradesh law into search queries for a database of statutes, rules and official guides.
Return JSON only, exactly: {"en": "<English query>", "hi": "<Hindi query>"}
- "en": one English search query using the formal legal words a statute would use.
- "hi": the same query in Hindi (Devanagari script), also with formal legal words.
- Keep every fact the user gave. Add no facts, section numbers, amounts, dates or names of Acts that the user did not mention.
- Do not answer the question and do not give advice.
- Each query at most 25 words."""  # noqa: E501

Call = Callable[[list[dict[str, str]]], str]
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_ACT_NO = re.compile(r"\(\s*act\s+no\.?[^)]*\)", re.IGNORECASE)


@dataclass(frozen=True)
class Act:
    instrument_id: str
    title_en: str
    title_hi: str | None = None


@dataclass
class Rewrite:
    queries: list[str] = field(default_factory=list)  # what retrieval searches with
    acts: list[Act] = field(default_factory=list)  # names that matched our corpus
    dropped_acts: list[str] = field(default_factory=list)  # names we do not hold


def _key(text: str) -> str:
    """Comparison form of a law name: folded, lower case, no year, no "(Act No. …)", no "the".
    Other brackets stay: "(E-Commerce)" and "(Jurisdiction …)" tell Rules apart."""
    t = normalize(text, fold_nukta=True).casefold()
    t = _ACT_NO.sub(" ", t)
    t = re.sub(r"\b(1[89]|20)\d\d\b", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\b(the|of|act no)\b", " ", t)
    return " ".join(t.split())


def act_catalog(
    manifest: Mapping[str, Any], aliases: Mapping[str, Any], live_modes: Iterable[str] = ("index",)
) -> dict[str, Act]:
    """Comparison key -> Act, for instruments with an indexed document (titles and aliases)."""
    modes = set(live_modes)
    live = {d["instrument_id"] for d in manifest["documents"] if d.get("mode") in modes}
    out: dict[str, Act] = {}
    for inst in manifest["instruments"]:
        iid = inst["instrument_id"]
        if iid not in live or not inst.get("title_en"):
            continue
        clean_en = " ".join(_ACT_NO.sub(" ", inst["title_en"]).split())
        act = Act(iid, clean_en, inst.get("title_hi"))
        names = [inst["title_en"], inst.get("title_hi") or ""]
        names += (aliases.get("aliases", {}).get(iid) or {}).get("aliases", [])
        for n in names:
            k = _key(n)
            if len(k) >= 3:
                out.setdefault(k, act)
    return out


def match_act(name: str, catalog: Mapping[str, Act]) -> Act | None:
    """Exact key match, else one key contained in the other with at least two words in common."""
    k = _key(name)
    if not k:
        return None
    if k in catalog:
        return catalog[k]
    words = set(k.split())
    for ck, act in catalog.items():
        common = words & set(ck.split())
        if len(common) >= 2 and (ck in k or k in ck):
            return act
    return None


def messages(question: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]


def parse(raw: str, question: str, catalog: Mapping[str, Act] | None = None) -> Rewrite:
    """English then Hindi query (+ matched official titles); bad or copied values are dropped.
    Free models sometimes wrap the JSON in prose or code fences: the outermost {...} is used."""
    try:
        data = json.loads(raw)
    except ValueError:
        m = _JSON_OBJECT.search(raw)
        try:
            data = json.loads(m.group()) if m else None
        except ValueError:
            data = None
    if not isinstance(data, dict):
        return Rewrite()
    rw = Rewrite()
    for name in (data.get("acts") or [])[:MAX_ACTS] if isinstance(data.get("acts"), list) else []:
        if not isinstance(name, str) or not name.strip():
            continue
        act = match_act(name, catalog or {})
        if act is None:
            rw.dropped_acts.append(name.strip()[:80])
        elif act not in rw.acts:
            rw.acts.append(act)
    seen = {question.strip().casefold()}
    for lang in ("en", "hi"):
        v = data.get(lang)
        if not (isinstance(v, str) and v.strip() and len(v) <= MAX_CHARS):
            continue
        v = " ".join(v.split())
        titles = [a.title_en if lang == "en" else a.title_hi for a in rw.acts]
        extra = " ".join(t for t in titles if t)
        q = f"{v} {extra}".strip()
        if q.casefold() not in seen:
            seen.add(q.casefold())
            rw.queries.append(q)
    return rw


def rewrite_full(
    question: str,
    call: Call,
    catalog: Mapping[str, Act] | None = None,
    on_error: Callable[[Exception], None] | None = None,
) -> Rewrite:
    """The whole rewrite (queries + act matches); empty if the call fails for any reason.
    ``on_error`` sees the failure (log its type), so silent fallbacks cannot hide an outage."""
    try:
        return parse(call(messages(question)), question, catalog)
    except Exception as e:
        if on_error is not None:
            on_error(e)
        return Rewrite()


def rewrite(
    question: str,
    call: Call,
    on_error: Callable[[Exception], None] | None = None,
    catalog: Mapping[str, Act] | None = None,
) -> list[str]:
    """Search queries only (see :func:`rewrite_full`)."""
    return rewrite_full(question, call, catalog, on_error).queries


def titles_of(acts: Sequence[Act]) -> list[str]:
    return [a.instrument_id for a in acts]
