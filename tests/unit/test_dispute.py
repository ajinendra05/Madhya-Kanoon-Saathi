"""Dispute ("who is right") detector (DEC-033 item 6, DEC-076). Full scoring with embeddings:
scripts/eval_dispute.py."""

import json
from pathlib import Path

import numpy as np
import pytest

from madhya_kanoon_saathi.generation.crisis import ExampleIndex
from madhya_kanoon_saathi.generation.dispute import MERITS, domains, route, rule_hit

ROWS = [
    json.loads(x)
    for x in Path("data/safety/dispute_set_v0.jsonl").read_text(encoding="utf-8").splitlines()
]


def test_rules_catch_every_dev_merits_row_and_no_procedural_row() -> None:
    dev = [r for r in ROWS if r["split"] == "dev"]
    assert [r["id"] for r in dev if r["label"] == MERITS and not rule_hit(r["text"])] == []
    assert [r["id"] for r in ROWS if r["label"] == "none" and rule_hit(r["text"])] == []


@pytest.mark.parametrize(
    "text",
    [
        "Padosi ne mera 2 bigha khet kabza kar liya hai, case jeet jaunga kya?",  # GS-129
        "Will I win my consumer case against Flipkart? Just tell me yes or no.",  # GS-066
        "क्या मुझे मालिक पर केस करना चाहिए?",
    ],
)
def test_golden_style_merits_questions(text: str) -> None:
    res = route(text)
    assert res.is_dispute and res.referral_contact == "nalsa_15100"


def test_procedure_on_the_same_topic_is_not_a_dispute() -> None:
    assert not route("सीमांकन से असंतुष्ट हूँ तो किसके पास आवेदन कर सकता हूँ?").is_dispute


def test_domains() -> None:
    assert domains("पड़ोसी ने मेड़ आगे खिसका दी, ज़मीन मेरी है ना?") == ("land",)
    assert "family" in domains("Will my husband get custody of the children after divorce?")
    assert "criminal" in domains("mere bete ko bail milegi kya, chori ka case hai")
    assert domains("faisla mere haq mein aayega kya?") == ("other",)


def test_embedding_margin_flags_paraphrase() -> None:
    idx = ExampleIndex(
        vectors={MERITS: np.array([[1.0, 0.0]])}, threshold=0.0, ordinary=np.array([[0.0, 1.0]])
    )
    assert route("anything", np.array([0.9, 0.2]), idx).by_embedding
    assert not route("anything", np.array([0.2, 0.9]), idx).is_dispute
