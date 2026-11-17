"""Hindi rules parsing and alignment with the English structure (W1.1b; section_uid rule 2).

Lines are shortened from the bulk Bodhan OCR of IN.RTIR2012@hi@1, IN.CPJR2021@bi@1,
IN.CPECR2020@bi@1 and MP.LRCDR2018@bi@1 (2026-11-17)."""

from madhya_kanoon_saathi.common.section_uid import is_valid
from madhya_kanoon_saathi.ingestion.hindi_rules import align, item_system, parse_hindi_rules
from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import parse_statute

INST = "IN.X2012"
M = "▁"


def ocr(*texts: str) -> list[Line]:
    return [Line(2, t.replace(" ", M), "body") for t in texts]


def aligned(hindi: list[str], english: list[str]) -> tuple[list[str], list[str]]:
    en = parse_statute(INST, ocr(*english), rules=True)
    parsed, report = align(INST, parse_hindi_rules(ocr(*hindi)), en)
    assert all(is_valid(u.uid) for u in parsed.units)
    return [u.uid.split(":", 1)[1] for u in parsed.units], report


def test_item_systems() -> None:
    assert item_system("क") == ("hl", 0)
    assert item_system("ङ") == ("hl", 4)
    assert item_system("तीन") == ("hw", 2)
    assert item_system("iv") == ("rom", 3)
    assert item_system("1") is None


def test_rules_clauses_and_proviso_align_by_position() -> None:
    # IN.RTIR2012@hi@1 pp.1-2 against the English rules
    hindi = [
        "1. संक्षिप्त नाम और प्रारंभ – (1) इन नियमों का संक्षिप्त नाम सूचना का अधिकार नियम, 2012 है ।",
        "(2) ये राजपत्र में उनके प्रकाशन की तारीख को प्रवृत्त होंगे ।",
        "2. परिभाषाएं – इन नियमों में, जब तक कि संदर्भ से अन्यथा अपेक्षित न हो,–",
        "(क) “अधिनियम” से सूचना का अधिकार अधिनियम, 2005 अभिप्रेत है ;",
        "(ख) “आयोग” से केंद्रीय सूचना आयोग अभिप्रेत है ;",
        "3. आवेदन फीस – अधिनियम की धारा 6 की उपधारा (1) के अधीन आवेदन के साथ दस रुपए की फीस",
        "परंतु किसी भी आवेदन को केवल इस आधार पर नामंजूर नहीं किया जाएगा",
    ]
    english = [
        "1. Short title and commencement.—(1) These rules may be called the RTI Rules, 2012.",
        "(2) They shall come into force on the date of their publication.",
        "2. Definitions.—In these rules, unless the context otherwise requires,—",
        "(a) “Act” means the Right to Information Act, 2005;",
        "(b) “Commission” means the Central Information Commission;",
        "3. Application Fee.—An application under sub-section (1) of Section 6 shall be",
        "Provided that no application shall be rejected only on the ground that",
    ]
    uids, report = aligned(hindi, english)
    assert uids == ["r1", "r1:ss1", "r1:ss2", "r2", "r2:cl_a", "r2:cl_b", "r3", "r3:prov1"]
    assert report == []


def test_count_mismatch_keeps_the_hindi_rule_whole() -> None:
    # IN.RTIR2012 r.14: the official Hindi lists 3 modes of service, the English 4
    # (no "registered post"); position-matching would give "email" the uid of "registered post"
    hindi = [
        "1. आयोग द्वारा सूचना की तामील – आयोग, नाम से सूचना जारी कर सकेगा, अर्थात् :–",
        "(i) स्वयं पक्षकार द्वारा तामील करके ;",
        "(ii) आदेशिका तामीलकर्ता के माध्यम से दस्ती परिदान द्वारा ;",
        "(iii) इलैक्ट्रानिक पता उपलब्ध होने की दशा में इलैक्ट्रानिक मेल द्वारा ।",
    ]
    english = [
        "1. Service of notice by Commission.—The Commission may issue the notice through:",
        "(i) service by the party itself;",
        "(ii) by hand delivery (dasti) through Process Server;",
        "(iii) by registered post with acknowledgement due;",
        "(iv) by electronic mail in case electronic address is available.",
    ]
    uids, report = aligned(hindi, english)
    assert uids == ["r1"]
    assert len(report) == 1 and "kept whole" in report[0]


def test_proviso_word_and_wrapped_cross_reference() -> None:
    # "परंतुक" (a proviso, noun) is not a proviso start; "(i) के ..." is a wrapped reference
    # (IN.CPJR2021@bi@1 p.2)
    hp = parse_hindi_rules(
        ocr(
            "1. राज्य आयोग की अधिकारिता – धारा 47 की उप-धारा (1) के खंड (क) के उप-खंड",
            "(i) के परंतुक के अनुसरण में, राज्य आयोग की अधिकारिता होगी।",
            "परंतुक के अधीन कोई बात",
        )
    )
    assert [c.kind for c in hp.roots[0].children] == []


def test_clauses_continue_after_a_proviso() -> None:
    # IN.CPECR2020 r.5(3): (क), proviso, then (ख) (ग)
    hp = parse_hindi_rules(
        ocr(
            "1. दायित्व — (1) प्रत्येक इकाई निम्नलिखित जानकारी देगी :",
            "(क) विक्रेताओं के ब्यौरे;",
            "परंतु कोई इकाई अनुरोध पर जानकारी देगी;",
            "(ख) एक टिकट नम्बर;",
            "(ग) उत्पाद वापसी संबंधी जानकारी;",
        )
    )
    ss1 = hp.roots[0].children[0]
    assert [c.kind for c in ss1.children] == ["item", "item", "item"]
    assert [c.kind for c in ss1.children[0].children] == ["prov"]  # proviso to clause (क)


def test_heading_dashes_and_rules_without_heading() -> None:
    # "-- (1)" (IN.CPECR2020 r.2); no heading (MP.LRCDR2018 r.3, r.4)
    hp = parse_hindi_rules(
        ocr(
            "1. विस्तार और लागू होना -- (1) ये नियम लागू होंगे",
            "2. सीमांकन तथा सीमा चिन्हों को संनिर्मित करने के लिए आवेदन प्ररूप एक में किया जाएगा।",
            "3. (1) आवेदक ऐसी फीस का भुगतान करेगा",
        )
    )
    assert [(r.num, r.heading) for r in hp.roots] == [
        (1, "विस्तार और लागू होना"),
        (2, ""),
        (3, ""),
    ]
    assert [c.kind for c in hp.roots[0].children] == ["ss"]
    assert [c.kind for c in hp.roots[2].children] == ["ss"]


def test_forms_schedule_and_signature() -> None:
    # MP.LRCDR2018@bi@1: schedule and forms align by order; the signature block is not text
    hindi = [
        "1. संक्षिप्त नाम – ये नियम सीमांकन नियम कहलाएंगे।",
        "अनुसूची—एक",
        "1. प्रापर्टी पिनें लगाई जा सकेंगी।",
        "प्ररूप-एक",
        "सीमांकन के लिए आवेदन",
        "मध्यप्रदेश के राज्यपाल के नाम से तथा आदेशानुसार,",
        "प्ररूप-दो",
        "सीमांकन रिपोर्ट",
    ]
    english = [
        "1. Short title.- These rules may be called the Demarcation Rules.",
        "SCHEDULE-I",
        "1. Property pins may be installed.",
        "FORM-I",
        "Application for demarcation",
        "FORM-II",
        "Demarcation report",
    ]
    uids, report = aligned(hindi, english)
    assert uids == ["r1", "sch1", "form_i", "form_ii"]
    assert report == []
