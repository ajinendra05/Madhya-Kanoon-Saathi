"""Answer service (DEC-010, DEC-086): Pub/Sub push → quota → pipeline → Telegram → Firestore log.

Pub/Sub push body: ``{"message": {"data": <base64>, "messageId", ...}, "subscription"}``; replies
102/200/201/202/204 acknowledge, anything else is retried (docs.cloud.google.com/pubsub/docs/push,
read 2026-11-21). Once a message has been read this service always acknowledges (204): a retry
after a paid model call would bill twice. Cloud Run itself checks that the caller is the
``mks-pubsub-push`` account (run.invoker), so the handler does not re-verify the token.

Order per message: ``/start``/``/help`` → greeting; quota (DEC-088, 20 per chat per Indian day) →
limit reply; pipeline inside the daily spend cap (₹20, DEC-088) → reply; redacted query record
(DEC-087). Chat ids are hashed before anything is stored; logs carry no text or chat id.

Environment: ``TELEGRAM_BOT_TOKEN``, ``SARVAM_API_KEY``, ``MKS_CHAT_HASH_KEY`` (Secret Manager),
``MKS_PROJECT``.
"""

from __future__ import annotations

import base64
import json
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from madhya_kanoon_saathi.common.store import Store, chat_hash
from madhya_kanoon_saathi.generation.budget import BudgetExceededError
from madhya_kanoon_saathi.generation.pipeline import Reply, detect_lang

DAILY_QUESTIONS = 20  # DEC-088
Respond = Callable[[str], tuple[Reply, list[dict[str, Any]]]]  # reply + per-call costs


def log(event: str, **fields: Any) -> None:
    """One JSON line per event on stdout (Cloud Logging); never message text or chat ids."""
    print(json.dumps({"service": "answer", "event": event, **fields}), flush=True)


def decode_push(body: bytes) -> dict[str, Any]:
    envelope = json.loads(body)
    data = base64.b64decode(envelope["message"]["data"])
    msg: dict[str, Any] = json.loads(data)
    if not isinstance(msg.get("chat_id"), int) or not isinstance(msg.get("text"), str):
        raise ValueError("push message lacks chat_id/text")
    return msg


def fill(template: str, numbers: Mapping[str, str]) -> str:
    """Put contact numbers from contacts.yaml into wording; a missing id raises, never blank."""
    return re.sub(r"\{([a-z0-9_]+)\}", lambda m: numbers[m.group(1)], template)


@dataclass
class AnswerService:
    store: Store
    send: Callable[[int, str], None]
    respond: Respond
    texts: Mapping[str, Any]  # approved bot_texts.json, numbers already filled
    hash_key: str
    limit: int = DAILY_QUESTIONS
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    def __call__(self, headers: Mapping[str, str], body: bytes) -> tuple[int, bytes]:
        try:
            msg = decode_push(body)
        except (ValueError, KeyError, TypeError):
            log("bad_push")
            return 204, b""  # retrying a malformed message cannot help
        try:
            log("done", update_id=msg.get("update_id"), outcome=self.handle(msg))
        except Exception as e:  # already logged inside where possible; never retry
            log("failed", update_id=msg.get("update_id"), error=type(e).__name__)
        return 204, b""

    def handle(self, msg: Mapping[str, Any]) -> str:
        chat, text = int(msg["chat_id"]), str(msg["text"]).strip()
        if text.startswith(("/start", "/help")):
            self.send(chat, self.texts["start"])
            return "start"
        now = self.clock()
        who = chat_hash(chat, self.hash_key)
        lang = detect_lang(text)
        if self.store.bump_quota(who, now) > self.limit:
            self.send(chat, self.texts["limit"][lang])
            return "limit"
        t0 = time.perf_counter()
        costs: list[dict[str, Any]] = []
        try:
            reply, costs = self.respond(text)
            outcome, out_text = "answered", reply.text
            record: dict[str, Any] = dict(reply.log)
        except BudgetExceededError:
            outcome, out_text, record = (
                "budget_cap",
                self.texts["error"],
                {"abstain_reason": "budget_cap"},
            )
        except Exception as e:
            outcome, out_text = "error", self.texts["error"]
            record = {"abstain_reason": "error", "error": type(e).__name__}
        total_ms = round((time.perf_counter() - t0) * 1000)
        try:
            self.send(chat, out_text)
        except Exception as e:
            record["send_error"] = type(e).__name__
            outcome += "_unsent"
        record.update(
            chat=who,
            lang=lang,
            question=text,
            reply=out_text,
            outcome=outcome,
            costs=costs,
            timings_ms={"total": total_ms},
        )
        self.store.log_query(f"u{msg.get('update_id')}", record, now)
        return outcome


def main() -> None:
    from madhya_kanoon_saathi.bot.telegram import TelegramClient
    from madhya_kanoon_saathi.common.env import secret
    from madhya_kanoon_saathi.common.store import FirestoreStore
    from madhya_kanoon_saathi.generation.budget import DailySpendGuard, cost_inr
    from madhya_kanoon_saathi.generation.llm import complete, request_body
    from madhya_kanoon_saathi.generation.local import LocalRuntime
    from madhya_kanoon_saathi.generation.service import DATA, contact_numbers, responder
    from madhya_kanoon_saathi.handlers.http import serve

    store = FirestoreStore.connect(secret("MKS_PROJECT"))
    guard = DailySpendGuard(store)
    bot_texts = json.loads((DATA / "bot_texts.json").read_text("utf-8"))
    if bot_texts.get("status") != "approved":
        raise PermissionError("data/bot_texts.json is not approved")
    numbers = contact_numbers()
    texts = {
        "start": fill(bot_texts["start"], numbers),
        "error": fill(bot_texts["error"], numbers),
        "limit": {k: fill(v, numbers) for k, v in bot_texts["limit"].items()},
    }
    log("loading")
    rt = LocalRuntime.load()  # models + indexes, before the port opens (startup probe)
    costs: list[dict[str, Any]] = []

    def generate(messages: list[dict[str, str]]) -> str:
        body = request_body(messages, "json_object", reasoning_effort="low", max_tokens=1200)
        t0 = time.perf_counter()
        comp = complete(body, purpose="telegram_cloud", guard=guard)
        costs.append(
            {
                "step": "generate",
                "provider": "sarvam",
                "model": comp.model,
                "units": comp.prompt_tokens + comp.completion_tokens,
                "unit_type": "tokens",
                "cost_inr": round(cost_inr(comp.prompt_tokens, comp.completion_tokens), 6),
                "latency_ms": round((time.perf_counter() - t0) * 1000),
            }
        )
        return comp.content

    answer_one = responder(rt, generate)

    def respond(question: str) -> tuple[Reply, list[dict[str, Any]]]:
        costs.clear()  # one request at a time per instance (Cloud Run concurrency 1)
        reply = answer_one(question)
        return reply, list(costs)

    client = TelegramClient(secret("TELEGRAM_BOT_TOKEN"), timeout=30)
    app = AnswerService(store, client.send_message, respond, texts, secret("MKS_CHAT_HASH_KEY"))
    log("ready")
    serve(app)


if __name__ == "__main__":
    main()
