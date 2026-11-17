"""OCR page reader and OCR cleanup in canonicalise (W1.1b). Examples are shaped like the real
Bodhan bulk output (IN.RTIR2012@en@1 p.2, MP.LRCDR2018@bi@1 p.16, MP.MWVDAOCT2026@hi@1 p.2)."""

import json
from pathlib import Path

import pytest

from madhya_kanoon_saathi.ingestion.chunker import canonicalise, ocr_clean
from madhya_kanoon_saathi.ingestion.ocr_text import (
    find_pages,
    is_running_head,
    line_lang,
    load,
    model_notes,
    page_lines,
)

M = "▁"  # Bodhan's word mark
REV = "cd50d301d0e17e8ecb32fc49c8ccbd7914dcfc25"


def w(text: str) -> str:
    """Write text the way Bodhan does: word marks instead of spaces."""
    return text.replace(" ", M)


@pytest.mark.parametrize(
    "line",
    [
        "6",
        "226 (74)",
        "५.",
        "$$3$$",
        "______",
        "THE GAZETTE OF INDIA : EXTRAORDINARY",
        "[PART II—SEC. 3(i)]",
        "[ भाग II—खण्ड 3(i) ]",
        "मध्यप्रदेश राजपत्र, दिनांक 1 फरवरी 2019",
        "भाग 4 (ग) ]",
    ],
)
def test_running_heads(line: str) -> None:
    assert is_running_head(w(line))


@pytest.mark.parametrize(
    "line",
    [
        "3. Application Fee.—An application under sub-section (1) of Section 6",
        "(1) इन नियमों का संक्षिप्त नाम मध्यप्रदेश भू-राजस्व संहिता (सीमांकन) नियम,",
        "(a) rupees two for each page in A-3 or smaller size paper;",
    ],
)
def test_body_lines_are_not_heads(line: str) -> None:
    assert not is_running_head(w(line))


def test_heads_only_at_page_top_and_bare_number_at_bottom() -> None:
    md = "\n".join(
        w(x)
        for x in [
            "6",
            "",
            "THE GAZETTE OF INDIA : EXTRAORDINARY",
            "3. Application Fee.—text",
            "4. Fees.—text",
            "5. More text.—",
            "6. Further.—text",
            "7. Last rule.—text",
            "THE GAZETTE OF INDIA quoted in a rule body",
            "",
            "615",
        ]
    )
    kinds = [(ln.text.replace(M, " "), ln.kind) for ln, _ in page_lines(2, md)]
    assert kinds[0] == ("6", "header")
    assert kinds[1] == ("THE GAZETTE OF INDIA : EXTRAORDINARY", "header")
    assert ("THE GAZETTE OF INDIA quoted in a rule body", "body") in kinds  # outside the head zone
    assert kinds[-1] == ("615", "header")


def test_blank_line_marks_paragraph_start() -> None:
    lines = [ln for ln, body in page_lines(1, "(1) first\n\n(2) second\nwrapped") if body]
    assert [ln.para_start for ln in lines] == [False, True, False]


def test_line_language() -> None:
    assert line_lang(w("(क) ए-3 और उससे छोटे आकार के कागज"), "en") == "hi"
    assert line_lang(w("(a) rupees two for each page"), "hi") == "en"
    assert line_lang("(1)", "hi") == "hi"  # no letters: keeps the previous language
    assert line_lang("<table>", "hi") == "hi"  # markup is not English (LRCDR forms)
    assert line_lang(w("<td>धारकों का नाम</td>"), "en") == "hi"


def test_model_notes_are_flagged() -> None:
    lines = [
        ln
        for ln, body in page_lines(
            1, w("The image contains a symbol of a flower\nश्रमायुक्त कार्यालय\nScanned with X")
        )
        if body
    ]
    assert len(model_notes(lines)) == 2


def _part(root: Path, pkg: str, folder: str, pages: dict[int, str], *, wrapped: bool) -> None:
    out = (root / f"{pkg}_out" / pkg / "out") if wrapped else (root / pkg / "out")
    (out / folder).mkdir(parents=True)
    (out / "run_info.json").write_text(json.dumps({"bodhan": {"revision": REV}, "dpi": 300}))
    for n, text in pages.items():
        (out / folder / f"p{n:04d}.md").write_text(text, encoding="utf-8")


def test_load_merges_parts_and_splits_languages(tmp_path: Path) -> None:
    folder = "IN.X2020_bi_1"
    _part(tmp_path, "mks_ocr_bulk_p1", folder, {1: w("1. नियम –\n(1) पाठ")}, wrapped=True)
    _part(tmp_path, "mks_ocr_bulk_p2", folder, {2: w("2\n\n1. Rule.—\n(1) text")}, wrapped=False)
    doc = load(tmp_path, "IN.X2020@bi@1", 2, "hi")
    assert doc.engine == "ocr:bodhan@cd50d301"
    assert [ln.text for ln in doc.lines["hi"]] == [w("1. नियम –"), w("(1) पाठ")]
    assert [ln.text for ln in doc.lines["en"]] == [w("1. Rule.—"), w("(1) text")]
    assert [ln.page for ln in doc.lines["en"]] == [2, 2]


def test_load_fails_on_missing_page(tmp_path: Path) -> None:
    _part(tmp_path, "p1", "IN.X2020_en_1", {1: "a"}, wrapped=False)
    with pytest.raises(ValueError, match="missing"):
        load(tmp_path, "IN.X2020@en@1", 2, "en")


def test_conflicting_duplicate_page_fails(tmp_path: Path) -> None:
    _part(tmp_path, "p1", "IN.X2020_en_1", {1: "a"}, wrapped=False)
    _part(tmp_path, "p2", "IN.X2020_en_1", {1: "b"}, wrapped=False)
    with pytest.raises(ValueError, match="two different"):
        find_pages(tmp_path, "IN.X2020@en@1")


def test_ocr_clean_word_marks_tables_and_leaders() -> None:
    assert ocr_clean(w("(a) rupees two")) == "(a) rupees two"
    cleaned = ocr_clean("<tr>\n<td>1.</td>\n<td></td>\n</tr>")
    assert cleaned.split() == ["1."]
    assert ocr_clean("| --- | --- |").strip() == ""
    assert ocr_clean("| मजदूर | | | 9575 |") == "| मजदूर | 9575 |"
    assert ocr_clean("Application No.................of 20......") == ("Application No … of 20 … ")


def test_table_rows_stay_on_separate_lines() -> None:
    from madhya_kanoon_saathi.ingestion.chunker import _assemble
    from madhya_kanoon_saathi.ingestion.structure import Unit

    md = "अनुसूची –च\n| वर्ग | वेतन |\n| --- | --- |\n| मजदूर | 9575 |\n<tr>\n<td>1.</td>\n</tr>"
    lines = [ln for ln, body in page_lines(1, w(md)) if body]
    raw, rmap, _ = _assemble([Unit("IN.X2020:sch1", "schedule", "", lines=lines)], ocr=True)
    assert canonicalise(raw, rmap).split("\n") == [
        "अनुसूची –च",
        "| वर्ग | वेतन |",
        "| मजदूर | 9575 |",
        "1.",
    ]


def test_canonicalise_applies_ocr_clean_only_when_flagged() -> None:
    raw = w("Date ........ Inspector")
    assert canonicalise(raw, {"breaks": [], "ocr": [1]}) == "Date … Inspector"
    assert canonicalise(raw, {"breaks": []}) == raw  # born-digital path unchanged
