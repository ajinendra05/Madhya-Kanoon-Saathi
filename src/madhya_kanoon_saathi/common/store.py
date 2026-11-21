"""What the cloud bot remembers, per DEC-087 (Firestore, asia-south1).

Three collections:

- ``seen_updates/{update_id}``: one document per Telegram update; a second arrival is a duplicate
  (DEC-010). Kept 2 days.
- ``queries/{query_id}``: one redacted record per question, costs embedded. Kept 90 days (DEC-029).
- ``quotas/{chat_hash}_{YYYYMMDD}``: questions per chat per Indian calendar day. Kept 2 days.

Chat ids are never stored: callers pass ``chat_hash(chat_id, key)`` (HMAC-SHA256, secret key).
Question and reply text pass ``redact()`` here, so no caller can forget it. Deletion is done by
Firestore TTL policies on ``expire_at``.

``MemoryStore`` is the in-process version used by tests and local runs; ``FirestoreStore`` wraps
the official client (google-cloud-firestore, DEC-087 option A). Both satisfy ``Store``.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from madhya_kanoon_saathi.common.redact import redact

SEEN, QUERIES, QUOTAS = "seen_updates", "queries", "quotas"
SEEN_TTL = timedelta(days=2)
QUERY_TTL = timedelta(days=90)
QUOTA_TTL = timedelta(days=2)
IST = timezone(timedelta(hours=5, minutes=30))  # India has no daylight saving
MIN_KEY_CHARS = 32

# identifying fields that must never reach a stored record
_FORBIDDEN = frozenset({"chat_id", "user_id", "username", "first_name", "last_name", "phone"})
_REDACTED = ("question", "reply")


def chat_hash(chat_id: int, key: str) -> str:
    """Keyed one-way code for a chat (32 hex chars): groups a chat's rows without identifying it."""
    if len(key) < MIN_KEY_CHARS:
        raise ValueError(f"chat hash key must be at least {MIN_KEY_CHARS} characters")
    mac = hmac.new(key.encode("utf-8"), str(chat_id).encode("ascii"), hashlib.sha256)
    return mac.hexdigest()[:32]


def quota_id(chat: str, now: datetime) -> str:
    return f"{chat}_{now.astimezone(IST):%Y%m%d}"


def query_doc(record: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    """The stored form of a query record: identifying keys refused, free text redacted."""
    bad = _FORBIDDEN & set(record)
    if bad:
        raise ValueError(f"identifying fields not allowed in a query record: {sorted(bad)}")
    if "chat" in record and not _is_hash(record["chat"]):
        raise ValueError("'chat' must be chat_hash(...), not a raw id")
    doc = dict(record)
    for k in _REDACTED:
        if isinstance(doc.get(k), str):
            doc[k] = redact(doc[k]).text
    doc["at"] = now
    doc["expire_at"] = now + QUERY_TTL
    return doc


def _is_hash(v: object) -> bool:
    return isinstance(v, str) and len(v) == 32 and all(c in "0123456789abcdef" for c in v)


def _check_now(now: datetime) -> None:
    if now.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")


class Store(Protocol):
    def mark_seen(self, update_id: int, now: datetime) -> bool:
        """True the first time an update id arrives, False for a duplicate."""
        ...

    def log_query(self, query_id: str, record: Mapping[str, Any], now: datetime) -> None: ...

    def bump_quota(self, chat: str, now: datetime) -> int:
        """Add one question for this chat today and return today's count."""
        ...


class MemoryStore:
    """Dict-backed store with the same rules (tests, local bot)."""

    def __init__(self) -> None:
        self.data: dict[str, dict[str, dict[str, Any]]] = {SEEN: {}, QUERIES: {}, QUOTAS: {}}

    def mark_seen(self, update_id: int, now: datetime) -> bool:
        _check_now(now)
        key = str(update_id)
        if key in self.data[SEEN]:
            return False
        self.data[SEEN][key] = {"received_at": now, "expire_at": now + SEEN_TTL}
        return True

    def log_query(self, query_id: str, record: Mapping[str, Any], now: datetime) -> None:
        _check_now(now)
        self.data[QUERIES][query_id] = query_doc(record, now)

    def bump_quota(self, chat: str, now: datetime) -> int:
        _check_now(now)
        if not _is_hash(chat):
            raise ValueError("quota key must be chat_hash(...), not a raw id")
        doc = self.data[QUOTAS].setdefault(quota_id(chat, now), {"count": 0})
        doc["count"] += 1
        doc["expire_at"] = now + QUOTA_TTL
        return int(doc["count"])


class FirestoreStore:
    """The same operations on Firestore. ``client`` is a ``google.cloud.firestore.Client``."""

    def __init__(self, client: Any) -> None:
        self.client = client

    @classmethod
    def connect(cls, project: str) -> FirestoreStore:
        from google.cloud import firestore  # imported here so tests and local runs don't need it

        return cls(firestore.Client(project=project))

    def mark_seen(self, update_id: int, now: datetime) -> bool:
        from google.api_core.exceptions import Conflict

        _check_now(now)
        ref = self.client.collection(SEEN).document(str(update_id))
        token = uuid.uuid4().hex
        try:
            ref.create({"received_at": now, "expire_at": now + SEEN_TTL, "token": token})
            return True
        except Conflict:
            # A retried create whose first attempt landed also conflicts: it is our own write
            snap = ref.get()
            return bool(snap.exists and snap.get("token") == token)

    def log_query(self, query_id: str, record: Mapping[str, Any], now: datetime) -> None:
        _check_now(now)
        self.client.collection(QUERIES).document(query_id).set(query_doc(record, now))

    def bump_quota(self, chat: str, now: datetime) -> int:
        from google.cloud import firestore

        _check_now(now)
        if not _is_hash(chat):
            raise ValueError("quota key must be chat_hash(...), not a raw id")
        ref = self.client.collection(QUOTAS).document(quota_id(chat, now))

        @firestore.transactional
        def bump(tx: Any) -> int:
            snap = ref.get(transaction=tx)
            n = int(snap.get("count")) + 1 if snap.exists else 1
            tx.set(ref, {"count": n, "expire_at": now + QUOTA_TTL})
            return n

        return int(bump(self.client.transaction()))
