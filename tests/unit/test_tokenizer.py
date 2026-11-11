"""Tokeniser rules (DEC-026), each with a real example and its source.

Sources: Bodhan OCR from the W0.5 run (2026-11-10) in data/ocr/out/bodhan/: p02.md = MP.SSS2026@bi@1 p.12,
p03.md = MP.LRCDR2018@bi@1 p.3, p04.md = MP.LRCDR2018@bi@1 p.5, p05.md = MP.LRCMR2018@hi@2 p.5; and chunks
IN.OSHC2020:sch2, IN.RTI2005:s8:ss1, IN.SVANSG2025:para1 (p.2) in data/parsed (2026-11-11).
The bare-reference rule is query-side (users type "8(1)(j)"); its example is a query shape.
"""

from madhya_kanoon_saathi.retrieval.tokenizer import KEYWORD, prepare, provision_tokens, tokenize


def test_devanagari_digits_and_hindi_keyword() -> None:
    # MP.SSS2026 p.12 (Bodhan OCR): "धारा ३३(१)"
    assert tokenize("धारा ३३(१)") == [KEYWORD, "s33", "s33_1"]


def test_english_reference_with_clause_letters() -> None:
    # IN.OSHC2020 Second Schedule: "section 18(2)(f)"
    assert tokenize("section 18(2)(f)") == [KEYWORD, "s18", "s18_2", "s18_2_f"]


def test_keyword_variants_map_to_one_token() -> None:
    for q in ("s. 8(1)(j)", "sec 8(1)(j)", "Section 8 (1) (j)", "dhara 8(1)(j)", "धारा 8(1)(j)"):
        assert tokenize(q) == [KEYWORD, "s8", "s8_1", "s8_1_j"], q


def test_bare_reference_and_plain_keyword() -> None:
    # Hinglish user query shape
    assert tokenize("8(1)(j) kya hai") == ["s8", "s8_1", "s8_1_j", "kya", "hai"]
    # MP.LRCDR2018 p.3 (Bodhan OCR): "धारा 129" has no bracket -> keyword + base only
    assert tokenize("धारा 129 के अधीन") == [KEYWORD, "s129", "अधीन"]


def test_hindi_clause_letter_is_not_latinised() -> None:
    assert tokenize("धारा 8(1)(ज)") == [KEYWORD, "s8", "s8_1", "s8_1_ज"]


def test_nukta_folded_and_lowercase() -> None:
    # MP.LRCDR2018 p.5 (Bodhan OCR): "सीमा चिन्हों की दृश्यता को बढ़ाने"
    assert tokenize("सीमा चिन्हों की दृश्यता को बढ़ाने") == tokenize("सीमा चिन्हों की दृश्यता को बढाने")
    # IN.SVANSG2025 p.2: "As per Section 2(1)(l)"
    assert prepare("As per Section 2(1)(l)") == "as per section 2(1)(l)"
    assert tokenize("As per Section 2(1)(l)") == ["per", KEYWORD, "s2", "s2_1", "s2_1_l"]


def test_stopwords_removed_but_legal_negations_kept() -> None:
    # IN.RTI2005 s.8(1): "there shall be no obligation to give any citizen"
    assert tokenize("there shall be no obligation to give any citizen") == [
        "there",
        "shall",
        "no",
        "obligation",
        "give",
        "citizen",
    ]
    # MP.LRCDR2018 p.3 (Bodhan OCR): "कलक्टर द्वारा फीस नियत नहीं की जाती"
    assert tokenize("कलक्टर द्वारा फीस नियत नहीं की जाती") == ["कलक्टर", "फीस", "नियत", "नहीं", "जाती"]


def test_danda_and_punctuation_split_words() -> None:
    # MP.LRCMR2018 p.5 (Bodhan OCR): "... तहसीलदार को भेजी जाएगी। रजिस..."
    assert tokenize("तहसीलदार को भेजी जाएगी।रजिस्ट्रीकरण") == [
        "तहसीलदार",
        "भेजी",
        "जाएगी",
        "रजिस्ट्रीकरण",
    ]


def test_provision_tokens_match_citation_tokens() -> None:
    assert provision_tokens("IN.RTI2005:s8:ss1:cl_j") == ["s8", "s8_1", "s8_1_j"]
    assert provision_tokens("IN.RTI2005:s8:ss1:cl_i:prov1") == ["s8", "s8_1", "s8_1_i"]
    assert provision_tokens("IN.SVANSG2025:para5:sp1:sp1") == ["para5", "para5_1", "para5_1_1"]
    assert provision_tokens("IN.RTI2005") == []
    # the query side produces the same tokens for the same provision
    assert set(provision_tokens("IN.RTI2005:s8:ss1:cl_j")) <= set(tokenize("section 8(1)(j)"))
