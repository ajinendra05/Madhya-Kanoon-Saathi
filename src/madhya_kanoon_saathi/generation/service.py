"""One question → one Reply, wired the same way for the local bot and the cloud answer service.

Loads the approved wording (answer texts, crisis replies, help topics, contact numbers) once and
returns a callable that embeds the question and runs the answer pipeline. The caller supplies
``generate`` (which decides the spend guard: local ledger or the production daily cap) and,
optionally, ``rewrite_call`` for query rewriting (E1, DEC-090).

Retrieval is lazy (A1, DEC-090): the pipeline calls it only when the reply needs law text, so topic
lists and other-state replies skip the reranker. The question vector is computed once and shared
with the crisis router and dispute detector.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from madhya_kanoon_saathi.common.contacts import load as load_contacts
from madhya_kanoon_saathi.generation import rewrite
from madhya_kanoon_saathi.generation.local import LocalRuntime
from madhya_kanoon_saathi.generation.pipeline import Generator, Reply, Retrieved, answer

DATA = Path("data")


def contact_numbers(data: Path = DATA) -> dict[str, str]:
    return {c.id: c.number for c in load_contacts(data / "contacts.yaml")}


def responder(
    rt: LocalRuntime,
    generate: Generator,
    *,
    rewrite_call: rewrite.Call | None = None,
    on_rewrite_error: Callable[[Exception], None] | None = None,
    data: Path = DATA,
    today: Callable[[], date] = date.today,
) -> Callable[[str], Reply]:
    def read(name: str) -> Any:
        return json.loads((data / name).read_text("utf-8"))

    catalog = rewrite.act_catalog(read("corpus_manifest.json"), read("instrument_aliases.json"))
    answer_texts = read("answer_texts.json")
    replies = read("safety/crisis_replies.json")
    topics = read("help_topics.json")
    numbers = contact_numbers(data)

    def respond(question: str) -> Reply:
        vec = rt.vector(question)
        on = today()

        def retrieve(q: str) -> list[Retrieved]:
            rewrites = (
                rewrite.rewrite(q, rewrite_call, on_rewrite_error, catalog) if rewrite_call else []
            )
            return rt.retrieve(q, vec, on, rewrites=rewrites)

        reply = answer(
            question,
            retrieve=retrieve,
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
        return reply

    return respond
