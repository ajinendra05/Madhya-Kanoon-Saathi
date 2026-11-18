"""Run the Telegram bot locally by long polling (W2.5). Stop with Ctrl+C.

Usage:
    uv run python scripts/run_bot.py [--allow-draft]

- Token: TELEGRAM_BOT_TOKEN from the environment or .env (never printed).
- Allow-list: MKS_BOT_ALLOWED_CHATS="123,456" in .env limits who can use it (strongly advised:
  every answered question is a paid Sarvam call inside the Rs10 cap, DEC-078). Without it, any
  chat that finds the bot can ask, and a warning is shown.
- Answer wording and crisis replies must be approved (DEC-079); the bot's own greeting/error texts
  (data/bot_texts.json) too, unless --allow-draft is given for local testing.
- Each answer's redacted log record (no raw question, DEC-029/076) is appended to
  data/logs/bot_local.jsonl (git-ignored).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from madhya_kanoon_saathi.bot.telegram import TelegramClient, run
from madhya_kanoon_saathi.common.contacts import load as load_contacts
from madhya_kanoon_saathi.common.env import secret
from madhya_kanoon_saathi.generation.llm import complete, request_body
from madhya_kanoon_saathi.generation.local import LocalRuntime
from madhya_kanoon_saathi.generation.pipeline import answer

LOG = Path("data/logs/bot_local.jsonl")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-draft", action="store_true", help="use draft bot_texts.json")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

    bot_texts = json.loads(Path("data/bot_texts.json").read_text("utf-8"))
    if bot_texts.get("status") != "approved" and not a.allow_draft:
        print("data/bot_texts.json is not approved; use --allow-draft for local testing")
        return 1
    numbers = {c.id: c.number for c in load_contacts(Path("data/contacts.yaml"))}
    fill = lambda t: re.sub(r"\{([a-z0-9_]+)\}", lambda m: numbers[m.group(1)], t)  # noqa: E731
    texts = {k: fill(bot_texts[k]) for k in ("start", "error", "not_allowed")}
    answer_texts = json.loads(Path("data/answer_texts.json").read_text("utf-8"))
    replies = json.loads(Path("data/safety/crisis_replies.json").read_text("utf-8"))

    try:
        allowed_raw = secret("MKS_BOT_ALLOWED_CHATS")
        allowed: frozenset[int] | None = frozenset(
            int(x) for x in allowed_raw.split(",") if x.strip()
        )
    except RuntimeError:
        allowed = None
        print("WARNING: MKS_BOT_ALLOWED_CHATS not set; anyone who finds the bot can spend budget")

    print("loading models and indexes ...")
    rt = LocalRuntime.load()

    def generate(messages: list[dict[str, str]]) -> str:
        body = request_body(messages, "json_object", reasoning_effort="low", max_tokens=1200)
        return complete(body, purpose="telegram_local").content

    def handler(question: str) -> str:
        vec = rt.vector(question)
        chunks = rt.retrieve(question, vec, date.today())
        reply = answer(
            question,
            retrieve=lambda _q: chunks,
            generate=generate,
            texts=answer_texts,
            crisis_replies=replies,
            numbers=numbers,
            today=date.today(),
            query_vec=vec,
            crisis_examples=rt.crisis_index,
            dispute_examples=rt.dispute_index,
            versions=rt.versions,
        )
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(reply.log, ensure_ascii=False) + "\n")  # redacted record only
        return reply.text

    client = TelegramClient(secret("TELEGRAM_BOT_TOKEN"))
    me = client.call("getMe", {})
    print(f"bot @{me.get('username')} is polling; Ctrl+C to stop")
    try:
        run(client, handler, texts, allowed=allowed)
    except KeyboardInterrupt:
        print("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
