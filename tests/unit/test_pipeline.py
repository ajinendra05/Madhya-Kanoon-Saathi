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
    extra={"checked_on": "2026-11-08"},
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
    assert "official PDF ki scan prati se" in r.text and "page 2" in r.text
    assert "IN.RTIR2012 2026-11-08" in r.text  # per-source check date, not today's date
    assert "2026-11-18" not in r.text and NUMBERS["nalsa_15100"] in r.text
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
    assert "tay nahi karta ki kaun sahi hai" in r.text


WAGE = Retrieved(
    chunk_id="MP.MWVDAOCT2026:sch_da@hi@2026-10-01",
    text="अनुसूची - द (कृषि नियोजन) अकुशल 7660 255.33 2430 81.00 10090 336.32 336",
    section_uid="MP.MWVDAOCT2026:sch_da",
    extra={
        "notification_no": "1/11/अन्वे./पांच/2024/22288-337",
        "publisher": "Labour Commissioner, Madhya Pradesh, Indore",
        "valid_from": "2026-10-01",
        "valid_to": "2027-03-31",
        "checked_on": "2026-11-06",
    },
)
R14 = {
    lang: Retrieved(
        chunk_id=f"IN.RTIR2012:r14@{lang}@2012-07-31",
        text=text,
        section_uid="IN.RTIR2012:r14",
        pages=(page, page),
        source_url=f"https://example.gov.in/rtir2012_{lang}.pdf",
    )
    for lang, text, page in (
        ("en", "14. Service of notice by Commission.—The Commission may issue the notice", 3),
        ("hi", "14. आयोग द्वारा सूचना की तामील – आयोग, नाम से सूचना जारी कर सकेगा", 4),
    )
}


def one_block(chunk: Retrieved, quote: str, text: str = "a") -> str:
    blocks = [{"text": text, "citations": [{"chunk_id": chunk.chunk_id, "quote": quote}]}]
    return json.dumps({"answer_blocks": blocks, "abstain": False, "abstain_reason": None})


def test_wage_line_has_number_authority_validity_and_review_date() -> None:
    r = run(
        "What is the agriculture minimum wage?",
        FakeLLM(one_block(WAGE, "अकुशल 7660 255.33")),
        (WAGE,),
    )
    for part in (
        "22288-337",
        "Labour Commissioner, Madhya Pradesh",
        "2026-10-01",
        "2027-03-31",
        "2026-11-08",
    ):
        assert part in r.text
    bare = Retrieved(WAGE.chunk_id, WAGE.text, WAGE.section_uid)  # no notification data
    r2 = run(
        "What is the agriculture minimum wage?",
        FakeLLM(one_block(bare, "अकुशल 7660 255.33")),
        (bare,),
    )
    assert "22288-337" not in r2.text and "69(2)" not in r2.text  # never a wage line without them


@pytest.mark.parametrize(
    ("question", "marker"),
    [
        ("How is notice served by the Commission?", "Both texts"),
        ("Commission notice kaise bhejta hai?", "Dono text"),
        ("आयोग सूचना कैसे भेजता है?", "दोनों पाठ"),
    ],
)
def test_rti_r14_note_cites_both_versions(question: str, marker: str) -> None:
    out = one_block(R14["en"], "Commission may issue the notice")
    r = run(question, FakeLLM(out), (R14["en"],), versions=lambda uid: list(R14.values()))
    assert marker in r.text
    assert "rtir2012_en.pdf" in r.text and "rtir2012_hi.pdf" in r.text


def test_rti_r14_note_omitted_without_both_versions() -> None:
    out = one_block(R14["en"], "Commission may issue the notice")
    r = run("How is notice served?", FakeLLM(out), (R14["en"],), versions=lambda uid: [R14["en"]])
    assert "registered post" not in r.text
    r2 = run("How is notice served?", FakeLLM(out), (R14["en"],))  # no lookup at all
    assert "registered post" not in r2.text


def test_blocks_judging_merits_are_dropped() -> None:
    win = one_block(RTI, "accompanied by a fee of rupees ten", text="Aap case jeet jaoge.")
    r = run("RTI ka case jeet jaunga kya", FakeLLM(win))
    assert r.abstained and r.log["merits_blocks_dropped"] == 1 and "jeet jaoge" not in r.text


def test_scan_label_names_unofficial_hosts() -> None:
    other = Retrieved(**{**RTI.__dict__, "source_url": "https://prsindia.org/files/x.pdf"})
    r = run("RTI ki fees kitni hai", FakeLLM(GOOD), (other,))
    assert "srot prsindia.org" in r.text and "official PDF" not in r.text
    archived = Retrieved(
        **{
            **RTI.__dict__,
            "source_url": "https://web.archive.org/web/2026id_/https://revenue.mp.gov.in/x.pdf",
        }
    )
    r2 = run("RTI ki fees kitni hai", FakeLLM(GOOD), (archived,))
    assert "official PDF ki scan prati se" in r2.text  # DEC-049: archive copy of an official file


def test_repealed_chunks_never_reach_the_generator() -> None:
    old = Retrieved(**{**RTI.__dict__, "status": "repealed"})
    llm = FakeLLM()
    r = run("RTI ki fees kitni hai", llm, (old,))
    assert r.abstained and not llm.calls


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


def clarify_out(question: str) -> str:
    return json.dumps(
        {"answer_blocks": [], "clarify": question, "abstain": False, "abstain_reason": None}
    )


def test_valid_clarifying_question_is_asked_without_retry() -> None:
    llm = FakeLLM(
        clarify_out("Kya aapka aavedan central government ke vibhag ko hai ya MP sarkar ke?")
    )
    r = run("RTI ki fees kitni hai", llm)
    assert len(llm.calls) == 1 and not r.abstained and r.reason == "clarify"
    assert r.text.startswith("Kya aapka aavedan") and r.log["clarify"] is True


@pytest.mark.parametrize(
    "question",
    [
        "x" * 201 + "?",  # too long
        "Please tell me your department",  # not a question
        "Kya aap case jeet jaoge?",  # judges the outcome
    ],
)
def test_bad_clarifying_question_is_treated_as_unsupported(question: str) -> None:
    llm = FakeLLM(clarify_out(question), GOOD)
    r = run("RTI ki fees kitni hai", llm)
    assert len(llm.calls) == 2 and not r.abstained and r.reason is None


HELP_TOPICS = json.loads(Path("data/help_topics.json").read_text(encoding="utf-8"))


def test_topic_question_gets_topic_list_without_retrieval_or_llm() -> None:
    llm = FakeLLM()

    def no_retrieval(q):  # type: ignore[no-untyped-def]
        raise AssertionError("retrieval must not run for a topic question")

    reply = answer(
        "aap mujhe kis kis topic me help kar sakte hai",
        retrieve=no_retrieval,
        generate=llm,
        texts=TEXTS,
        crisis_replies=REPLIES,
        numbers=NUMBERS,
        today=date(2026, 11, 18),
        topics=HELP_TOPICS,
        allow_draft=True,
    )
    assert reply.reason == "help" and not reply.abstained and not llm.calls
    assert HELP_TOPICS["topics"][0]["hinglish"] in reply.text


@pytest.mark.parametrize("chunks", [(), (RTI,)])
def test_no_support_abstention_lists_topics(chunks) -> None:  # type: ignore[no-untyped-def]
    abstain = json.dumps({"answer_blocks": [], "abstain": True, "abstain_reason": "not covered"})
    reply = run(
        "What is the stamp duty on a sale deed?", FakeLLM(abstain), chunks, topics=HELP_TOPICS
    )
    assert reply.abstained
    assert TEXTS["abstain"]["no_support"]["en"] in reply.text
    assert HELP_TOPICS["abstain_intro"]["en"] in reply.text
    assert all(t["en"] in reply.text for t in HELP_TOPICS["topics"])


def test_other_state_abstention_has_no_topic_list() -> None:
    reply = run("Kerala mein rent control law kya hai?", FakeLLM(), topics=HELP_TOPICS)
    assert reply.reason == "other_state"
    assert HELP_TOPICS["abstain_intro"]["hinglish"] not in reply.text


def test_topic_question_drops_embedding_only_safety_line() -> None:
    import numpy as np

    from madhya_kanoon_saathi.generation.crisis import ExampleIndex

    idx = ExampleIndex(vectors={"cyber_fraud": np.array([[1.0, 0.0]])}, threshold=0.5)
    q = "aap mujhe kis kis topic me help kar sakte hai"
    reply = run(
        q, FakeLLM(), topics=HELP_TOPICS, query_vec=np.array([1.0, 0.0]), crisis_examples=idx
    )
    assert reply.reason == "help" and reply.log["crisis"]["tier"] == "note"
    assert reply.log["crisis_note_suppressed"]
    assert REPLIES["note"]["hinglish"].split("{")[0] not in reply.text


def test_topic_question_keeps_rule_based_crisis_reply() -> None:
    q = "pati mujhe maar raha hai, aap kis kis topic me help kar sakte ho"
    reply = run(q, FakeLLM(), topics=HELP_TOPICS)
    assert reply.reason == "help" and reply.log["crisis"]["tier"] == "full"
    assert "181" in reply.text and "112" in reply.text
