"""LLM client: Sarvam-105B chat completions (DEC-006, DEC-077). Standard library only.

Verified 2026-11-18 from official docs:
- https://docs.sarvam.ai/api-reference-docs/chat/completions — ``POST
  https://api.sarvam.ai/v1/chat/completions``; ``Authorization: Bearer`` / ``api-subscription-key``
  header; models ``sarvam-105b`` (128K context) and ``sarvam-105b-conversations`` (32K);
  ``response_format = {"type": "json_schema", "json_schema": {name, schema, strict}}``;
  ``reasoning_effort`` none|low|medium|high|max (default medium; reasoning tokens billed as
  output); text in ``choices[0].message.content``; usage in ``usage.{prompt,completion}_tokens``.
- https://docs.sarvam.ai/api-reference-docs/getting-started/pricing — ₹10 input / ₹0.25 cached
  input / ₹25 output per 1M tokens excl. GST (introductory, through end-2026); 60 req/min on
  pay-as-you-go.

The key comes from the environment (``SARVAM_API_KEY``; locally loaded from ``.env``, in production
from SSM, DEC-009). It is never printed, logged or included in error messages.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ENDPOINT = "https://api.sarvam.ai/v1/chat/completions"
MODEL = "sarvam-105b"
PRICE_INR_PER_M = {"input": 10.0, "cached_input": 0.25, "output": 25.0}  # excl. GST, see above
_RETRY_STATUS = (429, 500, 502, 503, 504)


@dataclass(frozen=True)
class Completion:
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str

    @property
    def cost_inr(self) -> float:
        return (
            self.prompt_tokens * PRICE_INR_PER_M["input"]
            + self.completion_tokens * PRICE_INR_PER_M["output"]
        ) / 1_000_000


def api_key(env_file: Path = Path(".env")) -> str:
    """SARVAM_API_KEY from the environment, else from a local .env (value never echoed)."""
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "SARVAM_API_KEY":
                key = value.strip().strip('"').strip("'")
    if not key:
        raise RuntimeError("SARVAM_API_KEY is not set (.env locally, SSM in production)")
    return key


def request_body(
    messages: list[dict[str, str]],
    schema: dict[str, Any] | None = None,
    *,
    model: str = MODEL,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    reasoning_effort: str = "low",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "reasoning_effort": reasoning_effort,
    }
    if schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "answer", "schema": schema, "strict": True},
        }
    return body


def parse_response(data: dict[str, Any]) -> Completion:
    msg = data["choices"][0]["message"]
    usage = data.get("usage") or {}
    return Completion(
        content=msg.get("content") or "",
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
        model=str(data.get("model", "")),
    )


def complete(body: dict[str, Any], *, timeout: float = 60.0, retries: int = 2) -> Completion:
    """One paid call (with retries on 429/5xx). Raises RuntimeError without the key in it."""
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    key = api_key()
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            ENDPOINT,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "api-subscription-key": key,
                "Authorization": f"Bearer {key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return parse_response(json.loads(resp.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            if e.code in _RETRY_STATUS and attempt < retries:
                time.sleep(2**attempt)
                continue
            raise RuntimeError(f"Sarvam HTTP {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(2**attempt)
                continue
            raise RuntimeError(f"Sarvam unreachable: {e.reason}") from None
    raise RuntimeError("unreachable")
