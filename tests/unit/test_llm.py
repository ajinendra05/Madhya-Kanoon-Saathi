"""Sarvam client and prompt, offline (no network, no key needed). Live calls: DEC-077 contract test."""

import json
from pathlib import Path

import pytest

from madhya_kanoon_saathi.generation.llm import api_key, parse_response, request_body
from madhya_kanoon_saathi.generation.prompt import ANSWER_SCHEMA, build_messages


def test_request_body_uses_verified_fields() -> None:
    body = request_body([{"role": "user", "content": "hi"}], ANSWER_SCHEMA, reasoning_effort="none")
    assert body["model"] == "sarvam-105b"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"] is ANSWER_SCHEMA
    assert body["reasoning_effort"] == "none"
    json.dumps(body)  # serialisable


def test_parse_response_and_cost() -> None:
    comp = parse_response(
        {
            "model": "sarvam-105b",
            "choices": [{"message": {"content": '{"abstain": true}'}}],
            "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
        }
    )
    assert comp.content == '{"abstain": true}'
    assert comp.cost_inr == pytest.approx(35.0)  # Rs10 in + Rs25 out per 1M (docs 2026-11-18)


def test_api_key_from_env_file_and_missing_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    f = tmp_path / ".env"
    f.write_text("OTHER=x\nSARVAM_API_KEY='sk_test_value'\n", encoding="utf-8")
    assert api_key(f) == "sk_test_value"
    with pytest.raises(RuntimeError) as err:
        api_key(tmp_path / "missing.env")
    assert "sk_" not in str(err.value)  # the message never contains a key


def test_messages_carry_chunk_ids_and_language() -> None:
    msgs = build_messages("RTI fee?", [("IN.RTIR2012:r3@en@2012-07-31", "fee of rupees ten")], "hi")
    assert "Hindi (Devanagari)" in msgs[0]["content"]
    assert "[IN.RTIR2012:r3@en@2012-07-31]" in msgs[1]["content"]
