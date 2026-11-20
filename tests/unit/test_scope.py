"""Topic questions and the topic list (DEC-082)."""

import json
from pathlib import Path

import pytest

from madhya_kanoon_saathi.generation.scope import is_help_request, render

TOPICS = json.loads(Path("data/help_topics.json").read_text(encoding="utf-8"))
MANIFEST = json.loads(Path("data/corpus_manifest.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "q",
    [
        "aap mujhe kis kis topic me help kar sakte hai",
        "aap kis kis topic me help kar sakte ho?",
        "kaun kaun se vishay par jaankari dete ho",
        "tum kya kya bata sakte ho",
        "aap kya kar sakte ho",
        "kin topics par madad milegi",
        "आप किन विषयों पर जानकारी देते हैं?",
        "आप मुझे किस किस टॉपिक में मदद कर सकते हैं",
        "आप क्या क्या बता सकते हैं",
        "What can you help me with?",
        "which topics do you cover",
        "what can you do",
        "What kind of questions can you answer?",
        "how can you help me",
    ],
)
def test_topic_questions_are_detected(q: str) -> None:
    assert is_help_request(q)


@pytest.mark.parametrize(
    "q",
    [
        "RTI ke liye kya kya documents chahiye",
        "RTI me kya kya bata sakte ho",
        "minimum wage kitna hai MP mein",
        "what do you mean by deficiency in service",
        "मकान मालिक किराया बढ़ाने के लिए क्या कर सकता है",
        "landlord ne ghar khali karne ko kaha, kya kar sakte hai",
        "What can I do if the shop charged more than MRP?",
        "seemankan ke liye kya kya karna padega",
        "",
    ],
)
def test_real_questions_are_not_topic_questions(q: str) -> None:
    assert not is_help_request(q)


def test_every_topic_relies_on_indexed_or_guide_sources() -> None:
    live = {d["instrument_id"] for d in MANIFEST["documents"] if d["mode"] in ("index", "guide")}
    for t in TOPICS["topics"]:
        assert t["instruments"], t["id"]
        missing = set(t["instruments"]) - live
        assert not missing, f"{t['id']}: {sorted(missing)} not indexed"


def test_every_indexed_instrument_appears_in_a_topic() -> None:
    live = {d["instrument_id"] for d in MANIFEST["documents"] if d["mode"] in ("index", "guide")}
    listed = {i for t in TOPICS["topics"] for i in t["instruments"]}
    assert live <= listed, f"not described to users: {sorted(live - listed)}"


@pytest.mark.parametrize("lang", ["hi", "hinglish", "en"])
def test_render_has_every_topic_in_each_language(lang: str) -> None:
    full, short = render(TOPICS, lang), render(TOPICS, lang, abstain=True)
    for t in TOPICS["topics"]:
        assert t[lang] in full and t[lang] in short
    assert TOPICS["outro"][lang] in full and TOPICS["outro"][lang] not in short


def test_unapproved_topics_are_refused() -> None:
    with pytest.raises(PermissionError):
        render({**TOPICS, "status": "draft"}, "en")
