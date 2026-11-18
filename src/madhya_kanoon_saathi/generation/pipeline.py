"""Answer pipeline for one question (W2.1). Retrieval and the LLM are passed in as functions, so the
whole flow runs offline in tests with recorded or fake outputs.

Order (CONCEPTS §2.3, DEC-033/074/075/076/077):

1. language (hi / hinglish / en);
2. **crisis router** before anything else — a rule-detected self-harm message gets only the crisis
   reply; other rule hits put the crisis text first; embedding-only hits add one safety line;
3. **jurisdiction guard** — a question about another state's law abstains;
4. **dispute detector** — the generator is told to give procedure only, and the referral is added;
5. retrieval → generation → **citation validator** (retry once, strip unsupported blocks, abstain
   if none remain);
6. rendering: answer blocks with exact quotes and section ids, a scan label for OCR chunks,
   status caveats, the RTI r.14 note, the wage qualification, "law as of", the footer.

All wording comes from ``data/answer_texts.json`` and ``data/safety/crisis_replies.json`` and is
used only when Malik has approved it (``allow_draft`` exists for local demos and tests).
The returned ``log`` holds the **redacted** question only (DEC-029/076).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np

from madhya_kanoon_saathi.common.redact import redact
from madhya_kanoon_saathi.generation import crisis, dispute, jurisdiction
from madhya_kanoon_saathi.generation.crisis import ExampleIndex
from madhya_kanoon_saathi.generation.prompt import build_messages
from madhya_kanoon_saathi.generation.validator import Validation, decide, validate

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_HINGLISH = re.compile(
    r"\b(hai|hain|kya|kaise|kaun|kitna|kitni|kitne|mein|mera|meri|mujhe|nahi|kab|kahan|karna|"
    r"karein|chahiye|wala|wale|ki|ka|ke|se|par|aur|bhi|ho|tha|thi|liye|milega|milegi)\b",
    re.IGNORECASE,
)
WAGE_DOC_PREFIX = "MP.MWVDA"
RTI_R14 = "IN.RTIR2012:r14"


@dataclass(frozen=True)
class Retrieved:
    """One retrieved chunk as the pipeline needs it (from chunks.jsonl + manifest)."""

    chunk_id: str
    text: str
    section_uid: str
    status: str = "in_force"
    extraction: str = ""
    pages: tuple[int, int] | None = None
    source_url: str = ""
    extra: Mapping[str, str] = field(default_factory=dict)  # e.g. notification, valid_from/to


Retriever = Callable[[str], Sequence[Retrieved]]
Generator = Callable[[list[dict[str, str]]], str]


@dataclass
class Reply:
    text: str
    abstained: bool
    reason: str | None
    log: dict[str, Any]


def detect_lang(text: str) -> str:
    if _DEVANAGARI.search(text):
        return "hi"
    return "hinglish" if len(_HINGLISH.findall(text)) >= 2 else "en"


def _approved(doc: Mapping[str, Any], allow_draft: bool) -> Mapping[str, Any]:
    if doc.get("status") != "approved" and not allow_draft:
        raise PermissionError("user-facing wording is not approved yet (answer_texts.json)")
    return doc


def _fill(template: str, values: Mapping[str, str]) -> str:
    return re.sub(r"\{([a-z0-9_]+)\}", lambda m: values.get(m.group(1), m.group(0)), template)


def _render_blocks(
    blocks: Sequence[dict[str, Any]],
    chunks: Mapping[str, Retrieved],
    lang: str,
    texts: Mapping[str, Any],
) -> list[str]:
    out = []
    for b in blocks:
        lines = [b["text"].strip()]
        for c in b["citations"]:
            r = chunks[c["chunk_id"]]
            cite = f"“{c['quote'].strip()}” [{r.section_uid}]"
            if r.extraction.startswith("ocr:"):
                page = str(r.pages[0]) if r.pages else "?"
                cite += " " + _fill(texts["scan_label"][lang], {"page": page, "url": r.source_url})
            lines.append(cite)
        out.append("\n".join(lines))
    return out


def _notes(
    used: Sequence[Retrieved], lang: str, texts: Mapping[str, Any], numbers: Mapping[str, str]
) -> list[str]:
    notes: list[str] = []
    for status in dict.fromkeys(r.status for r in used):
        if status in texts["status_caveat"]:
            notes.append(texts["status_caveat"][status][lang])
    if any(r.section_uid.startswith(RTI_R14) for r in used):
        notes.append(texts["rti_r14_note"][lang])
    for r in used:
        if r.chunk_id.startswith(WAGE_DOC_PREFIX):
            notes.append(_fill(texts["wage_qualification"][lang], {**r.extra, **numbers}))
            break
    return notes


def answer(
    question: str,
    *,
    retrieve: Retriever,
    generate: Generator,
    texts: Mapping[str, Any],
    crisis_replies: Mapping[str, Any],
    numbers: Mapping[str, str],
    today: date,
    query_vec: np.ndarray | None = None,
    crisis_examples: ExampleIndex | None = None,
    dispute_examples: ExampleIndex | None = None,
    allow_draft: bool = False,
) -> Reply:
    """Answer one question end to end; see the module docstring for the order of checks."""
    texts = _approved(texts, allow_draft)
    replies = {**crisis_replies, "status": "approved"} if allow_draft else crisis_replies
    lang = detect_lang(question)
    log: dict[str, Any] = {"question": redact(question).text, "lang": lang}
    nalsa = {"nalsa_15100": numbers.get("nalsa_15100", "")}

    cr = crisis.route(question, query_vec, crisis_examples)
    crisis_text = crisis.render(cr, lang, dict(replies), dict(numbers)) if cr.is_crisis else None
    log["crisis"] = {"tier": cr.tier, "categories": cr.categories}
    if crisis_text is not None and not crisis_text.legal_answer_allowed:
        return Reply(crisis_text.prefix or "", True, "self_harm", log)

    def wrap(body: list[str], abstained: bool, reason: str | None) -> Reply:
        parts = [crisis_text.prefix] if crisis_text and crisis_text.prefix else []
        parts += body
        if crisis_text and crisis_text.suffix:
            parts.append(crisis_text.suffix)
        parts.append(_fill(texts["footer"][lang], nalsa))
        return Reply("\n\n".join(p for p in parts if p), abstained, reason, log)

    jur = jurisdiction.check(question)
    log["states"] = list(jur.states)
    if jur.other_state_only:
        return wrap([texts["abstain"]["other_state"][lang]], True, "other_state")

    dp = dispute.route(question, query_vec, dispute_examples)
    log["dispute"] = {"flag": dp.is_dispute, "domains": list(dp.domains)}

    chunks = list(retrieve(question))
    by_id = {r.chunk_id: r for r in chunks}
    context = {r.chunk_id: r.text for r in chunks}
    log["retrieved"] = [r.chunk_id for r in chunks]
    if not chunks:
        return wrap([texts["abstain"]["no_support"][lang]], True, "nothing_retrieved")

    messages = build_messages(
        question, [(r.chunk_id, r.text) for r in chunks], lang, procedure_only=dp.is_dispute
    )
    first = _validate_raw(generate(messages), context)
    retry = None
    if not first.all_supported and not first.abstained:
        feedback = "; ".join(r for _, r in first.v.dropped) or "; ".join(first.v.errors)
        messages = [
            *messages,
            {
                "role": "user",
                "content": "Your previous answer had unsupported citations ("
                + feedback[:500]
                + "). Answer again; copy every quote exactly from one excerpt.",
            },
        ]
        retry = _validate_raw(generate(messages), context)
    if first.abstained and not first.v.supported:
        decision_blocks, abstain, reason, attempts = [], True, first.reason, 1
    else:
        d = decide(first.v, retry.v if retry else None)
        decision_blocks, abstain, reason, attempts = d.blocks, d.abstain, d.reason, d.attempts
    log["attempts"] = attempts
    log["abstain_reason"] = reason
    if abstain:
        return wrap([texts["abstain"]["no_support"][lang]], True, reason or "abstained")

    used = [by_id[c["chunk_id"]] for b in decision_blocks for c in b["citations"]]
    used = list({r.chunk_id: r for r in used}.values())
    log["cited"] = [r.chunk_id for r in used]
    body = _render_blocks(decision_blocks, by_id, lang, texts)
    body += _notes(used, lang, texts, numbers)
    if dp.is_dispute:
        body.append(_fill(texts["dispute_referral"][lang], nalsa))
    body.append(_fill(texts["law_as_of"][lang], {"date": today.isoformat()}))
    return wrap(body, False, None)


@dataclass
class _Raw:
    v: Validation
    abstained: bool
    reason: str | None

    @property
    def all_supported(self) -> bool:
        return self.v.all_supported


def _validate_raw(content: str, context: Mapping[str, str]) -> _Raw:
    try:
        ans = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return _Raw(validate(None, context), False, "invalid JSON")
    abstained = isinstance(ans, dict) and ans.get("abstain") is True
    reason = ans.get("abstain_reason") if isinstance(ans, dict) else None
    return _Raw(validate(ans, context), abstained, reason)
