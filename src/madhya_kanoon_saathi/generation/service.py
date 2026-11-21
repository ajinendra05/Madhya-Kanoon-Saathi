"""One question → one Reply, wired the same way for the local bot and the cloud answer service.

Loads the approved wording (answer texts, crisis replies, help topics, contact numbers) once and
returns a callable that embeds, retrieves and runs the answer pipeline for a question. The caller
supplies ``generate`` (which decides the spend guard: local ledger or the production daily cap).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from madhya_kanoon_saathi.common.contacts import load as load_contacts
from madhya_kanoon_saathi.generation.local import LocalRuntime
from madhya_kanoon_saathi.generation.pipeline import Generator, Reply, answer

DATA = Path("data")


def contact_numbers(data: Path = DATA) -> dict[str, str]:
    return {c.id: c.number for c in load_contacts(data / "contacts.yaml")}


def responder(
    rt: LocalRuntime,
    generate: Generator,
    *,
    data: Path = DATA,
    today: Callable[[], date] = date.today,
) -> Callable[[str], Reply]:
    def read(name: str) -> Any:
        return json.loads((data / name).read_text("utf-8"))

    answer_texts = read("answer_texts.json")
    replies = read("safety/crisis_replies.json")
    topics = read("help_topics.json")
    numbers = contact_numbers(data)

    def respond(question: str) -> Reply:
        vec = rt.vector(question)
        on = today()
        chunks = rt.retrieve(question, vec, on)
        return answer(
            question,
            retrieve=lambda _q: chunks,
            generate=generate,
            texts=answer_texts,
            crisis_replies=replies,
            numbers=numbers,
            today=on,
            query_vec=vec,
            crisis_examples=rt.crisis_index,
            dispute_examples=rt.dispute_index,
            versions=rt.versions,
            topics=topics,
        )

    return respond
