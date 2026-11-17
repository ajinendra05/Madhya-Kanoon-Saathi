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


def test_tiers_follow_dec075() -> None:
    idx = ExampleIndex(
        vectors={"self_harm": np.array([[1.0, 0.0]])},
        threshold=0.1,
        ordinary=np.array([[0.0, 1.0]]),
    )
    note = route("salary nahi mili", np.array([0.9, 0.3]), idx)  # embedding-only hit
    assert note.tier == "note" and note.categories == ["self_harm"]
    assert note.legal_answer_allowed  # only a rule-detected self-harm switches legal content off
    full = route("main aatmahatya karna chahta hoon", np.array([0.9, 0.3]), idx)
    assert full.tier == "full" and not full.legal_answer_allowed
    assert route("RTI fee kitni hai").tier is None


def test_margin_subtracts_nearest_ordinary_question() -> None:
    idx = ExampleIndex(
        vectors={"cyber_fraud": np.array([[1.0, 0.0]])},
        threshold=0.0,
        ordinary=np.array([[0.8, 0.6]]),
    )
    margin = idx.similarities(np.array([1.0, 0.0]))["cyber_fraud"]
    assert abs(margin - (1.0 - 0.8)) < 1e-6


REPLIES = json.loads(Path("data/safety/crisis_replies.json").read_text(encoding="utf-8"))
NUMBERS = {c.id: c.number for c in load_contacts(Path("data/contacts.yaml"))}


def _templates() -> list[str]:
    out = [t for cat in REPLIES["full"].values() for t in cat.values()]
    return out + list(REPLIES["note"].values())


def test_reply_templates_cover_every_category_and_language() -> None:
    assert set(REPLIES["full"]) == set(CONTACTS)
    for texts in [*REPLIES["full"].values(), REPLIES["note"]]:
        assert set(texts) == {"hi", "hinglish", "en"}


def test_reply_templates_never_hardcode_numbers() -> None:
    import re

    for t in _templates():
        bare = re.sub(r"\{[a-z0-9_]+\}", "", t)
        assert not re.search(r"\d{3,}", bare), t  # numbers come only from contacts.yaml
        for ph in re.findall(r"\{([a-z0-9_]+)\}", t):
            assert ph == "numbers" or ph in NUMBERS, ph


def test_unapproved_wording_is_never_used() -> None:
    from madhya_kanoon_saathi.generation.crisis import render

    if REPLIES["status"] == "approved":
        pytest.skip("wording approved")
    with pytest.raises(PermissionError):
        render(route("pati roz maarta hai"), "hinglish", REPLIES, NUMBERS)


def test_render_full_and_note_tiers() -> None:
    from madhya_kanoon_saathi.generation.crisis import render

    approved = {**REPLIES, "status": "approved"}
    full = render(route("main aatmahatya karna chahta hoon"), "hinglish", approved, NUMBERS)
    assert full.prefix and "14416" in full.prefix and "112" in full.prefix
    assert full.suffix is None and not full.legal_answer_allowed
    idx = ExampleIndex(vectors={"cyber_fraud": np.array([[1.0, 0.0]])}, threshold=0.5)
    note = render(route("kuch hua hai", np.array([1.0, 0.0]), idx), "en", approved, NUMBERS)
    assert note.prefix is None and note.suffix and "1930" in note.suffix
    assert note.legal_answer_allowed
