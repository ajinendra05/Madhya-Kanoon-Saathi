"""Cloud handlers (DEC-010, DEC-086, DEC-088) with fakes: no network, no paid calls."""

from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from madhya_kanoon_saathi.common.store import MemoryStore, chat_hash
from madhya_kanoon_saathi.generation.budget import BudgetExceededError, DailySpendGuard
from madhya_kanoon_saathi.generation.pipeline import Reply, detect_lang
from madhya_kanoon_saathi.handlers.answer import AnswerService, decode_push, fill
from madhya_kanoon_saathi.handlers.http import make_server
from madhya_kanoon_saathi.handlers.ingress import HEADER, Ingress

NOW = datetime(2026, 11, 21, 10, 0, tzinfo=UTC)
SECRET = "s3cret_token-1"
KEY = "k" * 64


def update(uid: int = 1, text: str | None = "RTI kaise du", chat: int = 555) -> bytes:
    msg: dict[str, Any] = {"chat": {"id": chat}, "date": 1}
    if text is not None:
        msg["text"] = text
    return json.dumps({"update_id": uid, "message": msg}).encode()


# --- ingress ---


def make_ingress(fail: bool = False) -> tuple[Ingress, MemoryStore, list[bytes]]:
    store, sent = MemoryStore(), []

    def publish(data: bytes) -> None:
        if fail:
            raise OSError("pubsub down")
        sent.append(data)

    return Ingress(SECRET, store, publish, clock=lambda: NOW), store, sent


def test_ingress_rejects_wrong_or_missing_secret() -> None:
    app, _, sent = make_ingress()
    assert app({HEADER: "wrong"}, update())[0] == 401
    assert app({}, update())[0] == 401
    assert sent == []


def test_ingress_queues_once_and_drops_duplicates() -> None:
    app, _, sent = make_ingress()
    assert app({HEADER: SECRET}, update(7))[0] == 200
    assert app({HEADER: SECRET}, update(7))[0] == 200
    assert len(sent) == 1
    assert json.loads(sent[0]) == {
        "update_id": 7,
        "chat_id": 555,
        "text": "RTI kaise du",
        "date": 1,
    }


def test_ingress_skips_updates_without_text() -> None:
    app, store, sent = make_ingress()
    assert app({HEADER: SECRET}, update(text=None))[0] == 200
    assert sent == [] and store.data["seen_updates"] == {}


def test_ingress_bad_json_is_400() -> None:
    app, _, _ = make_ingress()
    assert app({HEADER: SECRET}, b"not json")[0] == 400


def test_ingress_publish_failure_is_retried_not_lost() -> None:
    app, store, _ = make_ingress(fail=True)
    assert app({HEADER: SECRET}, update(9))[0] == 500
    assert "9" not in store.data["seen_updates"]  # Telegram's retry will be processed
    ok, _, sent = make_ingress()
    ok.store = store  # same store, publishing works again
    ok.publish = sent.append
    assert ok({HEADER: SECRET}, update(9))[0] == 200 and len(sent) == 1


# --- answer ---


def push(chat: int = 555, text: str = "RTI kaise du", uid: int = 1) -> bytes:
    data = json.dumps({"update_id": uid, "chat_id": chat, "text": text, "date": 1}).encode()
    return json.dumps({"message": {"data": base64.b64encode(data).decode()}}).encode()


TEXTS = {
    "start": "hello",
    "error": "sorry",
    "limit": {"hi": "सीमा", "hinglish": "seema poori", "en": "limit reached"},
}


def make_answer(
    respond: Any = None, limit: int = 20, send_fails: bool = False
) -> tuple[AnswerService, MemoryStore, list[tuple[int, str]]]:
    store, out = MemoryStore(), []

    def send(chat: int, text: str) -> None:
        if send_fails:
            raise OSError("telegram down")
        out.append((chat, text))

    def default(q: str) -> tuple[Reply, list[dict[str, Any]]]:
        log = {"abstain_reason": None, "cited": ["IN.RTI2005:s6@en@2005-10-12"]}
        return Reply(f"answer to {q}", False, None, log), [{"step": "generate", "cost_inr": 0.02}]

    svc = AnswerService(store, send, respond or default, TEXTS, KEY, limit=limit, clock=lambda: NOW)
    return svc, store, out


def test_answer_replies_and_logs_a_redacted_hashed_record() -> None:
    svc, store, out = make_answer()
    status, _ = svc({}, push(text="mera number 9876543210 hai, RTI kaise du", uid=3))
    assert status == 204
    assert out == [(555, "answer to mera number 9876543210 hai, RTI kaise du")]
    rec = store.data["queries"]["u3"]
    assert rec["chat"] == chat_hash(555, KEY) and "555" not in json.dumps(rec, default=str)
    assert "9876543210" not in rec["question"] and "9876543210" not in rec["reply"]
    assert rec["outcome"] == "answered" and rec["lang"] == "hinglish"
    assert rec["costs"] == [{"step": "generate", "cost_inr": 0.02}]
    assert rec["cited"] == ["IN.RTI2005:s6@en@2005-10-12"]


def test_answer_start_command_gets_greeting_without_quota() -> None:
    svc, store, out = make_answer()
    svc({}, push(text="/start"))
    assert out == [(555, "hello")] and store.data["quotas"] == {}


def test_answer_daily_limit_stops_model_calls() -> None:
    calls: list[str] = []

    def respond(q: str) -> tuple[Reply, list[dict[str, Any]]]:
        calls.append(q)
        return Reply("ok", False, None, {}), []

    svc, _, out = make_answer(respond, limit=2)
    for i in range(3):
        svc({}, push(text="RTI kaise du", uid=i))
    assert len(calls) == 2
    assert out[-1] == (555, TEXTS["limit"][detect_lang("RTI kaise du")])


def test_answer_budget_cap_sends_error_text_and_logs_reason() -> None:
    def respond(q: str) -> tuple[Reply, list[dict[str, Any]]]:
        raise BudgetExceededError("cap")

    svc, store, out = make_answer(respond)
    assert svc({}, push(uid=4))[0] == 204
    assert out == [(555, "sorry")]
    assert store.data["queries"]["u4"]["abstain_reason"] == "budget_cap"


def test_answer_send_failure_is_logged_and_acknowledged() -> None:
    svc, store, _ = make_answer(send_fails=True)
    assert svc({}, push(uid=5))[0] == 204
    rec = store.data["queries"]["u5"]
    assert rec["outcome"] == "answered_unsent" and rec["send_error"] == "OSError"


@pytest.mark.parametrize(
    "body", [b"{}", b"nope", json.dumps({"message": {"data": "e30="}}).encode()]
)
def test_answer_malformed_push_is_acknowledged(body: bytes) -> None:
    svc, _, out = make_answer()
    assert svc({}, body)[0] == 204 and out == []


def test_decode_push_roundtrip() -> None:
    assert decode_push(push(chat=9, text="hi"))["chat_id"] == 9


def test_fill_refuses_unknown_contact_ids() -> None:
    assert fill("call {nalsa_15100}", {"nalsa_15100": "15100"}) == "call 15100"
    with pytest.raises(KeyError):
        fill("call {missing}", {})


def test_bot_texts_limit_message_is_approved_and_fillable() -> None:
    from madhya_kanoon_saathi.generation.service import contact_numbers

    texts = json.loads(Path("data/bot_texts.json").read_text(encoding="utf-8"))
    assert texts["status"] == "approved"
    numbers = contact_numbers()
    for lang in ("hi", "hinglish", "en"):
        assert "15100" in fill(texts["limit"][lang], numbers)


# --- daily spend guard (DEC-088) ---


def test_daily_spend_guard_reserves_settles_and_refuses() -> None:
    store = MemoryStore()
    guard = DailySpendGuard(store, cap=0.05, clock=lambda: NOW)
    body = {"messages": [{"role": "user", "content": "x" * 100}], "max_tokens": 1000}
    worst = guard.reserve(body)
    assert 0 < worst < 0.05
    guard.settle(worst, 0.001)
    assert store.data["spend"]["20261121"]["inr"] == pytest.approx(0.001)
    big = {"messages": [], "max_tokens": 5000}  # worst case ≈ ₹0.15 > cap
    with pytest.raises(BudgetExceededError):
        guard.reserve(big)
    assert store.data["spend"]["20261121"]["inr"] == pytest.approx(0.001)


# --- stdlib HTTP server ---


def test_http_server_routes_post_and_health() -> None:
    seen: list[tuple[str, bytes]] = []

    def post(headers: Any, body: bytes) -> tuple[int, bytes]:
        seen.append((headers.get(HEADER, ""), body))
        return 200, b"ok"

    srv = make_server(post, 0, host="127.0.0.1")
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{port}"
        with urllib.request.urlopen(base + "/healthz", timeout=5) as r:
            assert r.status == 200
        req = urllib.request.Request(
            base + "/", data=b"{}", method="POST", headers={"X-Telegram-Bot-Api-Secret-Token": "t"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            assert r.read() == b"ok"
        assert seen == [("t", b"{}")]
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(urllib.request.Request(base + "/x", data=b"", method="POST"))
        assert e.value.code == 404
    finally:
        srv.shutdown()
