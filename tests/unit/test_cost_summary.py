"""Nightly cost summary (W3.2, DEC-095): Firestore REST decoding, IST day bounds, aggregates only."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

SPEC = importlib.util.spec_from_file_location("cost_summary", Path("scripts/cost_summary.py"))
assert SPEC and SPEC.loader
cs = importlib.util.module_from_spec(SPEC)
sys.modules["cost_summary"] = cs
SPEC.loader.exec_module(cs)


def test_decode_firestore_typed_values() -> None:
    doc = {
        "fields": {
            "lang": {"stringValue": "hi"},
            "n": {"integerValue": "3"},
            "x": {"doubleValue": 0.5},
            "ok": {"booleanValue": True},
            "none": {"nullValue": None},
            "at": {"timestampValue": "2026-11-24T04:00:00Z"},
            "costs": {
                "arrayValue": {
                    "values": [{"mapValue": {"fields": {"step": {"stringValue": "generate"}}}}]
                }
            },
        }
    }
    f = cs.fields(doc)
    assert f == {
        "lang": "hi",
        "n": 3,
        "x": 0.5,
        "ok": True,
        "none": None,
        "at": "2026-11-24T04:00:00Z",
        "costs": [{"step": "generate"}],
    }


def test_day_bounds_are_indian_midnights_in_utc() -> None:
    assert cs.day_bounds(date(2026, 11, 24)) == ("2026-11-23T18:30:00Z", "2026-11-24T18:30:00Z")


RECORDS: list[dict[str, Any]] = [
    {
        "lang": "hinglish",
        "question": "mera number 98xxxxxxxx",
        "reply": "…",
        "chat": "a" * 32,
        "outcome": "answered",
        "abstain_reason": None,
        "crisis": {"tier": "note"},
        "timings_ms": {"total": 6000},
        "costs": [
            {
                "step": "rewrite",
                "provider": "free:api.groq.com",
                "cost_inr": 0.0,
                "latency_ms": 200,
            },
            {"step": "generate", "provider": "sarvam", "cost_inr": 0.02, "latency_ms": 500},
        ],
    },
    {
        "lang": "hi",
        "outcome": "answered",
        "abstain_reason": "no claim could be verified",
        "crisis": {"tier": "none"},
        "timings_ms": {"total": 8000},
        "costs": [{"step": "generate", "provider": "sarvam", "cost_inr": 0.03, "latency_ms": 700}],
    },
    {"lang": "en", "outcome": "answered", "help": True, "timings_ms": {"total": 100}, "costs": []},
]


def test_summary_counts_costs_and_times() -> None:
    s = cs.summarise(date(2026, 11, 24), RECORDS, {"inr": 0.05, "calls": 2})
    assert s["questions"] == 3 and s["abstained"] == 1 and s["topic_lists"] == 1
    assert s["crisis"] == {"full": 0, "note": 1}
    assert s["languages"] == {"hinglish": 1, "hi": 1, "en": 1}
    assert s["inr_total"] == 0.05 and s["inr_per_question"] == round(0.05 / 3, 4)
    assert s["steps"]["generate"]["calls"] == 2 and s["steps"]["rewrite"]["inr"] == 0.0
    assert s["providers"] == {"free:api.groq.com": 1, "sarvam": 2}
    assert s["time_s"]["p50"] == 6.0 and s["spend_counter"] == {"inr": 0.05, "calls": 2}


def test_summary_publishes_no_text_or_identifiers() -> None:
    s = json.dumps(cs.summarise(date(2026, 11, 24), RECORDS, None))
    for leak in ("mera number", "98xxxxxxxx", "a" * 32, "no claim could be verified"):
        assert leak not in s


def test_publish_merges_history_by_date(tmp_path: Path) -> None:
    for d, n in (("2026-11-23", 1), ("2026-11-24", 2), ("2026-11-24", 3)):
        s = cs.summarise(date.fromisoformat(d), RECORDS[:n], None)
        cs.publish(s, tmp_path)
    hist = json.loads((tmp_path / "data" / "history.json").read_text("utf-8"))
    assert [h["date"] for h in hist] == ["2026-11-23", "2026-11-24"]
    assert hist[-1]["questions"] == 3  # the re-run replaced the day
    assert (tmp_path / "index.html").exists()
