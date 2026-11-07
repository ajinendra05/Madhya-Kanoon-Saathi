"""Tests for section_uid (DEC-040). Examples are ID shapes, not claims about any provision."""

from datetime import date

import pytest

from madhya_kanoon_saathi.common.section_uid import (
    InvalidSectionUidError,
    ancestors,
    belongs_to,
    covers,
    is_valid,
    make_chunk_id,
    parent,
    parse,
    parse_chunk_id,
)


@pytest.mark.parametrize(
    "uid",
    [
        "IN.RTI2005",
        "IN.RTI2005:s8",
        "IN.RTI2005:s8:ss1:cl_j",
        "MP.ACA1961:s12:ss1:cl_a",
        "IN.COW2019:s17:prov2",
        "MP.LRC1959:s13A",
        "IN.RTI2005:s8:ss1:cl_j:scl_ii",
        "IN.RTI2005:s8:expl1",
        "IN.RTIR2012:r4",
        "IN.RTIR2012:r4:ss2:cl_b",
        "IN.CPA2019:sch1",
        "IN.CPA2019:sch1:para3",
        "MP.LSG2010:form_a",
        "IN.X2020:reg5",
    ],
)
def test_valid_uids_round_trip(uid: str) -> None:
    assert str(parse(uid)) == uid
    assert is_valid(uid)


@pytest.mark.parametrize(
    "uid",
    [
        "",
        " IN.RTI2005:s8",  # surrounding whitespace
        "RTI2005:s8",  # no jurisdiction (plan style, DEC-040 option A rejected)
        "MH.RTI2005:s8",  # jurisdiction outside scope (DEC-016)
        "in.RTI2005:s8",  # lowercase jurisdiction
        "IN.RTI05:s8",  # year must be 4 digits
        "IN.rti2005:s8",  # lowercase code
        "IN.RTI2005:s0",  # no section 0
        "IN.RTI2005:s08",  # no leading zero
        "IN.RTI2005:ss1",  # sub-section cannot be first
        "IN.RTI2005:s8:cl_j:ss1",  # wrong order
        "IN.RTI2005:s8:s9",  # two sections
        "IN.RTI2005:s8:scl_i",  # sub-clause without clause
        "IN.RTI2005:s8:prov1:cl_a",  # proviso must be last
        "IN.RTI2005:s8:cl_J",  # clause letters are lowercase
        "IN.RTI2005:s8:",  # empty segment
        "IN.RTI2005:s८",  # Devanagari digit: canonical uids are ASCII (tokeniser converts, DEC-026)
        "IN.RTI2005:s8:cl_ज",  # Hindi clause letter: aligned structurally, never transliterated
        "IN.RTI2005:art5",  # unknown segment kind
    ],
)
def test_invalid_uids_rejected(uid: str) -> None:
    assert not is_valid(uid)
    with pytest.raises(InvalidSectionUidError):
        parse(uid)


def test_parsed_fields() -> None:
    p = parse("MP.ACA1961:s12:ss1:cl_a")
    assert p.jurisdiction == "MP"
    assert p.instrument_id == "MP.ACA1961"
    assert p.year == 1961
    assert p.segments == ("s12", "ss1", "cl_a")


def test_parent_and_ancestors_are_computed_from_the_uid() -> None:
    assert parent("IN.RTI2005:s8:ss1:cl_j") == "IN.RTI2005:s8:ss1"
    assert parent("IN.RTI2005") is None
    assert ancestors("IN.RTI2005:s8:ss1:cl_j") == [
        "IN.RTI2005:s8:ss1",
        "IN.RTI2005:s8",
        "IN.RTI2005",
    ]


@pytest.mark.parametrize(
    ("retrieved", "expected", "result"),
    [
        ("IN.RTI2005:s8:ss1:cl_j", "IN.RTI2005:s8:ss1:cl_j", True),  # equal
        ("IN.RTI2005:s8:ss1", "IN.RTI2005:s8:ss1:cl_j", True),  # ancestor covers descendant
        ("IN.RTI2005", "IN.RTI2005:s8", True),
        ("IN.RTI2005:s8:ss1:cl_j", "IN.RTI2005:s8:ss1", False),  # descendant does not cover parent
        ("IN.RTI2005:s8:ss1:cl_i", "IN.RTI2005:s8:ss1:cl_j", False),  # sibling
        ("IN.RTI2005:s1", "IN.RTI2005:s10", False),  # prefix by characters is not ancestry
        ("MP.RTI2005:s8", "IN.RTI2005:s8", False),  # different jurisdiction
    ],
)
def test_covers(retrieved: str, expected: str, result: bool) -> None:
    assert covers(retrieved, expected) is result


def test_belongs_to() -> None:
    assert belongs_to("IN.RTIR2012:r4", "IN.RTIR2012")
    assert not belongs_to("IN.RTIR2012:r4", "IN.RTI2005")


def test_chunk_id_round_trip() -> None:
    cid = make_chunk_id("IN.RTI2005:s8:ss1:cl_j", "hi", date(2025, 1, 2))
    assert cid == "IN.RTI2005:s8:ss1:cl_j@hi@2025-01-02"
    uid, lang, valid_from = parse_chunk_id(cid)
    assert str(uid) == "IN.RTI2005:s8:ss1:cl_j"
    assert lang == "hi"
    assert valid_from == date(2025, 1, 2)


@pytest.mark.parametrize(
    "cid",
    [
        "IN.RTI2005:s8",  # no lang/date
        "IN.RTI2005:s8@mr@2025-01-02",  # Marathi out of scope (DEC-016)
        "IN.RTI2005:s8@hi@2025-13-01",  # impossible date
        "IN.RTI2005:s8@hi@2025-1-2",  # not zero-padded
        "IN.RTI2005:s8@hi@२०२५-०१-०२",  # Devanagari digits
        "RTI2005:s8@hi@2025-01-02",  # bad uid
    ],
)
def test_bad_chunk_ids(cid: str) -> None:
    with pytest.raises(InvalidSectionUidError):
        parse_chunk_id(cid)


def test_make_chunk_id_rejects_bad_language() -> None:
    with pytest.raises(InvalidSectionUidError):
        make_chunk_id("IN.RTI2005:s8", "mr", date(2025, 1, 2))


# --------------------------------------------------------------- roman clauses (DEC-045 item 7, U1)


@pytest.mark.parametrize(
    "uid",
    [
        "MP.LSGR2010:r8:clr_vii",  # rule 8, clause (vii)
        "MP.LSGR2010:r8:clr_vii:prov1",  # proviso added to clause (vii)
        "IN.X2020:s2:clr_iv:scla_b",  # roman clause with alphabetic sub-clause
        "IN.X2020:s2:clr_xiv:scl_ii",  # roman clause with roman sub-clause
        "IN.X2020:s2:cl_a:scla_b",  # alphabetic sub-clause under an alphabetic clause
        "IN.X2020:s2:clr_xlix",
        "IN.X2020:s2:clr_mmxxvi",
        "IN.X2020:s2:cl_i",  # letter (i), e.g. after (h)
        "IN.X2020:s2:clr_i",  # numeral (i)
    ],
)
def test_roman_clause_uids_valid(uid: str) -> None:
    assert str(parse(uid)) == uid


@pytest.mark.parametrize(
    "uid",
    [
        "IN.X2020:s2:clr_iiii",  # not canonical (4 = iv)
        "IN.X2020:s2:clr_vx",  # not a roman numeral
        "IN.X2020:s2:clr_ic",  # not canonical (99 = xcix)
        "IN.X2020:s2:clr_",  # empty
        "IN.X2020:s2:clr_VII",  # uppercase
        "IN.X2020:s2:clr_7",  # arabic digits
        "IN.X2020:s2:clr_vii:clr_i",  # two clause levels
        "IN.X2020:s2:cl_a:clr_i",  # alphabetic and roman clause at the same level
        "IN.X2020:s2:scla_b",  # sub-clause without a clause
        "IN.X2020:s2:ss1:scl_ii",  # sub-clause directly under a sub-section
        "IN.X2020:s2:clr_ii:scl_iiii",  # bad roman sub-clause
        "IN.X2020:s2:clr_ii:scla_B",  # uppercase sub-clause
        "IN.X2020:s2:clr_सात",  # Devanagari numeral word
    ],
)
def test_roman_clause_uids_invalid(uid: str) -> None:
    with pytest.raises(InvalidSectionUidError):
        parse(uid)


def test_letter_i_and_numeral_i_are_different_uids() -> None:
    assert not covers("IN.X2020:s2:cl_i", "IN.X2020:s2:clr_i")
    assert covers("IN.X2020:s2:clr_vii", "IN.X2020:s2:clr_vii:scla_a")
    assert parent("MP.LSGR2010:r8:clr_vii:prov1") == "MP.LSGR2010:r8:clr_vii"
