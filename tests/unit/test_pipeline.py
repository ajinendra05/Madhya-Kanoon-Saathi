"""Answer pipeline end to end, offline: fake retriever and fake LLM (W2.1)."""

import json
from datetime import date
from pathlib import Path

import pytest

from madhya_kanoon_saathi.common.contacts import load as load_contacts
from madhya_kanoon_saathi.generation.pipeline import Retrieved, answer, detect_lang

TEXTS = json.loads(Path("data/answer_texts.json").read_text(encoding="utf-8"))
REPLIES = json.loads(Path("data/safety/crisis_replies.json").read_text(encoding="utf-8"))
NUMBERS = {c.id: c.number for c in load_contacts(Path("data/contacts.yaml"))}
RTI = Retrieved(
    chunk_id="IN.RTIR2012:r3@en@2012-07-31",
    text="3. Application Fee.—An application under sub-section (1) of Section 6 of the Act shall "
    "be accompanied by a fee of rupees ten and shall ordinarily not contain more than five words",
    section_uid="IN.RTIR2012:r3",
    extraction="ocr:bodhan@cd50d301",
    pages=(2, 2),
    source_url="https://example.gov.in/rtir2012.pdf",
)
GOOD = json.dumps(
    {
        "answer_blocks": [
            {
                "text": "RTI aavedan ki fees 10 rupaye hai.",
                "citations": [
                    {"chunk_id": RTI.chunk_id, "quote": "accompanied by a fee of rupees ten"}
                ],
            }
        ],
        "abstain": False,
        "abstain_reason": None,
    }
)
BAD = GOOD.replace("accompanied by a fee of rupees ten", "the fee is ten rupees")


class FakeLLM:
    def __init__(self, *outputs: str) -> None:
        self.outputs, self.calls = list(outputs), []  # type: ignore[var-annotated]

    def __call__(self, messages):  # type: ignore[no-untyped-def]
        self.calls.append(messages)
        return self.outputs.pop(0)


def run(question: str, llm: FakeLLM, chunks=(RTI,), **kw):  # type: ignore[no-untyped-def]
    return answer(
        question,
        retrieve=lambda q: list(chunks),
        generate=llm,
        texts=TEXTS,
        crisis_replies=REPLIES,
        numbers=NUMBERS,
        today=date(2026, 11, 18),
        allow_draft=True,
        **kw,
    )


def test_language_detection() -> None:
    assert detect_lang("आरटीआई फीस कितनी है?") == "hi"
    assert detect_lang("RTI ki fees kitni hai") == "hinglish"
    assert detect_lang("What is the RTI fee?") == "en"


def test_supported_answer_is_rendered_with_quote_scan_label_and_footer() -> None:
    llm = FakeLLM(GOOD)
    r = run("RTI ki fees kitni hai, mera number 9876543210", llm)
    assert not r.abstained and len(llm.calls) == 1
    assert "“accompanied by a fee of rupees ten” [IN.RTIR2012:r3]" in r.text
    assert "scan ki gayi prati se" in r.text and "page 2" in r.text
    assert "Kanoon 2026-11-18" in r.text and NUMBERS["nalsa_15100"] in r.text
    assert "9876543210" not in r.log["question"]  # log is redacted
    assert r.log["cited"] == [RTI.chunk_id]


def test_unsupported_first_answer_is_retried_then_abstains() -> None:
    llm = FakeLLM(BAD, GOOD)
    r = run("RTI ki fees kitni hai", llm)
    assert not r.abstained and r.log["attempts"] == 2
    assert "unsupported citations" in llm.calls[1][-1]["content"]
    r2 = run("RTI ki fees kitni hai", FakeLLM(BAD, BAD))
    assert r2.abstained and "bharosemand jawab nahi mila" in r2.text


def test_invalid_json_counts_as_unsupported() -> None:
    assert run("RTI ki fees kitni hai", FakeLLM("not json", "still not json")).abstained


def test_self_harm_gets_only_the_crisis_reply() -> None:
    llm = FakeLLM()
    r = run("main aatmahatya karna chahta hoon", llm)
    assert r.abstained and r.reason == "self_harm" and not llm.calls
    assert NUMBERS["telemanas_14416"] in r.text


def test_other_state_abstains_without_calling_the_llm() -> None:
    llm = FakeLLM()
    r = run("Rajasthan mein RTI ki fees kitni hai", llm)
    assert r.abstained and r.reason == "other_state" and not llm.calls


def test_dispute_adds_procedure_only_instruction_and_referral() -> None:
    llm = FakeLLM(GOOD)
    r = run("RTI ka case jeet jaunga kya", llm)
    assert "procedure" in llm.calls[0][0]["content"]
    assert "Kaun sahi hai" in r.text


def test_wage_qualification_and_rti_r14_note() -> None:
    wage = Retrieved(
        chunk_id="MP.MWVDAOCT2026:sch_da@hi@2026-10-01",
        text="अनुसूची - द (कृषि नियोजन) अकुशल 7660 255.33 2430 81.00 10090 336.32 336",
        section_uid="MP.MWVDAOCT2026:sch_da",
        extra={"notification": "22288-337", "valid_from": "01.10.2026", "valid_to": "31.03.2027"},
    )
    r14 = Retrieved(
        chunk_id="IN.RTIR2012:r14@en@2012-07-31",
        text="14. Service of notice by Commission.—The Commission may issue the notice",
        section_uid="IN.RTIR2012:r14",
    )
    out = json.dumps(
        {
            "answer_blocks": [
                {
                    "text": "a",
                    "citations": [{"chunk_id": wage.chunk_id, "quote": "अकुशल 7660 255.33"}],
                },
                {
                    "text": "b",
                    "citations": [
                        {"chunk_id": r14.chunk_id, "quote": "Commission may issue the notice"}
                    ],
                },
            ],
            "abstain": False,
            "abstain_reason": None,
        }
    )
    r = run("What is the agriculture wage and how is notice served?", FakeLLM(out), (wage, r14))
    assert "22288-337" in r.text and "01.10.2026" in r.text
    assert "registered post" in r.text


def test_unapproved_wording_is_refused() -> None:
    if TEXTS["status"] == "approved":
        pytest.skip("wording approved")
    with pytest.raises(PermissionError):
        answer(
            "RTI fee?",
            retrieve=lambda q: [RTI],
            generate=FakeLLM(GOOD),
            texts=TEXTS,
            crisis_replies=REPLIES,
            numbers=NUMBERS,
            today=date(2026, 11, 18),
        )
