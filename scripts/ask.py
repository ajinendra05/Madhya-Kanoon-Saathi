"""Ask the bot one question locally (W2.1; Telegram comes in W2.5).

Usage:
    uv run python scripts/ask.py "RTI ki fees kitni hai?" --dry-run   # no LLM call, free
    uv run python scripts/ask.py "RTI ki fees kitni hai?" --allow-draft  # one paid Sarvam call

--dry-run shows the routing (crisis tier, jurisdiction, dispute) and the 6 retrieved chunks without
calling the LLM. Without --dry-run, Sarvam-105B answers (key from .env; ~1-3 paise per question)
and the validated, rendered reply is printed. --allow-draft uses the draft wording files until
Malik approves them (S27, S29).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from madhya_kanoon_saathi.common.contacts import load as load_contacts
from madhya_kanoon_saathi.generation import crisis, dispute, jurisdiction
from madhya_kanoon_saathi.generation.llm import complete, request_body
from madhya_kanoon_saathi.generation.local import LocalRuntime
from madhya_kanoon_saathi.generation.pipeline import answer
from madhya_kanoon_saathi.generation.prompt import ANSWER_SCHEMA


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-draft", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

    rt = LocalRuntime.load()
    today = date.today()
    vec = rt.vector(a.question)
    chunks = rt.retrieve(a.question, vec, today)
    if a.dry_run:
        cr = crisis.route(a.question, vec, rt.crisis_index)
        dp = dispute.route(a.question, vec, rt.dispute_index)
        print("crisis:", cr.tier, cr.categories)
        print("jurisdiction:", jurisdiction.check(a.question))
        print("dispute:", dp.is_dispute, dp.domains, f"margin {dp.margin:.3f}")
        for r in chunks:
            print(f"- {r.chunk_id} [{r.status}] {r.extraction or 'pdfium'}: {r.text[:120]}")
        return 0

    def generate(messages: list[dict[str, str]]) -> str:
        comp = complete(
            request_body(messages, ANSWER_SCHEMA, reasoning_effort="low"), purpose="ask_cli"
        )
        print(f"(LLM: {comp.prompt_tokens}+{comp.completion_tokens} tokens, "
              f"~₹{comp.cost_inr:.4f} excl. GST)", file=sys.stderr)  # fmt: skip
        return comp.content

    reply = answer(
        a.question,
        retrieve=lambda q: chunks,
        generate=generate,
        texts=json.loads(Path("data/answer_texts.json").read_text("utf-8")),
        crisis_replies=json.loads(Path("data/safety/crisis_replies.json").read_text("utf-8")),
        numbers={c.id: c.number for c in load_contacts(Path("data/contacts.yaml"))},
        today=today,
        query_vec=vec,
        crisis_examples=rt.crisis_index,
        dispute_examples=rt.dispute_index,
        allow_draft=a.allow_draft,
    )
    print(reply.text)
    print("\nlog:", json.dumps(reply.log, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
