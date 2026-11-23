"""Free hosted LLM for query rewriting only (DEC-092). OpenAI-compatible chat API, stdlib only.

Default provider: Groq (``https://api.groq.com/openai/v1``). Its data page says inference inputs are
not retained by default (console.groq.com/docs/your-data, read 2026-11-23); the service runs outside
India, so the question is **redacted** (``common/redact.py``: phone, Aadhaar, caste, health …)
before it is sent, and this client is used for nothing but search rewrites (never answers).

Settings (environment or ``.env``): ``MKS_REWRITE_BASE_URL``, ``MKS_REWRITE_MODEL``, key
``GROQ_API_KEY``. Free plans are rate-limited; any error (429, 5xx, timeout) raises, and the caller
(:func:`madhya_kanoon_saathi.generation.rewrite.rewrite`) falls back to the original question, so a
limit never costs money or blocks an answer. The rate-limit headers of the last reply are kept in
:attr:`FreeLLM.last_limits` (no content) so the real free-plan limits can be read and logged.
"""

from __future__ import annotations

import http.client
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from madhya_kanoon_saathi.common.env import secret
from madhya_kanoon_saathi.common.redact import redact

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
KEY_NAME = "GROQ_API_KEY"
# Groq's edge (Cloudflare) answers Python's default "Python-urllib" agent with 403 "error code:
# 1010" (seen 2026-11-23); a plain project agent works. Generic: no personal or contact details.
USER_AGENT = "madhya-kanoon-saathi/0.1"
_LIMIT_HEADERS = (
    "x-ratelimit-limit-requests",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-tokens",
)


class FreeLLMError(RuntimeError):
    """A free-provider call failed (message never contains the key or the question)."""


@dataclass
class FreeLLM:
    key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = 8.0
    max_tokens: int = 200
    last_limits: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> FreeLLM:
        return cls(
            key=secret(KEY_NAME),
            base_url=os.environ.get("MKS_REWRITE_BASE_URL", "").strip() or DEFAULT_BASE_URL,
            model=os.environ.get("MKS_REWRITE_MODEL", "").strip() or DEFAULT_MODEL,
        )

    def __call__(self, messages: list[dict[str, str]]) -> str:
        """Chat completion; user messages are redacted first. Returns the reply text."""
        safe = [
            {**m, "content": redact(m["content"]).text} if m.get("role") == "user" else m
            for m in messages
        ]
        body = {
            "model": self.model,
            "messages": safe,
            "max_tokens": self.max_tokens,
            "temperature": 0.1,
        }
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.key}",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                self.last_limits = {
                    h: resp.headers.get(h, "") for h in _LIMIT_HEADERS if resp.headers.get(h)
                }
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            wait = e.headers.get("retry-after") if e.headers else None
            raise FreeLLMError(
                f"free LLM HTTP {e.code}" + (f" retry-after {wait}s" if wait else "")
            ) from None
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            # URLError, timeouts, and dropped connections (RemoteDisconnected, seen 2026-11-23)
            raise FreeLLMError(f"free LLM network error ({type(e).__name__})") from None
        try:
            return str(data["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError):
            raise FreeLLMError("free LLM reply had no message") from None
