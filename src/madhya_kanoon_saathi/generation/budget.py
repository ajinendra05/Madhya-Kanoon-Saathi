"""Spend guard for paid LLM calls: hard cap of ₹10 incl. GST before production (DEC-078).

Before a call, :func:`check` adds the worst case (prompt tokens estimated from the text,
``max_tokens`` as output, verified Sarvam prices) to the amount already spent and refuses the call
if the cap would be exceeded. After the call, :func:`record` appends the actual usage to a
committed ledger. The ledger stores only time, model, purpose, token counts and cost — never
prompts, answers or keys.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CAP_INR = 10.0  # DEC-078: everything before production, GST included
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


def check(body: dict[str, Any], *, ledger: Path = LEDGER, cap: float = CAP_INR) -> float:
    """Worst-case cost of this call; raises BudgetExceededError if it could exceed the cap."""
    worst = cost_inr(estimate_prompt_tokens(body), int(body.get("max_tokens", 2048)))
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
