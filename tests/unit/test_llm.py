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
    assert "[E1]" in msgs[1]["content"]  # short label; code maps it back (ref_map)
    assert "IN.RTIR2012" not in msgs[1]["content"]


def test_parse_answer_maps_labels_and_tolerates_fences_and_trailing_junk() -> None:
    from madhya_kanoon_saathi.generation.pipeline import parse_answer

    refs = {"E1": "IN.RTIR2012:r3@en@2012-07-31"}
    obj = {
        "answer_blocks": [
            {"text": "x", "citations": [{"ref": "[E1]", "quote": "q"}, {"ref": "E9", "quote": "q"}]}
        ],
        "abstain": False,
        "abstain_reason": None,
    }
    fence = "`" * 3
    raw = fence + "json" + chr(10) + json.dumps(obj) + chr(10) + fence + "   " + chr(10) * 3
    cits = parse_answer(raw, refs)["answer_blocks"][0]["citations"]
    assert cits[0]["chunk_id"] == refs["E1"]
    assert cits[1]["chunk_id"] == "unknown-ref:E9"  # the validator will reject it
    with pytest.raises(ValueError):
        parse_answer("no json here", refs)


def test_json_object_mode() -> None:
    body = request_body([{"role": "user", "content": "x"}], "json_object")
    assert body["response_format"] == {"type": "json_object"}
