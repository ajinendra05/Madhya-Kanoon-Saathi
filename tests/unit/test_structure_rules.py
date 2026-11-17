"""Rules-gazette parsing (``parse_statute(rules=True)``, W1.1b) on lines shaped like the bulk Bodhan OCR
of the real gazettes: IN.RTIR2012@en@1, IN.CPECR2020@bi@1, IN.CPECRA2021@bi@1, MP.WCR2026@en@1.
OCR lines carry U+2581 word marks instead of spaces."""

from madhya_kanoon_saathi.common.section_uid import is_valid
from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import parse_statute, visible_text

M = "▁"


def ocr(*texts: str) -> list[Line]:
    return [Line(2, t.replace(" ", M), "body") for t in texts]


def parse(*texts: str):  # type: ignore[no-untyped-def]
    parsed = parse_statute("IN.X2020", ocr(*texts), rules=True)
    assert all(is_valid(u.uid) for u in parsed.units)
    return parsed


def short(parsed) -> list[str]:  # type: ignore[no-untyped-def]
    return [u.uid.split(":", 1)[1] for u in parsed.units]


def test_word_marks_are_spaces_for_matching() -> None:
    assert visible_text(ocr("3. Application Fee.—text")[0]) == "3. Application Fee.—text"


def test_rules_use_r_and_sub_rules() -> None:
    # IN.RTIR2012@en@1 p.1-2
    p = parse(
        "the Central Government hereby makes the following rules, namely:—",
        "1. Short title and commencement.—(1) These rules may be called the RTI Rules, 2012.",
        "(2) They shall come into force on the date of their publication.",
        "3. Application Fee.—An application under sub-section (1) of Section 6 shall be",
        "Provided that no application shall be rejected only on the ground that",
    )
    assert short(p) == ["r1", "r1:ss1", "r1:ss2", "r3", "r3:prov1"]
    assert p.units[0].heading == "Short title and commencement"
    assert len(p.unassigned) == 1  # the preamble


def test_heading_endings_in_rules() -> None:
    # ".-" (MP.WCR2026 p.2), ". ---" and ": -" (IN.CPECR2020 pp.8, 11)
    p = parse(
        "1. Short title and extent.-",
        "(1) These rules may be called the MP Code on Wages Rules, 2026.",
        "4. Duties of e-commerce entities. ---",
        "(1) An e-commerce entity shall:",
        "7. Duties and liabilities of inventory e-commerce entities: -",
        "(1) Every inventory e-commerce entity shall provide",
    )
    assert short(p) == ["r1", "r1:ss1", "r4", "r4:ss1", "r7", "r7:ss1"]
    assert [u.heading for u in p.units if u.kind == "section"] == [
        "Short title and extent",
        "Duties of e-commerce entities",
        "Duties and liabilities of inventory e-commerce entities",
    ]


def test_amending_rule_without_heading() -> None:
    # IN.CPECRA2021@bi@1 p.2: "1. (1) These rules may be called ..."
    p = parse(
        "1. (1) These rules may be called the Consumer Protection Rules, 2021.", "2. In rule 4"
    )
    assert short(p) == ["r1", "r1:ss1", "r2"]
    assert p.units[0].heading == ""


def test_signature_block_and_printer_line_are_not_rule_text() -> None:
    # IN.CPJR2021@bi@1 p.2, renumbered from rule 5 (the "[" of "[F. No." is stripped before matching)
    p = parse(
        "1. Jurisdiction of National Commission.—Subject to the other provisions",
        "exceeds two crore rupees.",
        "[F. No. J-9/1/2020-CPU]",
        "ANUPAM MISHRA, Jt. Secy.",
        "Uploaded by Dte. of Printing at Government of India Press, Ring Road",
    )
    assert len(p.units[0].lines) == 2
    assert len(p.trailing) == 3


def test_appendix_after_signature_is_a_form() -> None:
    # IN.RTIR2012@en@1 pp.3-4 (rule 15 renumbered 1): appeal format after the signature
    p = parse(
        "1. Order of the Commission.—The order of the Commission shall be in writing",
        "[F. No. 1/35/2009-IR]",
        "MANOJ JOSHI, Jt. Secy.",
        "APPENDIX",
        "FORMAT OF APPEAL",
        "1. Name and address of the appellant",
        "Printed by the Manager, Government of India Press",
    )
    assert short(p) == ["r1", "form_appendix"]
    assert len(p.units[1].lines) == 3
    assert p.units[1].para_restart  # forms are chunked by size, never by their numbered items


def test_form_headings_vs_cross_references() -> None:
    # MP.WCR2026@en@1 pp.17, 30, 47-48 (rule 18 renumbered 1): references ending a sentence are not headings
    p = parse(
        "1. Form of Register, etc.- Every employer shall maintain a register in",
        "Form-I appended to these rules, electronically or otherwise.",
        "Form-IX.",
        "FORM-1",
        "Form-II [See rule 49]",
        "Form - IX",
    )
    assert short(p) == ["r1", "form_i", "form_ii", "form_ix"]  # "FORM-1" read as Form-I
    assert len(p.units[0].lines) == 3


def test_bare_schedule_in_rules() -> None:
    # MP.WCR2026@en@1 p.33 (rule 50 renumbered 1): "SCHEDULE*"; parts restart numbering
    p = parse(
        "1. Annual Return.- The return under these rules shall be filed",
        "SCHEDULE*",
        "[see sub-rule (3) of rule 4]",
        "Part-A",
        "1. Calf boy",
        "2. Cattleman",
        "Part-B",
        "1. Assistant Cook",
    )
    assert short(p)[:2] == ["r1", "sch1"]
    assert [u for u in short(p) if u.startswith("r")] == ["r1"]


def test_statute_mode_unchanged_for_bare_schedule_and_forms() -> None:
    lines = [Line(5, "[15th June, 2005.]", "body"), Line(5, "1. Short title.—text", "body")]
    lines += [Line(5, "SCHEDULE*", "body"), Line(5, "FORM-1", "body")]
    p = parse_statute("IN.X2020", lines)
    assert [u.uid.split(":", 1)[1] for u in p.units] == ["s1"]
