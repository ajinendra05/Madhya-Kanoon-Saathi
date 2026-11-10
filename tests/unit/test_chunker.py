"""Chunker (DEC-055): canonical text, version chain, index_scope, splitting, QA. Snippets cite their source."""

from dataclasses import replace
from datetime import UTC, date, datetime

from madhya_kanoon_saathi.common.section_uid import parse_chunk_id
from madhya_kanoon_saathi.ingestion.chunker import (
    MAX_TOKENS,
    build_chunks,
    canonicalise,
    qa,
)
from madhya_kanoon_saathi.ingestion.manifest import (
    AppliesTo,
    CommencementOverride,
    Document,
    Instrument,
)
from madhya_kanoon_saathi.ingestion.pdf_text import Footnote, Line
from madhya_kanoon_saathi.ingestion.structure import parse_statute

SHA = "8d73989088febe131299d4b9a2f17b83002a576fab15084882c8f30d3424bc20"
DOC = Document(
    doc_id="IN.RTI2005@en@1",
    instrument_id="IN.RTI2005",
    language="en",
    status="in_force",
    mode="index",
    source_url="https://www.indiacode.nic.in/bitstream/x.pdf",
    publisher="India Code",
    fetched_at=datetime(2026, 11, 8, tzinfo=UTC),
    sha256=SHA,
    bytes=1,
    content_type="application/pdf",
    text_layer="born_digital",
    applies_to=AppliesTo(level="national"),
)
INST = Instrument(
    instrument_id="IN.RTI2005", type="act", jurisdiction="IN", commenced_on=date(2005, 6, 15)
)


def body(*texts: str, page: int = 10) -> list[Line]:
    out = [Line(page, "[15th June, 2005.]", "body")]
    for t in texts:
        if t.startswith("^"):
            out.append(Line(page, t[1:], "body", ((0, len(t) - 1),)))
        else:
            out.append(Line(page, t, "body"))
    return out


def test_canonicalise_markers_breaks_and_hyphens() -> None:
    raw = "1\n[(j) information which relates to personal\ninformation;]\n(2) sub-\nsection (1) applies"
    rmap = {"markers": [[0, 1]], "breaks": [raw.index("\n(2)")]}
    assert (
        canonicalise(raw, rmap)
        == "[(j) information which relates to personal information;]\n(2) sub-section (1) applies"
    )


def test_canonicalise_keeps_nukta_and_drops_invisibles() -> None:
    # DEC-054: stored text keeps the nukta; zero-width joiners go
    assert canonicalise("ज़मीन‍ का\nख़सरा", {"markers": [], "breaks": []}) == "ज़मीन का ख़सरा"


def test_rti_s8_chunk_with_footnote_and_version() -> None:
    # IN.RTI2005@en@1 pp.10-11 (s.8 renumbered 2 so the section sequence check passes)
    parsed = parse_statute(
        "IN.RTI2005",
        body(
            "1. Short title.—(1) This Act may be called the Right to Information Act, 2005.",
            "2. Exemption from disclosure of information.—(1) Notwithstanding anything contained in this Act,",
            "(a) information, disclosure of which would prejudicially affect the sovereignty",
            "^1",
            "[(b) information which relates to personal information;]",
            "(2) Notwithstanding anything in the Official Secrets Act, 1923",
        ),
    )
    fns = [Footnote(10, "1", "Subs. by Act 22 of 2023, s. 44 for clause (j) (w.e.f. 13-11-2025).")]
    res = qa(build_chunks(parsed, DOC, INST, fns, "pdfium-test"))
    assert res.errors == []
    by_uid = {c.section_uid: c for c in res.chunks}
    c = by_uid["IN.RTI2005:s2:ss1"]
    assert c.chunk_id == "IN.RTI2005:s2:ss1@en@2005-06-15" and c.version_source == "commenced_on"
    assert c.text.startswith("2. Exemption from disclosure of information.—(1) Notwithstanding")
    assert (
        "\n[(b) information which relates to personal information;]" in c.text
        and "1\n[" not in c.text
    )
    assert c.footnotes == [{"n": "1", "page": "10", "text": fns[0].text}]
    assert c.heading == "Exemption from disclosure of information"
    assert c.locator == {"kind": "pdf_page", "pages": [10, 10]} and c.jurisdiction == "IN"
    assert canonicalise(c.raw_text, c.raw_map) == c.text


def test_version_chain_override_then_undated() -> None:
    parsed = parse_statute(
        "IN.RTI2005",
        body("1. Short title.—(1) This Act may be called the Right to Information Act."),
    )
    inst = replace(
        INST, commencement_overrides=(CommencementOverride("IN.RTI2005:s1", date(2005, 10, 12)),)
    )
    (c,) = build_chunks(parsed, DOC, inst, [], "x").chunks
    assert c.version == "2005-10-12" and c.version_source == "commencement_override"
    bare = replace(INST, commenced_on=None, enacted_on=None)
    (c,) = build_chunks(parsed, DOC, bare, [], "x").chunks
    assert c.version == f"nd-{SHA[:8]}" and parse_chunk_id(c.chunk_id).version == f"nd-{SHA[:8]}"
    dated = replace(DOC, valid_from=date(2025, 11, 18))
    (c,) = build_chunks(parsed, dated, INST, [], "x").chunks
    assert c.version_source == "valid_from"


def test_index_scope_and_repealed_sections_are_skipped() -> None:
    # IN.TPA1882@en@1 corpus scope is ss.105-111 (DEC-051); s.85 is "[...] Rep. by ..." in the text
    parsed = parse_statute(
        "IN.TPA1882",
        body(
            "1. Short title.—This Act may be called the Transfer of Property Act, 1882.",
            "2.[Parties to suits for foreclosure, sale and redemption.] Rep. by the Code of Civil Procedure",
            "3. Lease defined.—A lease of immovable property is a transfer of a right to enjoy such property",
        ),
    )
    doc = replace(
        DOC, doc_id="IN.TPA1882@en@1", instrument_id="IN.TPA1882", index_scope=("IN.TPA1882:s3",)
    )
    inst = replace(INST, instrument_id="IN.TPA1882")
    res = build_chunks(parsed, doc, inst, [], "x")
    assert [c.section_uid for c in res.chunks] == ["IN.TPA1882:s3"]
    assert "IN.TPA1882:s2 (repealed in text)" in res.skipped
    assert "IN.TPA1882:s1 (outside index_scope)" in res.skipped


def test_long_subsection_splits_into_clauses() -> None:
    # shape of IN.SSC2020@en@1 s.131(3): "(3) (a) ..." with long clauses
    long = " ".join(["word"] * 200)
    parsed = parse_statute(
        "IN.SSC2020",
        body(
            "1. Short title.—(1) This Code may be called the Code on Social Security, 2020.",
            "(2) It extends to the whole of India.",
            f"(3) (a) The Central Provident Fund Commissioner may {long}",
            f"(b) A notice issued under this sub-section {long}",
        ),
    )
    doc = replace(DOC, doc_id="IN.SSC2020@en@1", instrument_id="IN.SSC2020")
    res = qa(build_chunks(parsed, doc, replace(INST, instrument_id="IN.SSC2020"), [], "x"))
    uids = [c.section_uid for c in res.chunks]
    assert "IN.SSC2020:s1:ss3:cl_a" in uids and "IN.SSC2020:s1:ss3:cl_b" in uids
    assert all(c.token_estimate <= MAX_TOKENS for c in res.chunks) and res.errors == []


def test_bill_material_after_the_act_is_not_parsed() -> None:
    # IN.IRC2020@en@1 p.66: "STATEMENT OF OBJECTS AND REASONS" follows the schedules
    parsed = parse_statute(
        "IN.IRC2020",
        body(
            "1. Short title.—(1) This Code may be called the Industrial Relations Code, 2020.",
            "THE THIRD SCHEDULE",
            "11. Any increase or reduction (other than casual) in the number of persons employed",
            "STATEMENT OF OBJECTS AND REASONS",
            "5. The salient features of the Industrial Relations Code, 2020, inter alia, are as follows:—",
        ),
    )
    assert parsed.trailing[0].text == "STATEMENT OF OBJECTS AND REASONS"
    assert all("salient" not in ln.text for u in parsed.units for ln in u.lines)


def test_qa_flags_tampered_text() -> None:
    parsed = parse_statute(
        "IN.RTI2005",
        body("1. Short title.—(1) This Act may be called the Right to Information Act."),
    )
    res = build_chunks(parsed, DOC, INST, [], "x")
    res.chunks[0].text += " extra"
    assert any("raw/canonical mismatch" in e for e in qa(res).errors)
