"""Wage notification schedules and the arithmetic gate (DEC-050, DEC-071 item 2, DEC-072).

Rows and headers are copied from the bulk Bodhan OCR of MP.MWVDAOCT2026@hi@1 (pp.1-4, 2026-11-17)."""

import pytest

from madhya_kanoon_saathi.common.section_uid import is_valid
from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import Unit
from madhya_kanoon_saathi.ingestion.wage_tables import (
    check_wage_rows,
    parse_wage_notification,
    schedule_uid,
    translit,
)

INST = "MP.MWVDAOCT2026"
M = "▁"
HEAD = "| श्रमिकों का वर्ग | प्रतिमाह | प्रतिदिन | प्रतिमाह | प्रतिदिन | प्रतिमाह | प्रतिदिन | |"


def ocr(*texts: str, page: int = 2) -> list[Line]:
    return [Line(page, t.replace(" ", M), "body") for t in texts]


def unit(*texts: str) -> Unit:
    return Unit(f"{INST}:sch_cha", "schedule", "", lines=ocr(*texts))


@pytest.mark.parametrize(
    ("line", "uid"),
    [
        ("अनुसूची - अ (खण्ड - ब)", "sch_a_ba"),
        ("अनुसूची –च", "sch_cha"),
        ("अनुसूची - द (कृषि नियोजन)", "sch_da"),
        ("अनुसूची -क", "sch_ka"),
        ("अनुसूची - ई (वीडी नियोजन)", "sch_ii"),
        ("अनुसूची -एफ (अगरबत्ती नियोजन)", "sch_epha"),
        ("(खण्ड-अ - अनुसूची-अ)", "sch_a_a"),
    ],
)
def test_schedule_uids(line: str, uid: str) -> None:
    head = schedule_uid(INST, line.replace(" ", M))
    assert head is not None and head[0] == f"{INST}:{uid}"
    assert is_valid(head[0])


def test_not_a_schedule_heading() -> None:
    assert schedule_uid(INST, "उपरोक्त विषयांतर्गत अनुसूचित नियोजनों की सूची में") is None


def test_translit_rejects_unknown_characters() -> None:
    assert translit("एफ") == "epha"
    with pytest.raises(ValueError, match="transliteration"):
        translit("कि")


def test_title_line_belongs_to_the_next_schedule_and_signature_is_dropped() -> None:
    p = parse_wage_notification(
        INST,
        ocr(
            "अधिसूचना",
            "अनुसूची -क",
            "| अकुशल | 9575 | 319.17 | 3000 | 100.00 | 12575 | 419.17 | 419 |",
            "बीडी नियोजन",
            "अखिल भारतीय उपभोक्ता मूल्य सूचकांक में 2573 औसत बिन्दुओं की वृद्धि हुई है।",
            "अनुसूची - ई (वीडी नियोजन)",
            "| बीडी रोलर (1000 बीडी बनाने के लिए) | 106.81 | 28.38 | 135.19 |",
            "(शीतला पटले)",
            "श्रमायुक्त,",
            "मध्य प्रदेश, इन्दौर",
        ),
    )
    assert [u.uid.split(":")[1] for u in p.units] == ["sch_ka", "sch_ii"]
    assert len(p.units[0].lines) == 2  # the beedi title moved to the next schedule
    assert len(p.units[1].lines) == 4
    assert len(p.trailing) == 3 and len(p.unassigned) == 1


def test_arithmetic_gate_passes_real_rows() -> None:
    errors, n = check_wage_rows(
        unit(
            "अनुसूची –च",
            "मासिक एवं दैनिक वेतन की दरें। (26 दिन के मान से)",
            HEAD,
            "| मजदूर | 9575 | 368.27 | 3000 | 115.38 | 12575 | 483.65 | 484 |",
            "| कटर्स | 14444 | 555.54 | 3000 | 115.38 | 17444 | 670.92 | 671 |",
            "| लिपिकीय वर्ग |  |  |  |  |  |  |  |",
        )
    )
    assert errors == [] and n == 2


def test_arithmetic_gate_30_day_basis_and_printed_sum() -> None:
    # agriculture: 10090 / 30 = 336.33 but the notification prints 255.33 + 81.00 = 336.32
    errors, n = check_wage_rows(
        unit(
            "(30 दिन के मान से) (आंकडे रुपये में)",
            "| अकुशल | 7660 | 255.33 | 2430 | 81.00 | 10090 | 336.32 | 336 |",
        )
    )
    assert errors == [] and n == 1


@pytest.mark.parametrize(
    ("row", "failure"),
    [
        # one misread digit in each column
        ("| मजदूर | 9375 | 368.27 | 3000 | 115.38 | 12575 | 483.65 | 484 |", "total (monthly)"),
        ("| मजदूर | 9575 | 386.27 | 3000 | 115.38 | 12575 | 483.65 | 484 |", "daily base"),
        ("| मजदूर | 9575 | 368.27 | 3000 | 115.38 | 12575 | 483.65 | 483 |", "rounded half up"),
        ("| मजदूर | 9575 | 368.27 | 3000 | 115.88 | 12575 | 483.65 | 484 |", "daily VDA"),
    ],
)
def test_arithmetic_gate_catches_a_misread_digit(row: str, failure: str) -> None:
    errors, _ = check_wage_rows(unit("(26 दिन के मान से)", row))
    assert any(failure in e for e in errors)


def test_four_column_piece_rate_rows() -> None:
    ok, _ = check_wage_rows(
        unit("| (ब) सुगंधित (सेंटेड) | 45.00 | 30.00 | रूपये 75.00 |")  # agarbatti, p.4
    )
    bad, _ = check_wage_rows(unit("| बीडी रोलर | 106.81 | 28.38 | 135.91 |"))
    assert ok == [] and len(bad) == 1


def test_missing_day_basis_is_an_error() -> None:
    errors, _ = check_wage_rows(
        unit("| अकुशल | 9575 | 368.27 | 3000 | 115.38 | 12575 | 483.65 | 484 |")
    )
    assert errors and "day basis" in errors[0]
