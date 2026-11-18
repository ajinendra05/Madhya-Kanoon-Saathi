"""Citation validator (generation rules, DEC-054). Context texts are real chunk wording:
IN.RTIR2012:r3 (OCR, English) and MP.LRCDR2018:r4:ss1 (OCR, Hindi)."""

from madhya_kanoon_saathi.generation.validator import decide, validate

RTI = "IN.RTIR2012:r3@en@2012-07-31"
LRC = "MP.LRCDR2018:r4:ss1@hi@2019-02-01"
CONTEXT = {
    RTI: "3. Application Fee.—An application under sub-section (1) of Section 6 of the Act shall "
    "be accompanied by a fee of rupees ten and shall ordinarily not contain more than five "
    "hundred words",
    LRC: "4. (1) आवेदक क्रमशः सीमांकन तथा सीमा चिन्हों को संनिर्मित करने के लिए ऐसी फीस का भुगतान "
    "करेगा जो कि कलक्टर द्वारा आयुक्त, भू-अभिलेख के अनुमोदन से समय-समय पर, विनिश्चित की जाए।",
}


def answer(*blocks: dict) -> dict:  # type: ignore[type-arg]
    return {"answer_blocks": list(blocks), "abstain": False, "abstain_reason": None}


def block(text: str, *cits: tuple[str, str]) -> dict:  # type: ignore[type-arg]
    return {"text": text, "citations": [{"chunk_id": c, "quote": q} for c, q in cits]}


def test_exact_quotes_pass() -> None:
    v = validate(
        answer(
            block("RTI fee is Rs 10.", (RTI, "accompanied by a fee of rupees ten")),
            block("फीस कलक्टर तय करता है।", (LRC, "कलक्टर द्वारा आयुक्त, भू-अभिलेख के अनुमोदन से")),
        ),
        CONTEXT,
    )
    assert v.all_supported and len(v.supported) == 2


def test_whitespace_and_nukta_differences_do_not_fail_a_true_quote() -> None:
    v = validate(answer(block("x", (RTI, "accompanied  by a\nfee of rupees ten"))), CONTEXT)
    assert v.all_supported


def test_paraphrase_unknown_chunk_short_quote_and_missing_citation_fail() -> None:
    v = validate(
        answer(
            block("a", (RTI, "the fee is ten rupees")),  # paraphrase
            block("b", ("IN.RTI2005:s6@en@2005-06-15", "accompanied by a fee")),  # not retrieved
            block("c", (RTI, "rupees ten")),  # too short
            {"text": "d", "citations": []},  # no citation
        ),
        CONTEXT,
    )
    assert not v.supported and len(v.dropped) == 4
    reasons = " | ".join(r for _, r in v.dropped)
    for part in (
        "not found verbatim",
        "not in retrieved context",
        "shorter than",
        "without citation",
    ):
        assert part in reasons


def test_one_bad_citation_drops_its_whole_block() -> None:
    v = validate(
        answer(block("x", (RTI, "accompanied by a fee of rupees ten"), (RTI, "fee is twenty"))),
        CONTEXT,
    )
    assert not v.supported and len(v.dropped) == 1


def test_abstention_needs_no_citations_and_bad_contract_is_an_error() -> None:
    assert validate({"answer_blocks": [], "abstain": True}, CONTEXT).errors == []
    assert validate({"answer_blocks": [], "abstain": False}, CONTEXT).errors
    assert validate("not json", CONTEXT).errors


def test_policy_retry_then_strip_then_abstain() -> None:
    good = validate(answer(block("ok", (RTI, "accompanied by a fee of rupees ten"))), CONTEXT)
    bad = validate(answer(block("bad", (RTI, "the fee is ten rupees"))), CONTEXT)
    mixed = validate(
        answer(
            block("ok", (RTI, "accompanied by a fee of rupees ten")),
            block("bad", (RTI, "fee is ten rupees only")),
        ),
        CONTEXT,
    )
    assert decide(good).attempts == 1 and not decide(good).abstain
    d = decide(bad, mixed)  # retry keeps only the supported block
    assert d.attempts == 2 and [b["text"] for b in d.blocks] == ["ok"]
    assert decide(bad, bad).abstain
