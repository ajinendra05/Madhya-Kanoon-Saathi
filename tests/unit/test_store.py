"""Bot storage rules (DEC-087)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from google.api_core.exceptions import Conflict

from madhya_kanoon_saathi.common.store import (
    QUERY_TTL,
    SEEN_TTL,
    FirestoreStore,
    MemoryStore,
    chat_hash,
    query_doc,
    quota_id,
)

KEY = "k" * 40
NOW = datetime(2026, 11, 21, 10, 0, tzinfo=UTC)


def test_chat_hash_is_stable_keyed_and_not_the_id() -> None:
    h = chat_hash(123456789, KEY)
    assert h == chat_hash(123456789, KEY)
    assert len(h) == 32 and "123456789" not in h
    assert h != chat_hash(123456789, "x" * 40)
    assert h != chat_hash(123456780, KEY)


def test_chat_hash_refuses_a_short_key() -> None:
    with pytest.raises(ValueError):
        chat_hash(1, "short")


def test_duplicate_update_is_detected() -> None:
    s = MemoryStore()
    assert s.mark_seen(42, NOW) is True
    assert s.mark_seen(42, NOW) is False
    assert s.mark_seen(43, NOW) is True
    assert s.data["seen_updates"]["42"]["expire_at"] == NOW + SEEN_TTL


def test_query_text_is_redacted_and_expires_after_90_days() -> None:
    s = MemoryStore()
    rec = {
        "chat": chat_hash(1, KEY),
        "lang": "hinglish",
        "question": "mera number 9876543210 hai, RTI kaise du",
        "reply": "aapne 9876543210 diya",
        "costs": [{"step": "generate", "cost_inr": 0.02}],
    }
    s.log_query("q1", rec, NOW)
    doc = s.data["queries"]["q1"]
    assert "9876543210" not in doc["question"] and "[PHONE]" in doc["question"]
    assert "9876543210" not in doc["reply"]
    assert doc["expire_at"] == NOW + QUERY_TTL
    assert timedelta(days=90) == QUERY_TTL
    assert doc["costs"] == rec["costs"]
    assert "9876543210" in rec["question"]  # caller's record is not mutated


@pytest.mark.parametrize("field", ["chat_id", "username", "first_name", "user_id"])
def test_identifying_fields_are_refused(field: str) -> None:
    with pytest.raises(ValueError):
        query_doc({field: "x"}, NOW)


def test_raw_chat_id_is_refused() -> None:
    with pytest.raises(ValueError):
        query_doc({"chat": "123456789"}, NOW)
    with pytest.raises(ValueError):
        MemoryStore().bump_quota("123456789", NOW)


def test_naive_timestamps_are_refused() -> None:
    with pytest.raises(ValueError):
        MemoryStore().mark_seen(1, datetime(2026, 11, 21, 10, 0))


def test_quota_counts_per_chat_per_indian_day() -> None:
    s, a, b = MemoryStore(), chat_hash(1, KEY), chat_hash(2, KEY)
    assert [s.bump_quota(a, NOW) for _ in range(3)] == [1, 2, 3]
    assert s.bump_quota(b, NOW) == 1
    # 18:30 UTC is midnight in India: a new day starts
    late = datetime(2026, 11, 21, 18, 29, tzinfo=UTC)
    nxt = datetime(2026, 11, 21, 18, 30, tzinfo=UTC)
    assert quota_id(a, late).endswith("_20261121")
    assert quota_id(a, nxt).endswith("_20261122")
    assert s.bump_quota(a, nxt) == 1


# --- FirestoreStore duplicate check against a fake client (no network) ---


class _Snap:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self.exists = data is not None
        self._d = data or {}

    def get(self, k: str) -> Any:
        return self._d[k]


class _Ref:
    def __init__(self, db: dict[str, dict[str, Any]], key: str, lose_first_reply: bool) -> None:
        self.db, self.key, self.lose = db, key, lose_first_reply

    def create(self, data: dict[str, Any]) -> None:
        if self.key in self.db:
            raise Conflict("exists")
        self.db[self.key] = data
        if self.lose:  # write landed, reply lost, client retried and hit its own document
            raise Conflict("exists")

    def get(self) -> _Snap:
        return _Snap(self.db.get(self.key))


class _Client:
    def __init__(self, lose_first_reply: bool = False) -> None:
        self.db: dict[str, dict[str, Any]] = {}
        self.lose = lose_first_reply

    def collection(self, name: str) -> _Client:
        return self

    def document(self, key: str) -> _Ref:
        return _Ref(self.db, key, self.lose)


def test_firestore_duplicate_update_is_detected() -> None:
    s = FirestoreStore(_Client())
    assert s.mark_seen(7, NOW) is True
    assert s.mark_seen(7, NOW) is False


def test_firestore_own_retried_write_is_not_a_duplicate() -> None:
    assert FirestoreStore(_Client(lose_first_reply=True)).mark_seen(7, NOW) is True
