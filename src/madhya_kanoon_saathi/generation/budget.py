"""Spend guard for paid LLM calls: hard cap of ₹10 incl. GST before production (DEC-078).

Before a call, :func:`check` adds the worst case (prompt tokens estimated from the text,
``max_tokens`` as output, verified Sarvam prices) to the amount already spent and refuses the call
if the cap would be exceeded. After the call, :func:`record` appends the actual usage to a
committed ledger. The ledger stores only time, model, purpose, token counts and cost — never
prompts, answers or keys.

In the cloud the ledger file would be lost on every restart, so production uses
:class:`DailySpendGuard` instead: a ₹20/day cap held in Firestore ``spend/{YYYYMMDD}`` (DEC-088).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

CAP_INR = 10.0  # DEC-078: everything before production, GST included
DAILY_CAP_INR = 20.0  # DEC-088: production, per Indian calendar day, GST included
GST = 0.18
LEDGER = Path("data/spend/llm_ledger.jsonl")
PRICE_INR_PER_M = {"input": 10.0, "output": 25.0}  # sarvam-105b, verified 2026-11-18 (DEC-077)


class BudgetExceededError(RuntimeError):
    """A paid call was refused because it could push spending past the cap."""


def cost_inr(prompt_tokens: int, completion_tokens: int) -> float:
    """Cost including GST."""
    base = prompt_tokens * PRICE_INR_PER_M["input"] + completion_tokens * PRICE_INR_PER_M["output"]
    return base / 1_000_000 * (1 + GST)


def estimate_prompt_tokens(body: dict[str, Any]) -> int:
    """Generous estimate: ~1 token per 2 characters (Devanagari is token-dense) + overhead."""
    text = json.dumps(body.get("messages", []), ensure_ascii=False)
    schema = json.dumps(body.get("response_format", {}), ensure_ascii=False)
    return (len(text) + len(schema)) // 2 + 100


def spent(ledger: Path = LEDGER) -> float:
    if not ledger.is_file():
        return 0.0
    return sum(
        float(json.loads(line)["cost_inr_incl_gst"])
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def worst_case(body: dict[str, Any]) -> float:
    """Most this call can cost, incl. GST: estimated prompt + ``max_tokens`` of output."""
    return cost_inr(estimate_prompt_tokens(body), int(body.get("max_tokens", 2048)))


def check(body: dict[str, Any], *, ledger: Path = LEDGER, cap: float = CAP_INR) -> float:
    """Worst-case cost of this call; raises BudgetExceededError if it could exceed the cap."""
    worst = worst_case(body)
    already = spent(ledger)
    if already + worst > cap:
        raise BudgetExceededError(
            f"paid call refused: spent ₹{already:.4f} + worst case ₹{worst:.4f} > cap ₹{cap:.2f} "
            "(DEC-078; raising the cap needs a new decision)"
        )
    return worst


def record(
    *,
    model: str,
    purpose: str,
    prompt_tokens: int,
    completion_tokens: int,
    ledger: Path = LEDGER,
) -> float:
    """Append the actual usage; returns the cost incl. GST."""
    cost = cost_inr(prompt_tokens, completion_tokens)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": model,
        "purpose": purpose,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_inr_incl_gst": round(cost, 6),
    }
    with ledger.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row) + "\n")
    return cost


class SpendCounter(Protocol):
    def add_spend(self, inr: float, now: datetime, cap: float | None = None) -> bool: ...


class DailySpendGuard:
    """Production cap (DEC-088): reserve the worst case before a call, settle to the actual cost
    after it. A failed call keeps its reservation (it may still have been billed)."""

    def __init__(
        self,
        store: SpendCounter,
        cap: float = DAILY_CAP_INR,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.store, self.cap, self.clock = store, cap, clock

    def reserve(self, body: dict[str, Any]) -> float:
        worst = worst_case(body)
        if not self.store.add_spend(worst, self.clock(), cap=self.cap):
            raise BudgetExceededError(
                f"paid call refused: today's spend would pass the daily cap ₹{self.cap:.2f} "
                "(DEC-088; raising it needs a new decision)"
            )
        return worst

    def settle(self, reserved: float, actual: float) -> None:
        self.store.add_spend(actual - reserved, self.clock())
