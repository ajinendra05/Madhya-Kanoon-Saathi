"""Decimal-numbered guidelines (DEC-057). Lines from IN.SVANSG2025@en@1 / IN.SVANLOG2025@en@1 (pypdfium2, 2026-11-11)."""

from madhya_kanoon_saathi.common.section_uid import is_valid
from madhya_kanoon_saathi.ingestion.guideline import _is_next, parse_guideline
from madhya_kanoon_saathi.ingestion.pdf_text import Line


def L(*texts: str) -> list[Line]:
    return [Line(4, t, "body") for t in texts]


def test_is_next_hierarchy() -> None:
    assert _is_next((), (1,))
    assert _is_next((5,), (5, 1)) and _is_next((5, 1), (5, 1, 1)) and _is_next((5, 1, 3), (5, 2))
    assert _is_next((5, 7), (6,)) and _is_next((5, 1, 3), (6,))
    assert not _is_next((5,), (5, 2)) and not _is_next((5, 1), (7,)) and not _is_next((), (2,))


def test_svansg_headings_items_and_annexure() -> None:
    parsed = parse_guideline(
        "IN.SVANSG2025",
        L(
            "5.1.1. Rate of Interest...............................................",  # contents page
            "1. Background",
            "2. Objective",
            "a) Recognition of Street Vendors;",
            "b) Financial Inclusion via working capital term loan in three tranches;",
            "3. Scheme Coverage",
            "4. Eligibility Criteria of Beneficiaries",
            "5. Scheme Components ",
            "5.1.Working Capital Term Loans",  # no space after the number (p.4)
            "1. 1",  # table cell: not a heading
            "st tranche loan of up to ₹15,000 to be repaid in 12 months, ",
            "5.1.1. Rate of Interest",
            "a) In case of Scheduled Commercial Banks, Cooperative Banks & SHG Banks, the rates ",
            "5.2. Credit card",
            "5.3 Digital Adoption",
            "5.4 'SVANidhi se Samriddhi' (SSS)",  # title starts with a quote mark
            "6. Stakeholders ",
            "provided at Annexure-E).",  # a reference, not an annexure heading
            "Annexure A",
            "1. Criteria for Identifying Eligible Street Vendors:",
            "2. Process for Approval of Letter of Recommendation (LoR):",
        ),
    )
    uids = [u.uid.split(":", 1)[1] for u in parsed.units]
    assert all(is_valid(u.uid) for u in parsed.units)
    assert "para2:cl_a" in uids and "para2:cl_b" in uids
    assert "para5:sp1" in uids and "para5:sp1:sp1" in uids and "para5:sp1:sp1:cl_a" in uids
    assert "para5:sp4" in uids and "para6" in uids
    assert uids[-3:] == ["sch1", "sch1:para1", "sch1:para2"]
    assert len(parsed.unassigned) == 1  # the contents line
    headings = {u.label: u.heading for u in parsed.units}
    assert (
        headings["5.1"] == "Working Capital Term Loans"
        and headings["5.4"] == "'SVANidhi se Samriddhi' (SSS)"
    )


def test_annexure_table_rows_are_not_body_headings() -> None:
    # IN.SVANLOG2025@en@1 p.11: Annexure 1 is a table; rows "11 Monitoring/ End Use" are not heading 11
    parsed = parse_guideline(
        "IN.SVANLOG2025",
        L(
            "1. Background and Rationale",
            "Annexure 1",
            "1 Loan Amount",
            "2",  # empty cell
            "3 Moratorium As per LI policy, within the specified repayment period",
        ),
    )
    assert [u.uid.split(":", 1)[1] for u in parsed.units] == [
        "para1",
        "sch1",
        "sch1:para1",
        "sch1:para2",
        "sch1:para3",
    ]
