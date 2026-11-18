"""Spend cap for paid LLM calls (DEC-078). No network: the call itself is never reached."""

import json
from pathlib import Path

import pytest

from madhya_kanoon_saathi.generation import budget, llm


def body(max_tokens: int = 600) -> dict:  # type: ignore[type-arg]
    return llm.request_body([{"role": "user", "content": "RTI fee? " * 50}], max_tokens=max_tokens)


def test_cost_includes_gst() -> None:
    assert budget.cost_inr(1_000_000, 0) == pytest.approx(11.8)
    assert budget.cost_inr(0, 1_000_000) == pytest.approx(29.5)


def test_ledger_accumulates_and_never_stores_text(tmp_path: Path) -> None:
    led = tmp_path / "ledger.jsonl"
    budget.record(
        model="sarvam-105b", purpose="t", prompt_tokens=1000, completion_tokens=500, ledger=led
    )
    budget.record(
        model="sarvam-105b", purpose="t", prompt_tokens=1000, completion_tokens=500, ledger=led
    )
    assert budget.spent(led) == pytest.approx(2 * budget.cost_inr(1000, 500))
    row = json.loads(led.read_text(encoding="utf-8").splitlines()[0])
    assert set(row) == {
        "at",
        "model",
        "purpose",
        "prompt_tokens",
        "completion_tokens",
        "cost_inr_incl_gst",
    }


def test_call_refused_before_spending_when_cap_would_be_exceeded(tmp_path: Path) -> None:
    led = tmp_path / "ledger.jsonl"
    budget.record(
        model="m", purpose="t", prompt_tokens=840_000, completion_tokens=0, ledger=led
    )  # ~Rs9.91
    with pytest.raises(budget.BudgetExceededError):
        budget.check(body(max_tokens=10_000), ledger=led)
    with pytest.raises(budget.BudgetExceededError):  # complete() checks before any key or network
        llm.complete(body(max_tokens=10_000), purpose="t", ledger=led)


def test_small_call_allowed_under_cap(tmp_path: Path) -> None:
    worst = budget.check(body(), ledger=tmp_path / "empty.jsonl")
    assert 0 < worst < 0.05  # a few paise
