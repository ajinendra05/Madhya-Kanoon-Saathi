"""Line classification on real snippets.

Main source: IN.RTI2005@en@1 (India Code PDF, 'As on the 18th November, 2025'). Font sizes as
reported by pypdfium2 on 2026-11-10: body 11 pt, footnotes 9 pt, superscript markers 7 pt.
"""

from madhya_kanoon_saathi.ingestion.pdf_text import body_size, classify_line, lines_from_pages


def chars(
    text: str, size: float = 11.0, small: dict[int, float] | None = None
) -> list[tuple[str, float]]:
    small = small or {}
    return [(c, small.get(i, size if c not in "\r\n " else 1.0)) for i, c in enumerate(text)]


def test_body_size_is_mode() -> None:
    assert body_size([11.0] * 50 + [9.0] * 10 + [7.0] * 2) == 11.0


def test_marker_inside_body_line() -> None:
    # p.5: "(2) It extends to the whole of India 1***." -- the "1" is a 7 pt superscript
    line = "(2) It extends to the whole of India 1***."
    kind, markers = classify_line(chars(line, small={line.index("1"): 7.0}), 11.0)
    assert kind == "body"
    assert markers == ((line.index("1"), line.index("1") + 1),)


def test_marker_only_line_is_body_with_marker() -> None:
    # p.11: the marker "1" sits on its own line before
    # "[(j) information which relates to personal information;]"
    kind, markers = classify_line([("1", 7.0)], 11.0)
    assert kind == "body" and markers == ((0, 1),)


def test_footnote_line_by_size() -> None:
    # p.11 bottom: "1. Subs. by Act 22 of 2023, s. 44 for clause (j) (w.e.f. 13-11-2025)." at 9 pt
    kind, _ = classify_line(
        chars("1. Subs. by Act 22 of 2023, s. 44 for clause (j) (w.e.f. 13-11-2025).", 9.0), 11.0
    )
    assert kind == "footnote"


def test_section_heading_is_body_not_footnote() -> None:
    # p.11: "11. Third party information.--(1) Where ..." looks like a footnote start but is 11 pt
    kind, _ = classify_line(
        chars("11. Third party information.—(1) Where a Central Public Information"), 11.0
    )
    assert kind == "body"


def test_small_caps_title_mid_page_is_body() -> None:
    # IN.COW2019@en@1: chapter title "MINIMUM WAGES" is set smaller than body text,
    # but body text follows it on the page
    body_line = (
        "5. Payment of minimum rate of wages.—No employer shall pay to any employee wages less"
    )
    page = chars("CHAPTER II\r\n") + chars("MINIMUM WAGES\r\n", 9.0) + chars(body_line * 3)
    kinds = [ln.kind for ln in lines_from_pages([page]).lines]
    assert kinds == ["body", "body", "body"]


def test_page_n_of_m_footer_is_header() -> None:
    # IN.MTA2021@en@1 carries "Page 4 of 28" on every page
    page = chars(
        "1. Short title, extent and commencement.—(1) This Act may be called\r\n" * 3
    ) + chars("Page 4 of 28", 9.0)
    assert lines_from_pages([page]).lines[-1].kind == "header"


def test_page_header_footnotes_and_continuation() -> None:
    page = (
        chars("11\r\n")
        + chars("(j) information which relates to personal information;\r\n")
        + chars(
            "(2) Notwithstanding anything in the Official Secrets Act, 1923 (19 of 1923) "
            "nor any of the\r\n"
        )
        + chars("1. Subs. by Act 22 of 2023, s. 44 for clause (j)\r\n", 9.0)
        + chars("(w.e.f. 13-11-2025).", 9.0)
    )
    doc = lines_from_pages([page])
    assert [ln.kind for ln in doc.lines] == ["header", "body", "body", "footnote", "footnote"]
    assert len(doc.footnotes) == 1
    fn = doc.footnotes[0]
    assert (fn.page, fn.n) == (1, "1")
    assert fn.text == "Subs. by Act 22 of 2023, s. 44 for clause (j) (w.e.f. 13-11-2025)."


def test_footnote_label_variants() -> None:
    # IN.COW2019@en@1 p.5 "1.18th December, 2020--...",
    # IN.SSC2020@en@1 p.8 "1*. 3rd May, 2021--...",
    # IN.CPA2019@en@1 p.4 "*. Vide notification No. S.O. 3912(E) ..."
    body = chars(
        "(1) This Code may be called the Code on Wages, 2019, and it extends "
        "to the whole of India.\n" * 3
    )
    for line, label in (
        ("1.18th December, 2020", "1"),
        ("1*. 3rd May, 2021", "1*"),
        ("*. Vide notification", "*"),
    ):
        doc = lines_from_pages([body + chars(line, 9.0)])
        assert [f.n for f in doc.footnotes] == [label]
