"""Local Telegram bot by long polling (W2.5; DEC-007). Standard library only.

Bot API (https://core.telegram.org/bots/api): ``POST https://api.telegram.org/bot<token>/<method>``
with a JSON body; ``getUpdates`` (``offset`` = last update_id + 1 confirms earlier updates,
``timeout`` = long-poll seconds; fails with 409 while a webhook is set); ``sendMessage``
(``chat_id``, ``text`` of at most 4096 characters). Production uses a webhook via the Function
URL and SQS instead (DEC-010, W3.1); this loop is for local testing only.

The token is part of every request URL, so errors are re-raised without the URL and the token is
never printed or logged. Each message is answered by a handler (the answer pipeline); the bot
never logs the question itself, only what the handler returns as a redacted log record.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

API = "https://api.telegram.org/bot{token}/{method}"
MAX_TEXT = 4096
POLL_SECONDS = 50


class TelegramError(RuntimeError):
    """A Bot API call failed (message never contains the token or URL)."""


def split_text(text: str, limit: int = MAX_TEXT) -> list[str]:
    """Split a long reply into Telegram-sized parts, at paragraph or line breaks when possible."""
    parts: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = max(rest.rfind("\n\n", 0, limit), rest.rfind("\n", 0, limit))
        if cut <= 0:
            cut = limit
        parts.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip("\n")
    if rest.strip():
        parts.append(rest)
    return parts


@dataclass
class TelegramClient:
    token: str
    timeout: float = POLL_SECONDS + 10

    def call(self, method: str, params: dict[str, Any]) -> Any:
        req = urllib.request.Request(
            API.format(token=self.token, method=method),
            data=json.dumps(params, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                desc = json.loads(e.read().decode("utf-8")).get("description", "")
            except ValueError:
                desc = ""
            raise TelegramError(f"{method}: HTTP {e.code} {desc}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            reason = getattr(e, "reason", type(e).__name__)
            raise TelegramError(f"{method}: network error ({reason})") from None
        if not body.get("ok"):
            raise TelegramError(f"{method}: {body.get('description', 'not ok')}")
        return body["result"]

    def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"timeout": POLL_SECONDS, "allowed_updates": ["message"]}
        if offset is not None:
            params["offset"] = offset
        result: list[dict[str, Any]] = self.call("getUpdates", params)
        return result

    def send_message(self, chat_id: int, text: str) -> None:
        for part in split_text(text):
            self.call("sendMessage", {"chat_id": chat_id, "text": part})


Handler = Callable[[str], str]


def handle_update(
    update: dict[str, Any],
    client: Any,
    handler: Handler,
    texts: dict[str, Any],
    allowed: frozenset[int] | None,
) -> str:
    """Answer one update; returns what happened (for the local console, no message text)."""
    msg = update.get("message") or {}
    chat = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()
    if chat is None or not text:
        return "skipped (no text)"
    if allowed is not None and chat not in allowed:
        client.send_message(chat, texts["not_allowed"])
        return "refused (chat not in allow-list)"
    if text.startswith("/start") or text.startswith("/help"):
        client.send_message(chat, texts["start"])
        return "start"
    try:
        reply = handler(text)
    except Exception as e:
        client.send_message(chat, texts["error"])
        return f"error ({type(e).__name__})"
    client.send_message(chat, reply)
    return "answered"


def run(
    client: Any,
    handler: Handler,
    texts: dict[str, Any],
    *,
    allowed: frozenset[int] | None = None,
    max_loops: int | None = None,
    log: Callable[[str], None] = print,
) -> None:
    """Long-poll and answer until interrupted (or ``max_loops`` polls, for tests)."""
    offset: int | None = None
    loops = 0
    while max_loops is None or loops < max_loops:
        loops += 1
        try:
            updates = client.get_updates(offset)
        except TelegramError as e:
            log(f"poll failed: {e}; retrying in 5 s")
            time.sleep(5)
            continue
        for u in updates:
            offset = int(u["update_id"]) + 1  # confirm it even if answering fails
            log(f"update {u['update_id']}: {handle_update(u, client, handler, texts, allowed)}")
