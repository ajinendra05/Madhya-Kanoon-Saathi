"""Generator prompt and answer schema (W2.1). PROMPT_VERSION v0 is a DRAFT pending Malik's approval
(generation rules: prompts are a major decision); it is used for the DEC-077 contract test only.

The model sees only the retrieved chunks, each with its ``chunk_id``, and must answer in the output
contract below; :mod:`validator` then checks every citation deterministically.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

PROMPT_VERSION = "v1-draft"  # v1: E-labels + JSON in prompt (eval 2026-11-18)

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

SYSTEM_V0 = """You give legal INFORMATION (not legal advice) about Madhya Pradesh and central
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


PROCEDURE_ONLY = (
    "\n7. This question asks who is right or how a dispute will end. Do not answer that part;"
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
    system = SYSTEM_V0.format(language=LANG_NAME.get(lang, "English"))
    if procedure_only:
        system += PROCEDURE_ONLY
    user = f"Law excerpts:\n\n{excerpts}\n\nQuestion: {question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def ref_map(chunks: Sequence[tuple[str, str]]) -> dict[str, str]:
    """Label -> chunk_id, as used in :func:`build_messages`."""
    return {f"E{i}": cid for i, (cid, _) in enumerate(chunks, 1)}
