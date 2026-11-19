"""Generator prompt and answer schema (W2.1). v1 approved by Malik 2026-11-18 (DEC-079); v2 written
from Malik's instructions of 2026-11-19 (DEC-080: claim-level blocks, short exact quotes, one
optional clarifying question) and adopted only if the eval improves.

The model sees only the retrieved chunks, each with its ``chunk_id``, and must answer in the output
contract below; :mod:`validator` then checks every citation deterministically.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

PROMPT_VERSION = "v2"  # v2 under test (DEC-080): claim-level blocks, short quotes, clarify field

ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer_blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "chunk_id": {"type": "string"},
                                "quote": {"type": "string"},
                            },
                            "required": ["chunk_id", "quote"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["text", "citations"],
                "additionalProperties": False,
            },
        },
        "clarify": {"type": ["string", "null"]},
        "abstain": {"type": "boolean"},
        "abstain_reason": {"type": ["string", "null"]},
    },
    "required": ["answer_blocks", "abstain", "abstain_reason"],
    "additionalProperties": False,
}

LANG_NAME = {
    "hi": "Hindi (Devanagari)",
    "hinglish": "Hinglish (Hindi in Roman script)",
    "en": "English",
}

SYSTEM_V1 = """You give legal INFORMATION (not legal advice) about Madhya Pradesh and central
Indian law. Use ONLY the excerpts provided. Each excerpt starts with a label like [E1].
Rules:
1. Every statement must be supported by an excerpt. Put it in an answer block and cite the label
   (e.g. "E1") with a quote copied EXACTLY, word for word, from that excerpt (at least 3 words,
   no changes, no translation).
2. If the excerpts do not answer the question, set abstain to true, give a short abstain_reason,
   and return no answer blocks. Never use outside knowledge, never guess amounts, dates or sections.
3. Do not say who is right in a dispute and do not predict outcomes; explain the procedure only.
4. Never ask for caste, religion, disability or health information. Never recommend private lawyers.
5. Write the answer text in {language}. Quotes stay in the excerpt's own language.
6. Keep it short: at most 4 answer blocks, plain words.
Return ONLY this JSON object, nothing else:
{{"answer_blocks": [{{"text": "<one or two sentences answering the question>",
   "citations": [{{"ref": "<label, e.g. E2>", "quote": "<exact words from that excerpt>"}}]}}],
 "abstain": false, "abstain_reason": null}}
Replace every <...> with real content; never output the placeholders themselves."""


SYSTEM_V2 = """You give legal INFORMATION (not legal advice) about Madhya Pradesh and central
Indian law. Use ONLY the excerpts provided. Each excerpt starts with a label like [E1].
Rules:
1. Split the answer into blocks with ONE independently checkable claim each (a fee, a time limit,
   who decides, where to apply ...). The citations of a block must together support EVERY claim in
   that block; if a sentence makes two claims from different excerpts, make two blocks.
2. Quotes: copy 5 to 20 CONSECUTIVE words exactly as they appear in one excerpt: no changes, no
   translation, no "..." or "***", never join words from different places. Prefer two short
   citations over one long quote.
3. If the question is ambiguous and the excerpts could answer it once one detail is known, you may
   instead ask ONE brief clarifying question in "clarify" (no answer blocks, abstain false).
4. If the excerpts cannot answer the question whatever the clarification, set abstain to true with
   a short abstain_reason and no answer blocks. Never use outside knowledge, never guess amounts,
   dates or sections.
5. Do not say who is right in a dispute and do not predict outcomes; explain the procedure only.
6. Never ask for caste, religion, disability or health information. Never recommend private lawyers.
7. Write the answer text and any clarifying question in {language}. Quotes stay in the excerpt's
   own language.
8. Keep it short: at most 5 answer blocks, plain words.
Return ONLY this JSON object, nothing else:
{{"answer_blocks": [{{"text": "<one claim answering part of the question>",
   "citations": [{{"ref": "<label, e.g. E2>", "quote": "<5-20 exact consecutive words>"}}]}}],
 "clarify": null, "abstain": false, "abstain_reason": null}}
Replace every <...> with real content; never output the placeholders themselves."""

PROCEDURE_ONLY = (
    "\n9. This question asks who is right or how a dispute will end. Do not answer that part;"
    " explain only the procedure the excerpts describe."
)


def build_messages(
    question: str,
    chunks: Sequence[tuple[str, str]],
    lang: str,
    *,
    procedure_only: bool = False,
) -> list[dict[str, str]]:
    """Messages for one question; ``chunks`` = (chunk_id, canonical text) as retrieved.

    Excerpts are labelled E1, E2, ... (see :func:`ref_map`): the model mangled long chunk ids in
    the first live eval (2026-11-18), so it cites short labels and code maps them back."""
    excerpts = "\n\n".join(f"[E{i}]\n{text}" for i, (_, text) in enumerate(chunks, 1))
    system = SYSTEM_V2.format(language=LANG_NAME.get(lang, "English"))
    if procedure_only:
        system += PROCEDURE_ONLY
    user = f"Law excerpts:\n\n{excerpts}\n\nQuestion: {question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def ref_map(chunks: Sequence[tuple[str, str]]) -> dict[str, str]:
    """Label -> chunk_id, as used in :func:`build_messages`."""
    return {f"E{i}": cid for i, (cid, _) in enumerate(chunks, 1)}
