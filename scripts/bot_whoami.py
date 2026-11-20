"""Show the chat ids that recently messaged the bot, to fill MKS_BOT_ALLOWED_CHATS (W2.5).

Usage:
    1. In Telegram, send any message (e.g. "hi") to the bot.
    2. uv run python scripts/bot_whoami.py

Reads pending updates once WITHOUT confirming them (no offset) and without answering; prints only
chat id, chat type and first name, never message text. Free: no LLM call. The token is read from
.env and never printed. Does not work while the bot (scripts/run_bot.py) is polling.
"""

from __future__ import annotations

import sys

from madhya_kanoon_saathi.bot.telegram import TelegramClient
from madhya_kanoon_saathi.common.env import secret


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    client = TelegramClient(secret("TELEGRAM_BOT_TOKEN"), timeout=15)
    updates = client.call("getUpdates", {"timeout": 0, "allowed_updates": ["message"]})
    seen: dict[int, tuple[str, str]] = {}
    for u in updates:
        chat = (u.get("message") or {}).get("chat") or {}
        if "id" in chat:
            seen[chat["id"]] = (chat.get("type", "?"), chat.get("first_name", ""))
    if not seen:
        print("No messages waiting. Send 'hi' to the bot in Telegram, then run this again.")
        return 1
    for cid, (kind, name) in seen.items():
        print(f"chat id {cid}  ({kind}, {name})")
    print("\nAdd yours to .env as: MKS_BOT_ALLOWED_CHATS=<chat id>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
