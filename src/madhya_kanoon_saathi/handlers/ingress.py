"""Ingress service (DEC-010, DEC-086): Telegram webhook → secret check → dedup → Pub/Sub → 200.

Telegram sends ``X-Telegram-Bot-Api-Secret-Token`` with the secret given to ``setWebhook`` and
repeats any request that gets a non-2xx reply (core.telegram.org/bots/api#setwebhook, read
2026-11-21). Duplicates are dropped by ``Store.mark_seen``; if queueing then fails the mark is
removed and 500 is returned, so Telegram's retry is processed instead of being lost.

Published payload: ``{"update_id", "chat_id", "text", "date"}`` only. Publishing uses the
Pub/Sub REST API (``POST https://pubsub.googleapis.com/v1/{topic}:publish``) with a token from the
Cloud Run metadata server, so no client library is needed.

Environment: ``TELEGRAM_WEBHOOK_SECRET`` (Secret Manager), ``MKS_PROJECT``, ``MKS_TOPIC``.
"""

from __future__ import annotations

import base64
import hmac
import json
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from madhya_kanoon_saathi.common.env import secret
from madhya_kanoon_saathi.common.store import FirestoreStore, Store

HEADER = "x-telegram-bot-api-secret-token"
METADATA_TOKEN = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)


def log(event: str, **fields: Any) -> None:
    """One JSON line per event on stdout (Cloud Logging); never message text or chat ids."""
    print(json.dumps({"service": "ingress", "event": event, **fields}), flush=True)


@dataclass
class Ingress:
    webhook_secret: str
    store: Store
    publish: Callable[[bytes], None]
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    def __call__(self, headers: Mapping[str, str], body: bytes) -> tuple[int, bytes]:
        if not hmac.compare_digest(headers.get(HEADER, ""), self.webhook_secret):
            log("bad_secret")
            return 401, b""
        try:
            update = json.loads(body)
            update_id = int(update["update_id"])
        except (ValueError, KeyError, TypeError):
            log("bad_update")
            return 400, b""
        msg = update.get("message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        text = msg.get("text")
        if chat_id is None or not isinstance(text, str) or not text.strip():
            log("skipped", update_id=update_id)  # stickers, edits, joins: nothing to answer
            return 200, b""
        if not self.store.mark_seen(update_id, self.clock()):
            log("duplicate", update_id=update_id)
            return 200, b""
        payload = {
            "update_id": update_id,
            "chat_id": chat_id,
            "text": text,
            "date": msg.get("date"),
        }
        try:
            self.publish(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.store.forget_seen(update_id)
            log("publish_failed", update_id=update_id, error=type(e).__name__)
            return 500, b""
        log("queued", update_id=update_id)
        return 200, b""


class MetadataToken:
    """Access token of the service's own account, cached until a minute before expiry."""

    def __init__(self) -> None:
        self._token, self._until = "", 0.0

    def __call__(self) -> str:
        if time.time() < self._until:
            return self._token
        req = urllib.request.Request(METADATA_TOKEN, headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        self._token = str(data["access_token"])
        self._until = time.time() + int(data.get("expires_in", 300)) - 60
        return self._token


@dataclass
class PubSubPublisher:
    topic: str  # projects/{project}/topics/{topic}
    token: Callable[[], str] = field(default_factory=MetadataToken)

    def __call__(self, data: bytes) -> None:
        body = json.dumps({"messages": [{"data": base64.b64encode(data).decode("ascii")}]})
        req = urllib.request.Request(
            f"https://pubsub.googleapis.com/v1/{self.topic}:publish",
            data=body.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token()}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise RuntimeError(f"publish returned HTTP {resp.status}")


def main() -> None:
    from madhya_kanoon_saathi.handlers.http import serve

    project = secret("MKS_PROJECT")
    topic = f"projects/{project}/topics/{secret('MKS_TOPIC')}"
    app = Ingress(
        secret("TELEGRAM_WEBHOOK_SECRET"), FirestoreStore.connect(project), PubSubPublisher(topic)
    )
    log("ready")
    serve(app)


if __name__ == "__main__":
    main()
