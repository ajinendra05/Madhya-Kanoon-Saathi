"""Generator prompt and answer schema (W2.1). PROMPT_VERSION v0 is a DRAFT pending Malik's approval
(generation rules: prompts are a major decision); it is used for the DEC-077 contract test only.

The model sees only the retrieved chunks, each with its ``chunk_id``, and must answer in the output
contract below; :mod:`validator` then checks every citation deterministically.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

PROMPT_VERSION = "v0-draft"

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
Indian law. Use ONLY the law excerpts provided. Each excerpt starts with its chunk_id in
square brackets.
Rules:
1. Every statement must be supported by an excerpt. Put it in an answer block and cite the chunk_id
   with a quote copied EXACTLY, word for word, from that excerpt (at least 3 words, no changes).
2. If the excerpts do not answer the question, set abstain to true, give a short abstain_reason,
   and return no answer blocks. Never use outside knowledge, never guess amounts, dates or sections.
3. Do not say who is right in a dispute and do not predict outcomes; explain the procedure only.
4. Never ask for caste, religion, disability or health information. Never recommend private lawyers.
5. Write the answer text in {language}. Quotes stay in the excerpt's own language.
6. Keep it short: at most 4 answer blocks, plain words."""


def build_messages(
    question: str, chunks: Sequence[tuple[str, str]], lang: str
) -> list[dict[str, str]]:
    """Messages for one question; ``chunks`` = (chunk_id, canonical text) as retrieved."""
    excerpts = "\n\n".join(f"[{cid}]\n{text}" for cid, text in chunks)
    system = SYSTEM_V0.format(language=LANG_NAME.get(lang, "English"))
    user = f"Law excerpts:\n\n{excerpts}\n\nQuestion: {question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
