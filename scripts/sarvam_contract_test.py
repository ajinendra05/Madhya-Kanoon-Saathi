"""The single DEC-077 contract test: one tiny paid Sarvam call (~2 paise), saved as a fixture.

Usage (approved once by Malik, DEC-077; do not loop or rerun casually):
    uv run python scripts/sarvam_contract_test.py

Sends the golden question GS-074 ("RTI application fee") with its real retrieved chunk
IN.RTIR2012:r3 to sarvam-105b with structured JSON output, then runs the citation validator.
Writes tests/fixtures/sarvam/contract_gs074.json (request without key, response content, usage,
validation result). The API key is read from the environment / .env and never printed.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from madhya_kanoon_saathi.generation.llm import complete, request_body
from madhya_kanoon_saathi.generation.prompt import ANSWER_SCHEMA, PROMPT_VERSION, build_messages
from madhya_kanoon_saathi.generation.validator import validate

OUT = Path("tests/fixtures/sarvam/contract_gs074.json")
QUESTION = "RTI application ki fees kitni hai central government ke liye?"
CHUNK_ID = "IN.RTIR2012:r3@en@2012-07-31"


def main() -> int:
    chunk = next(
        json.loads(line)
        for line in Path("data/parsed/chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if json.loads(line)["chunk_id"] == CHUNK_ID
    )
    context = {CHUNK_ID: chunk["text"]}
    body = request_body(
        build_messages(QUESTION, [(CHUNK_ID, chunk["text"])], "hinglish"),
        ANSWER_SCHEMA,
        max_tokens=600,
        reasoning_effort="low",  # the API rejects "none" (HTTP 400, 2026-11-18)
    )
    if OUT.exists():
        print(f"{OUT} exists: the contract test has already been run; not calling again")
        return 0
    started = datetime.now(UTC)
    comp = complete(body, purpose="contract_test_gs074")
    try:
        answer = json.loads(comp.content)
        parse_error = None
    except json.JSONDecodeError as e:
        answer, parse_error = None, str(e)
    v = validate(answer, context) if answer is not None else None
    record = {
        "run_at": started.isoformat(timespec="seconds"),
        "prompt_version": PROMPT_VERSION,
        "request": body,
        "response": {"model": comp.model, "content": comp.content},
        "usage": {"prompt_tokens": comp.prompt_tokens, "completion_tokens": comp.completion_tokens},
        "cost_inr_excl_gst": round(comp.cost_inr, 4),
        "json_parse_error": parse_error,
        "validation": None
        if v is None
        else {
            "supported_blocks": len(v.supported),
            "dropped": [r for _, r in v.dropped],
            "errors": v.errors,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")
    print(
        json.dumps({k: record[k] for k in ("usage", "cost_inr_excl_gst", "validation")}, indent=1)
    )
    print("answer:", comp.content[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
