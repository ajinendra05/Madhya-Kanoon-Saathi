"""Bill layout (IN.MTA2021@en@1, MoHUA Model Tenancy Act PDF; lines as extracted by pypdfium2, 2026-11-11)."""

from madhya_kanoon_saathi.ingestion.bill_layout import split_margin, toc_headings
from madhya_kanoon_saathi.ingestion.chunker import canonicalise
from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import parse_statute

CONTENTS = [
    Line(1, "ARRANGEMENT OF CLAUSES", "body"),
    Line(1, "CHAPTER I", "body"),
    Line(1, "PRELIMINARY", "body"),
    Line(1, "Clauses ", "body"),
    Line(1, "1. Short title, extent and commencement.", "body"),
    Line(1, "2. Definitions.", "body"),
    Line(
        3, "39.Officers and other employees of Rent Authority, Rent Court and Rent ", "body"
    ),  # p.3 wraps
    Line(3, "Tribunal.", "body"),
    Line(3, "47.Repeal and savings.", "body"),
    Line(3, "First Schedule", "body"),
]


def test_contents_headings_with_wrap_and_schedule_cut() -> None:
    h = toc_headings(
        [
            *CONTENTS,
            Line(4, "BE it enacted by the (State/Union territory Legislature) in the", "body"),
        ]
    )
    assert h["1"] == "Short title, extent and commencement"
    assert h["39"] == "Officers and other employees of Rent Authority, Rent Court and Rent Tribunal"
    assert h["47"] == "Repeal and savings"


def test_margin_text_is_skipped_in_canonical_text() -> None:
    # p.4: "2. In this Act, unless the context otherwise requires,–– Definitions." with "Definitions." at 10 pt
    line2 = "2. In this Act, unless the context otherwise requires,–– Definitions. "
    a = line2.index("Definitions.")
    body = [
        *CONTENTS,
        Line(4, "BE it enacted by the (State/Union territory Legislature) in the", "body"),
        Line(4, "1. (1) This Act may be called the (Name of State/Union territory) ", "body"),
        Line(4, "Short title, extent", "footnote", small=((0, 19),)),
        Line(4, line2, "body", small=((a, a + 12),)),
        Line(4, "41 of ", "body", small=((0, 5),)),
        Line(4, "(a) “landlord”, whether called landowner or lessor", "body"),
    ]
    split = split_margin(body)
    assert split.headings["2"] == "Definitions"
    assert "41 of" in split.citations
    parsed = parse_statute("IN.MTA2021", split.lines, margin_headings=True)
    assert [u.uid for u in parsed.units if u.kind == "section"] == [
        "IN.MTA2021:s1",
        "IN.MTA2021:s2",
    ]
    s2 = next(ln for ln in split.lines if ln.text == line2)
    assert s2.skips == ((a, a + 12),)
    rmap = {"markers": [], "breaks": [], "skips": [list(s2.skips[0])]}
    assert canonicalise(s2.text, rmap) == "2. In this Act, unless the context otherwise requires,––"
