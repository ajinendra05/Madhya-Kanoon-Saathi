"""Local Telegram bot loop with a fake client (no network, no token)."""

from typing import Any

from madhya_kanoon_saathi.bot.telegram import handle_update, run, split_text

TEXTS = {"start": "hello", "error": "sorry", "not_allowed": "private"}


class FakeClient:
    def __init__(self, batches: list[list[dict[str, Any]]]) -> None:
        self.batches, self.sent, self.offsets = list(batches), [], []  # type: ignore[var-annotated]

    def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        self.offsets.append(offset)
        return self.batches.pop(0) if self.batches else []

    def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


def upd(uid: int, chat: int, text: str) -> dict[str, Any]:
    return {"update_id": uid, "message": {"chat": {"id": chat}, "text": text}}


def test_split_text_keeps_parts_under_limit() -> None:
    text = "\n\n".join("x" * 3000 for _ in range(3))
    parts = split_text(text)
    assert len(parts) == 3 and all(len(p) <= 4096 for p in parts)
    assert split_text("short") == ["short"]


def test_start_answer_error_and_allow_list() -> None:
    c = FakeClient([])
    assert handle_update(upd(1, 7, "/start"), c, lambda q: "A", TEXTS, None) == "start"
    assert handle_update(upd(2, 7, "RTI fee?"), c, lambda q: "A:" + q, TEXTS, None) == "answered"

    def boom(q: str) -> str:
        raise RuntimeError("secret detail")

    assert handle_update(upd(3, 7, "x"), c, boom, TEXTS, None) == "error (RuntimeError)"
    assert handle_update(upd(4, 9, "x"), c, lambda q: "A", TEXTS, frozenset({7})).startswith(
        "refused"
    )
    assert c.sent == [(7, "hello"), (7, "A:RTI fee?"), (7, "sorry"), (9, "private")]
    assert all("secret detail" not in t for _, t in c.sent)  # errors never leak to users


def test_run_confirms_updates_with_offset() -> None:
    c = FakeClient([[upd(10, 7, "a"), upd(11, 7, "b")], []])
    logs: list[str] = []
    run(c, lambda q: "ok", TEXTS, max_loops=2, log=logs.append)
    assert c.offsets == [None, 12] and len(c.sent) == 2
    assert all(line != "a" for line in logs)  # console log has no message text
