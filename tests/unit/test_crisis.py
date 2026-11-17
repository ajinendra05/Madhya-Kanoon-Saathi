"""Crisis router, rules layer and result logic (DEC-033 item 1, DEC-074).

The golden crisis rows (GS-020, GS-113, GS-114, GS-115, GS-120) must always be caught by the rules
alone; the full set (data/safety/crisis_set_v0.jsonl) is scored by scripts/eval_crisis.py."""

import json
from pathlib import Path

import numpy as np
import pytest

from madhya_kanoon_saathi.common.contacts import load as load_contacts
from madhya_kanoon_saathi.generation.crisis import CONTACTS, ExampleIndex, route, rule_categories

SET = Path("data/safety/crisis_set_v0.jsonl")
ROWS = [json.loads(x) for x in SET.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("row", [r for r in ROWS if r["source"].startswith("golden:")], ids=str)
def test_golden_crisis_rows_caught_by_rules(row: dict) -> None:  # type: ignore[type-arg]
    assert row["label"] in rule_categories(row["text"])


def test_rules_catch_every_dev_and_test_crisis_row() -> None:
    missed = [
        r["id"]
        for r in ROWS
        if r["split"] in ("dev", "test")
        and r["label"] != "none"
        and r["label"] not in rule_categories(r["text"])
    ]
    assert missed == []


def test_rules_raise_no_alarm_on_lookalike_legal_questions() -> None:
    alarms = [r["id"] for r in ROWS if r["label"] == "none" and rule_categories(r["text"])]
    assert alarms == []


@pytest.mark.parametrize(
    "text",
    [
        "मालिक ने दो महीने का वेतन मार लिया है",  # "मार लिया" = withheld, not violence
        "The killer whale documentary was never delivered",
        "मकान मालिक मुझे घर खाली करने का नोटिस दे रहा है",
    ],
)
def test_specific_false_friends(text: str) -> None:
    assert rule_categories(text) == []


def test_nukta_and_chandrabindu_variants_match() -> None:
    assert rule_categories("रात में कहाँ जाऊँ, मालिक ने ताला लगा दिया") == ["eviction_now"]
    assert rule_categories("रोज़ छेड़छाड़ करते हैं") == ["violence_now"]


def test_self_harm_blocks_legal_answer_and_contacts_are_deduplicated() -> None:
    res = route("पति रोज़ मारता है, अब मैं आत्महत्या करना चाहती हूँ")
    assert res.categories == ["self_harm", "domestic_violence"]
    assert not res.legal_answer_allowed
    assert res.contact_ids == ["telemanas_14416", "erss_112", "women_181"]


def test_embedding_layer_adds_categories_at_threshold() -> None:
    idx = ExampleIndex(vectors={"cyber_fraud": np.array([[1.0, 0.0]])}, threshold=0.8)
    assert route("anything", np.array([0.9, 0.1]), idx).by_embedding == ["cyber_fraud"]
    assert route("anything", np.array([0.1, 0.9]), idx).categories == []


def test_every_router_contact_is_sourced() -> None:
    ids = {c.id for c in load_contacts(Path("data/contacts.yaml"))}
    assert {x for v in CONTACTS.values() for x in v} <= ids
