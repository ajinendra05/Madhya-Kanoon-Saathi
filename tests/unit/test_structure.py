"""Provision-tree parsing on real snippets of India Code PDFs (text as extracted by pypdfium2, 2026-11-10).

Each test cites the document and page the lines come from. Lines are shortened where only the start matters.
"""

from madhya_kanoon_saathi.common.section_uid import is_valid
from madhya_kanoon_saathi.ingestion.pdf_text import Line
from madhya_kanoon_saathi.ingestion.structure import parse_statute

ENACTED = "[15th June, 2005.]"


def lines(*texts: str, page: int = 5) -> list[Line]:
    out = [Line(page, ENACTED, "body")]
    for t in texts:
        if t.startswith("^"):  # "^1" = a superscript footnote marker on its own line
            out.append(Line(page, t[1:], "body", ((0, len(t) - 1),)))
        else:
            out.append(Line(page, t, "body"))
    return out


def uids(instrument: str, *texts: str) -> list[str]:
    parsed = parse_statute(instrument, lines(*texts))
    assert all(is_valid(u.uid) for u in parsed.units)
    return [u.uid.split(":", 1)[1] for u in parsed.units if ":" in u.uid]


def test_front_matter_is_unassigned() -> None:
    # IN.RTI2005@en@1 p.4-5: contents lines ("19. Appeal.") come before the enactment line
    parsed = parse_statute(
        "IN.RTI2005",
        [
            Line(4, "19. Appeal.", "body"),
            Line(5, ENACTED, "body"),
            Line(5, "1. Short title.—(1) This Act", "body"),
        ],
    )
    assert [ln.text for ln in parsed.unassigned] == ["19. Appeal.", ENACTED]
    assert [u.uid for u in parsed.units] == ["IN.RTI2005:s1", "IN.RTI2005:s1:ss1"]


def test_rti_s8_provisos_between_clauses_belong_to_clause_i() -> None:
    # IN.RTI2005@en@1 pp.10-11: two provisos sit between clauses (i) and (j); (j) has marker "1" on its own line
    got = uids(
        "IN.RTI2005",
        "1. Short title.—(1) This Act may be called the Right to Information Act, 2005.",
        "2. Definitions.—In this Act, unless the context otherwise requires,—",
        "(a) “appropriate Government” means in relation to a public authority",
        "3. Right to information.—Subject to the provisions of this Act, all citizens shall have",
        "4. Obligations of public authorities.—(1) Every public authority shall—",
        "5. Designation of Public Information Officers.—(1) Every public authority shall",
        "6. Request for obtaining information.—(1) A person, who desires to obtain any",
        "7. Disposal of request.—(1) Subject to the proviso to sub-section (2) of section 5",
        "8. Exemption from disclosure of information.—(1) Notwithstanding anything contained",
        "(a) information, disclosure of which would prejudicially affect the sovereignty",
        *[f"({c}) information of kind {c};" for c in "bcdefg"],
        "(h) information which would impede the process of investigation",
        "(i) cabinet papers including records of deliberations of the Council of Ministers,",
        "Provided that the decisions of Council of Ministers, the reasons thereof, and the material",
        "Provided further that those matters which come under the exemptions specified in this section",
        "^1",
        "[(j) information which relates to personal information;]",
        "(2) Notwithstanding anything in the Official Secrets Act, 1923 (19 of 1923) nor any of the",
    )
    assert "s8:ss1:cl_a" in got
    assert "s8:ss1:cl_i:prov1" in got and "s8:ss1:cl_i:prov2" in got
    assert "s8:ss1:cl_h" in got and "s8:ss1:cl_j" in got and "s8:ss2" in got


def test_rti_s2_h_has_two_sub_lists_and_i_is_disambiguated() -> None:
    # IN.RTI2005@en@1 p.6: s.2(h) has sub-clauses (a)-(d), then "(i) body owned..." (roman, "(ii)" follows);
    # the next "(i)" is clause (i) "record" because "(j)" follows its own sub-list
    got = uids(
        "IN.RTI2005",
        "1. Short title.—(1) This Act may be called the Right to Information Act, 2005.",
        "2. Definitions.—In this Act, unless the context otherwise requires,—",
        "(g) “prescribed” means prescribed by rules made under this Act",
        "(a) “appropriate Government” means in relation to a public authority which is established,",
        "(b) “Central Information Commission” means the Central Information Commission",
        "(c) “Central Public Information Officer” means",
        "(d) “Chief Information Commissioner”",
        "(e) “competent authority” means—",
        "(f) “information” means any material in any form,",
        "(g) “prescribed” means prescribed by rules made under this Act",
        "(h) “public authority” means any authority or body or institution of self-government",
        "(a) by or under the Constitution;",
        "(b) by any other law made by Parliament;",
        "(i) body owned, controlled or substantially financed;",
        "(ii) non-Government organisation substantially financed,",
        "(i) “record” includes—",
        "(a) any document, manuscript and file;",
        "(j) “right to information” means the right to information accessible under this Act",
    )
    assert "s2:cl_h:scla_a" in got and "s2:cl_h:scla_b" in got
    assert "s2:cl_h:scl_i" in got and "s2:cl_h:scl_ii" in got
    assert "s2:cl_i" in got and "s2:cl_i:scla_a" in got and "s2:cl_j" in got


def test_letter_i_inside_exclusion_list() -> None:
    # IN.COW2019@en@1 pp.7-8, definition of "wages": roman list (i)-(iii), then exclusions (a)-(k)
    # where "(i) any commission" is the letter i because "(j)" follows
    got = uids(
        "IN.COW2019",
        "1. Short title.—(1) This Code may be called the Code on Wages, 2019.",
        "2. Definitions.—In this Code, unless the context otherwise requires,—",
        "(a) “appropriate Government” means,—",
        "(b) “contractor”, in relation to an establishment, means",
        "(c) “wages” means all remuneration whether by way of salaries, allowances",
        "(i) basic pay;",
        "(ii) dearness allowance; and",
        "(a) any bonus payable under any law for the time being in force,",
        *[f"({c}) any exclusion of kind {c};" for c in "bcdefg"],
        "(h) any gratuity payable on the termination of employment;",
        "(i) any commission payable to the employee;",
        "(j) any remuneration payable under any award or settlement",
        "(d) “worker” means any person",
    )
    assert "s2:cl_c:scl_i" in got and "s2:cl_c:scl_ii" in got
    assert "s2:cl_c:scla_a" in got
    assert "s2:cl_c:scla_i" in got and "s2:cl_c:scla_j" in got
    assert "s2:cl_d" in got


def test_section_heading_variants() -> None:
    # IN.SSC2020@en@1 p.78 "131. other modes ..." (lowercase); p.21 "49.Matters ..." (no space);
    # IN.COW2019@en@1 p.19 "39 .Time limit ..." (space before dot); IN.SSC2020 s.9 dash missing before "(1)"
    parsed = parse_statute(
        "IN.SSC2020",
        lines(
            "1. Short title.—(1) This Code may be called the Code on Social Security, 2020.",
            "2.Definitions.—In this Code,",
            "3 .Registration.—(1) Every establishment",
            "4. other modes of recovery.— (1) Notwithstanding the issue of a certificate",
            "5. Procedure for transaction of business of Social Security Organisation, etc. (1) A Social",
        ),
    )
    secs = [u for u in parsed.units if u.kind == "section"]
    assert [u.label for u in secs] == ["1", "2", "3", "4", "5"]
    assert (
        secs[4].heading
        == "Procedure for transaction of business of Social Security Organisation, etc"
    )
    assert "IN.SSC2020:s5:ss1" in {u.uid for u in parsed.units}


def test_wrapped_heading_and_repealed_sections() -> None:
    # IN.TPA1882@en@1 p.37: s.106 heading wraps; p.33: "85.[Parties to suits ...] Rep. by ...";
    # IN.RA1908@en@1: s.56 bracketed heading wraps before "Rep. by"
    parsed = parse_statute(
        "IN.TPA1882",
        lines(
            "1. Short title.—This Act may be called the Transfer of Property Act, 1882.",
            "2.[Parties to suits for foreclosure, sale and redemption.] Rep. by the Code of Civil Procedure",
            "3. [Copy of entries in Indexes Nos. I, II and III to be sent by Sub-Registrar to Registrar",
            "and filed.] Rep. by the Indian Registration (Amendment) Act, 1929 (15 of 1929), s. 2.",
            "4. Duration of certain leases in absence of written contract or",
            "local usage.—(1) In the absence of a contract or local law or usage to the contrary,",
        ),
    )
    secs = {u.label: u for u in parsed.units if u.kind == "section"}
    assert (
        secs["2"].repealed
        and secs["2"].heading == "Parties to suits for foreclosure, sale and redemption"
    )
    assert secs["3"].repealed
    assert not secs["4"].repealed
    assert (
        secs["4"].heading
        == "Duration of certain leases in absence of written contract or local usage"
    )
    assert "IN.TPA1882:s4:ss1" in {u.uid for u in parsed.units}


def test_state_amendment_blocks_are_set_aside() -> None:
    # IN.RA1908@en@1 p.13: a UP version of s.18A after main s.18, then main s.19 (renumbered 2/2A/3)
    parsed = parse_statute(
        "IN.RA1908",
        lines(
            "1. Short title.—(1) This Act may be called the Registration Act, 1908.",
            "2. Definitions.—In this Act, unless there is anything repugnant",
            "STATE AMENDMENT",
            "Uttar Pradesh",
            "2A. Documents for registration to be accompanied by a true copy thereof.—(1) The Registering",
            "[Vide Uttar Pradesh Act 14 of 1971, s. 2]",
            "3. Registration-districts.—The State Government shall form districts",
        ),
    )
    assert [u.uid for u in parsed.units if u.kind == "section"] == [
        "IN.RA1908:s1",
        "IN.RA1908:s2",
        "IN.RA1908:s3",
    ]
    assert len(parsed.state_amendments) == 1
    sa = parsed.state_amendments[0]
    assert sa.after_uid == "IN.RA1908:s2" and len(sa.lines) == 4 and not sa.mentions_mp


def test_schedule_paragraphs() -> None:
    # IN.RTI2005@en@1 pp.24-25: "THE SECOND SCHEDULE" with numbered organisations
    got = uids(
        "IN.RTI2005",
        "1. Short title.—(1) This Act may be called the Right to Information Act, 2005.",
        "THE SECOND SCHEDULE",
        "(See section 24)",
        "1. Intelligence Bureau.",
        "2. Research and Analysis Wing of the Cabinet Secretariat.",
    )
    assert got[-3:] == ["sch2", "sch2:para1", "sch2:para2"]
