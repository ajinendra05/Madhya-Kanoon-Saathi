"""Free hosted LLM client for query rewriting (DEC-092): redaction, limits, errors. No network."""

from __future__ import annotations

import io
import json
import urllib.error
from typing import Any

import pytest

from madhya_kanoon_saathi.generation import free_llm, rewrite
from madhya_kanoon_saathi.generation.free_llm import FreeLLM, FreeLLMError


class _Resp(io.BytesIO):
    def __init__(self, payload: dict[str, Any], headers: dict[str, str]) -> None:
        super().__init__(json.dumps(payload).encode())
        self.headers = headers

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *a: object) -> None:
        return None


def test_question_is_redacted_and_limits_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float) -> _Resp:
        sent["url"] = req.full_url
        sent["auth"] = req.headers["Authorization"]
        sent["ua"] = req.get_header("User-agent")
        sent["body"] = json.loads(req.data)
        return _Resp(
            {"choices": [{"message": {"content": '{"en": "x", "hi": "y"}'}}]},
            {"x-ratelimit-remaining-requests": "14399", "x-ratelimit-limit-requests": "14400"},
        )

    monkeypatch.setattr(free_llm.urllib.request, "urlopen", fake_urlopen)
    llm = FreeLLM(key="k", base_url="https://api.example.com/openai/v1", model="m")
    out = llm(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "mera number 9876543210 hai"},
        ]
    )
    assert out == '{"en": "x", "hi": "y"}'
    assert sent["url"] == "https://api.example.com/openai/v1/chat/completions"
    user = sent["body"]["messages"][1]["content"]
    assert "9876543210" not in user and "[PHONE]" in user
    assert sent["body"]["messages"][0]["content"] == "sys" and sent["body"]["model"] == "m"
    assert llm.last_limits["x-ratelimit-limit-requests"] == "14400"
    assert sent["ua"] == "madhya-kanoon-saathi/0.1"  # not Python-urllib (Cloudflare 1010)


def test_http_errors_raise_without_details(monkeypatch: pytest.MonkeyPatch) -> None:
    def rate_limited(req: Any, timeout: float) -> _Resp:
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO(b"secret"))  # type: ignore[arg-type]

    monkeypatch.setattr(free_llm.urllib.request, "urlopen", rate_limited)
    with pytest.raises(FreeLLMError) as e:
        FreeLLM(key="sk-abc")([{"role": "user", "content": "q"}])
    assert "429" in str(e.value) and "sk-abc" not in str(e.value)


def test_rate_limit_falls_back_to_the_original_question(monkeypatch: pytest.MonkeyPatch) -> None:
    def down(req: Any, timeout: float) -> _Resp:
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(free_llm.urllib.request, "urlopen", down)
    errors: list[Exception] = []
    assert rewrite.rewrite("RTI kaise du", FreeLLM(key="k"), errors.append) == []
    assert isinstance(errors[0], FreeLLMError)


def test_parse_accepts_json_inside_prose_or_fences() -> None:
    raw = 'Sure!\n```json\n{"en": "defective goods trader refund", "hi": "दोषपूर्ण माल"}\n```'
    assert rewrite.parse(raw, "kharab saman").queries == [
        "defective goods trader refund",
        "दोषपूर्ण माल",
    ]


def test_no_key_disables_rewriting(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    from madhya_kanoon_saathi.handlers.answer import free_rewriter

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here
    assert free_rewriter([]) is None


def test_dropped_connection_becomes_free_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import http.client

    def dropped(req: Any, timeout: float) -> _Resp:
        raise http.client.RemoteDisconnected("Remote end closed connection without response")

    monkeypatch.setattr(free_llm.urllib.request, "urlopen", dropped)
    with pytest.raises(FreeLLMError, match="RemoteDisconnected"):
        FreeLLM(key="k")([{"role": "user", "content": "q"}])
