"""Query-side jurisdiction guard (DEC-016, DEC-033 item 5)."""

import pytest

from madhya_kanoon_saathi.generation.jurisdiction import check


@pytest.mark.parametrize(
    ("text", "states"),
    [
        ("Rajasthan mein kiraya kanoon kya hai", ("RJ",)),
        ("उत्तर प्रदेश में दाखिल खारिज कैसे होता है", ("UP",)),
        ("UP mein zameen ka namantaran", ("UP",)),
        ("Chhattisgarh me automatic mutation", ("CG",)),
        ("I live in Mumbai, can my landlord evict me?", ("MH",)),
    ],
)
def test_other_state_questions(text: str, states: tuple[str, ...]) -> None:
    c = check(text)
    assert c.states == states and c.other_state_only


@pytest.mark.parametrize(
    "text",
    [
        "मध्यप्रदेश में न्यूनतम मजदूरी कितनी है",
        "MP mein RTI fee kitni hai",
        "UP se MP aaya hoon, yahan ration card kaise banega",  # names MP too: in scope
        "RTI application ki fees kitni hai",  # no state: MP + central by default
        "New Delhi, the 17th May, 2021 notification",  # central gazette header
        "jaipuri razai kharab nikli, refund chahiye",  # not the city
    ],
)
def test_in_scope_questions(text: str) -> None:
    assert not check(text).other_state_only


def test_mp_city_keeps_question_in_scope() -> None:
    # golden GS-054: company in Delhi, consumer in Jabalpur (MP)
    c = check("कंपनी दिल्ली की है, क्या मैं जबलपुर से ही शिकायत कर सकता हूँ?")
    assert c.states == ("MP", "DL") and not c.other_state_only
