"""Tests for the corpus manifest validator (DEC-040).

Fixtures use invented instruments (TESTACT/TESTRULES) so no test states a legal fact.
"""

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from madhya_kanoon_saathi.ingestion.manifest import (
    ManifestError,
    load_manifest,
    parse_manifest,
)

SHA = "a" * 64


def _verification(what: str, by: str = "claude", result: str = "confirmed") -> dict[str, Any]:
    return {
        "what": what,
        "by": by,
        "on": "2026-11-06",
        "method": "compared with official gazette PDF",
        "evidence": "https://example.gov.in/gazette.pdf p.1",
        "result": result,
    }


def _valid() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "instruments": [
            {
                "instrument_id": "IN.TESTACT2000",
                "type": "act",
                "jurisdiction": "IN",
                "title_en": "Test Act, 2000",
                "enacted_on": "2000-01-01",
                "commenced_on": "2000-02-01",
                "commencement_overrides": [
                    {"uid": "IN.TESTACT2000:s5", "commenced_on": "2001-01-01"}
                ],
                "amendments": [
                    {
                        "by": "IN.TESTAMEND2010",
                        "commenced_on": "2010-05-01",
                        "affects": ["IN.TESTACT2000:s3"],
                    }
                ],
            },
            {
                "instrument_id": "IN.TESTRULES2001",
                "type": "rules",
                "jurisdiction": "IN",
                "title_hi": "परीक्षण नियम",
                "parent_instrument": "IN.TESTACT2000",
                "made_under": ["IN.TESTACT2000:s20"],
            },
            {
                "instrument_id": "MP.TESTGUIDE2026",
                "type": "official_guide",
                "jurisdiction": "MP",
                "title_en": "Test portal guide",
            },
        ],
        "documents": [
            {
                "doc_id": "IN.TESTACT2000@en@1",
                "instrument_id": "IN.TESTACT2000",
                "language": "en",
                "status": "in_force",
                "mode": "index",
                "source_url": "https://example.gov.in/act.pdf",
                "publisher": "Example ministry",
                "fetched_at": "2026-11-06T10:00:00+05:30",
                "sha256": SHA,
                "bytes": 1234,
                "content_type": "application/pdf",
                "text_layer": "born_digital",
                "valid_from": "2000-02-01",
                "applies_to": {"level": "national"},
                "applies_to_overrides": [
                    {"uid": "IN.TESTACT2000:s9", "applies_to": {"level": "state", "states": ["MP"]}}
                ],
                "verifications": [_verification("status"), _verification("commencement")],
                "local_path": "raw/testact.pdf",
            },
            {
                "doc_id": "IN.TESTRULES2001@hi@1",
                "instrument_id": "IN.TESTRULES2001",
                "language": "hi",
                "status": "draft",
                "mode": "gated",
                "gate": ["L3"],
                "source_url": "https://example.gov.in/rules.pdf",
                "publisher": "Example ministry",
                "fetched_at": "2026-11-06T10:00:00+05:30",
                "sha256": "b" * 64,
                "bytes": 99,
                "content_type": "application/pdf",
                "text_layer": "scanned",
                "ocr_engine": "bodhan",
                "applies_to": {"level": "national"},
            },
            {
                "doc_id": "MP.TESTGUIDE2026@hi@1",
                "instrument_id": "MP.TESTGUIDE2026",
                "language": "hi",
                "status": "in_force",
                "mode": "guide",
                "source_url": "https://example.mp.gov.in/guide",
                "publisher": "Example MP dept",
                "fetched_at": "2026-11-06T10:00:00+05:30",
                "sha256": "c" * 64,
                "bytes": 10,
                "content_type": "text/html",
                "text_layer": "born_digital",
                "applies_to": {"level": "state", "states": ["MP"]},
                "valid_from": "2026-01-01",
                "expires_on": "2026-12-31",
            },
        ],
    }


def _errors(data: dict[str, Any]) -> list[str]:
    manifest, errors = parse_manifest(data)
    assert manifest is None
    return errors


def test_valid_manifest_parses() -> None:
    manifest, errors = parse_manifest(_valid())
    assert errors == []
    assert manifest is not None
    act = manifest.instruments["IN.TESTACT2000"]
    assert act.authority_rank == 1 and act.binding
    guide = manifest.instruments["MP.TESTGUIDE2026"]
    assert guide.authority_rank == 5 and not guide.binding
    assert manifest.instruments["IN.TESTRULES2001"].made_under == ("IN.TESTACT2000:s20",)


def test_is_current_is_computed() -> None:
    manifest, _ = parse_manifest(_valid())
    assert manifest is not None
    guide = manifest.documents["MP.TESTGUIDE2026@hi@1"]
    assert guide.is_current(date(2026, 6, 1))
    assert not guide.is_current(date(2027, 1, 1))  # expired -> auto-abstain
    assert not guide.is_current(date(2025, 12, 31))  # before valid_from
    draft = manifest.documents["IN.TESTRULES2001@hi@1"]
    assert not draft.is_current(date(2026, 6, 1))  # drafts are never current


def _mutate(path: list[Any], value: Any) -> dict[str, Any]:
    data = copy.deepcopy(_valid())
    target: Any = data
    for key in path[:-1]:
        target = target[key]
    if value is _DELETE:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return data


_DELETE = object()
DOC0 = ["documents", 0]
INST0 = ["instruments", 0]


@pytest.mark.parametrize(
    ("path", "value", "expected"),
    [
        ([*DOC0, "status"], "enacted", "not in"),
        ([*DOC0, "mode"], "live", "not in"),
        ([*DOC0, "sha256"], "ABC", "sha256"),
        ([*DOC0, "bytes"], 0, "positive integer"),
        ([*DOC0, "fetched_at"], "2026-11-06T10:00:00", "timezone"),
        ([*DOC0, "valid_to"], "1999-01-01", "valid_to is before valid_from"),
        ([*DOC0, "source_url"], "ftp://x", "http(s)"),
        ([*DOC0, "s3_path"], "bucket/key", "s3://"),
        ([*DOC0, "local_path"], "C:/data/x.pdf", "relative"),
        ([*DOC0, "ocr_engine"], "bodhan", "born_digital"),
        ([*DOC0, "language"], "mr", "not in"),  # DEC-016
        ([*DOC0, "doc_id"], "OTHER@en@1", "must start with"),
        ([*DOC0, "instrument_id"], "IN.MISSING2000", "unknown instrument_id"),
        ([*DOC0, "surprise"], 1, "unknown field"),
        ([*DOC0, "applies_to"], {"level": "state"}, "needs 'states'"),
        ([*DOC0, "applies_to"], {"level": "national", "states": ["MP"]}, "takes no states"),
        ([*DOC0, "applies_to"], {"level": "state", "states": ["MH"]}, "invalid value"),
        ([*DOC0, "applies_to"], {"level": "district", "states": ["MP"]}, "needs 'districts'"),
        ([*DOC0, "applies_to_overrides", 0, "uid"], "IN.TESTRULES2001:r1", "not a provision"),
        ([*DOC0, "gate"], ["L3"], "only allowed with mode=gated"),
        (["documents", 1, "gate"], [], "needs at least one 'gate'"),
        (["documents", 1, "gate"], ["later"], "invalid value"),
        (["documents", 2, "applies_to"], {"level": "national"}, "cannot apply nationally"),
        (["documents", 2, "mode"], "index", "official guides use mode=guide"),
        ([*INST0, "instrument_id"], "RTI2005", "bad instrument_id"),
        ([*INST0, "jurisdiction"], "MP", "prefix must match"),
        ([*INST0, "type"], "circular", "not in"),
        ([*INST0, "commenced_on"], "1999-01-01", "before enacted_on"),
        ([*INST0, "title_en"], _DELETE, "at least one of title_en"),
        ([*INST0, "amendments", 0, "affects"], ["IN.OTHER2000:s1"], "not a provision"),
        ([*INST0, "commencement_overrides", 0, "uid"], "IN.TESTACT2000:ss1", "not a provision"),
        (["instruments", 1, "made_under"], ["IN.OTHER2000:s2"], "not a provision of"),
        (["instruments", 1, "parent_instrument"], "IN.NOPE2000", "unknown parent_instrument"),
        (["schema_version"], 2, "schema_version"),
    ],
)
def test_invalid_fields_are_reported(path: list[Any], value: Any, expected: str) -> None:
    errors = _errors(_mutate(path, value))
    assert any(expected in e for e in errors), errors


@pytest.mark.parametrize(
    "verifications",
    [
        [],
        [{**_verification("status")}],  # commencement missing
        [_verification("status"), _verification("commencement", result="unclear")],
    ],
)
def test_index_gate_needs_confirmed_status_and_commencement(verifications: list[Any]) -> None:
    errors = _errors(_mutate([*DOC0, "verifications"], verifications))
    assert any("index gate" in e for e in errors), errors


def test_index_gate_blocks_on_conflict() -> None:
    v = [
        _verification("status"),
        _verification("commencement"),
        _verification("text_matches_source", result="conflict"),
    ]
    errors = _errors(_mutate([*DOC0, "verifications"], v))
    assert any("result=conflict" in e for e in errors), errors


def test_interpretation_needs_a_human() -> None:
    v = [_verification("status"), _verification("commencement"), _verification("interpretation")]
    errors = _errors(_mutate([*DOC0, "verifications"], v))
    assert any("malik or advocate" in e for e in errors), errors
    ok = [
        _verification("status"),
        _verification("commencement"),
        _verification("interpretation", by="advocate"),
    ]
    _, errors = parse_manifest(_mutate([*DOC0, "verifications"], ok))
    assert errors == []


def test_gated_documents_skip_the_index_gate() -> None:
    _, errors = parse_manifest(_valid())
    assert errors == []  # documents[1] is gated with no verifications


def test_duplicate_ids() -> None:
    data = _valid()
    data["documents"].append(copy.deepcopy(data["documents"][0]))
    assert any("duplicate doc_id" in e for e in _errors(data))


def test_all_errors_are_collected() -> None:
    data = _mutate([*DOC0, "status"], "bad")
    data["documents"][0]["mode"] = "bad"
    assert len(_errors(data)) >= 2


def test_not_an_object() -> None:
    assert parse_manifest([]) == (None, ["manifest must be a JSON object"])


def test_load_manifest(tmp_path: Path) -> None:
    good = tmp_path / "m.json"
    good.write_text(json.dumps(_valid(), ensure_ascii=False), encoding="utf-8")
    assert len(load_manifest(good).documents) == 3
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(_mutate([*DOC0, "status"], "x")), encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(bad)
    assert exc.value.errors


def test_repo_manifest_is_valid() -> None:
    repo_manifest = Path(__file__).parents[2] / "data" / "corpus_manifest.json"
    if not repo_manifest.exists():
        pytest.skip("no corpus manifest yet (W0.4)")
    load_manifest(repo_manifest)


# --------------------------------------------------------------- DEC-044 additions


def test_ordinance_type_is_binding_rank_1() -> None:
    data = _valid()
    data["instruments"].append(
        {
            "instrument_id": "MP.TESTORD2020",
            "type": "ordinance",
            "jurisdiction": "MP",
            "title_hi": "परीक्षण अध्यादेश",
            "amends": ["MP.TESTGUIDE2026"],
        }
    )
    manifest, errors = parse_manifest(data)
    assert errors == []
    assert manifest is not None
    ordinance = manifest.instruments["MP.TESTORD2020"]
    assert ordinance.binding and ordinance.authority_rank == 1
    assert ordinance.amends == ("MP.TESTGUIDE2026",)


def test_amends_must_be_ids_and_not_self() -> None:
    errors = _errors(_mutate([*INST0, "amends"], ["IN.TESTACT2000"]))
    assert any("cannot amend itself" in e for e in errors), errors
    errors = _errors(_mutate([*INST0, "amends"], ["not an id"]))
    assert any("'amends' has invalid value" in e for e in errors), errors


def test_enacted_not_commenced_is_never_current() -> None:
    data = _mutate(["instruments", 0, "commenced_on"], _DELETE)
    data["documents"][1]["status"] = "enacted_not_commenced"
    manifest, errors = parse_manifest(data)
    assert errors == [], errors
    assert manifest is not None
    assert not manifest.documents["IN.TESTRULES2001@hi@1"].is_current(date(2030, 1, 1))


def test_enacted_not_commenced_conflicts_with_commencement_date() -> None:
    # documents[0] belongs to IN.TESTACT2000, which has commenced_on set in the fixture.
    data = _mutate([*DOC0, "status"], "enacted_not_commenced")
    data["documents"][0]["mode"] = "archive"
    errors = _errors(data)
    assert any("update status from enacted_not_commenced" in e for e in errors), errors


# --------------------------------------------------------------- DEC-048 draft index gate


def test_draft_can_be_indexed_with_status_check_only() -> None:
    data = _mutate([*DOC0, "status"], "draft")
    data["documents"][0]["verifications"] = [_verification("status")]
    _, errors = parse_manifest(data)
    assert errors == [], errors


def test_draft_index_still_needs_confirmed_status() -> None:
    data = _mutate([*DOC0, "status"], "draft")
    data["documents"][0]["verifications"] = [_verification("text_matches_source")]
    errors = _errors(data)
    assert any("index gate" in e and "'status'" in e for e in errors), errors


def test_draft_index_blocked_by_conflict() -> None:
    data = _mutate([*DOC0, "status"], "draft")
    data["documents"][0]["verifications"] = [
        _verification("status"),
        _verification("text_matches_source", result="conflict"),
    ]
    assert any("result=conflict" in e for e in _errors(data))


@pytest.mark.parametrize("status", ["in_force", "enacted_not_commenced", "proposal"])
def test_non_draft_index_still_needs_commencement(status: str) -> None:
    data = _mutate([*DOC0, "status"], status)
    data["documents"][0]["verifications"] = [_verification("status")]
    if status == "enacted_not_commenced":
        data["instruments"][0].pop("commenced_on")
    errors = _errors(data)
    assert any("'commencement'" in e for e in errors), errors


# --------------------------------------------------------------- DEC-051 index_scope


def test_index_scope_limits_what_is_in_scope() -> None:
    data = _mutate([*DOC0, "index_scope"], ["IN.TESTACT2000:s5", "IN.TESTACT2000:s7:ss1"])
    manifest, errors = parse_manifest(data)
    assert errors == [], errors
    assert manifest is not None
    doc = next(iter(manifest.documents.values()))
    assert doc.in_scope("IN.TESTACT2000:s5")
    assert doc.in_scope("IN.TESTACT2000:s5:ss2:cl_a")  # descendants are in scope
    assert doc.in_scope("IN.TESTACT2000:s7:ss1")
    assert not doc.in_scope("IN.TESTACT2000:s7")  # the parent of a scoped uid is not
    assert not doc.in_scope("IN.TESTACT2000:s6")


def test_no_index_scope_means_whole_document() -> None:
    manifest, errors = parse_manifest(_valid())
    assert errors == [] and manifest is not None
    doc = next(iter(manifest.documents.values()))
    assert doc.index_scope == ()
    assert doc.in_scope("IN.TESTACT2000:s99")


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        ([], "non-empty"),
        (["IN.OTHER2000:s1"], "not a provision of"),
        (["IN.TESTACT2000"], "not a provision of"),
        (["IN.TESTACT2000:x9"], "not a provision of"),
        (["IN.TESTACT2000:s5", "IN.TESTACT2000:s5"], "duplicate"),
        (["IN.TESTACT2000:s5", "IN.TESTACT2000:s5:ss1"], "already covered"),
        ("IN.TESTACT2000:s5", "list of strings"),
    ],
)
def test_bad_index_scope_is_rejected(scope: Any, expected: str) -> None:
    errors = _errors(_mutate([*DOC0, "index_scope"], scope))
    assert any(expected in e for e in errors), errors


# --------------------------------------------------------------- DEC-052 model_law


def _model_law() -> dict[str, Any]:
    data = _valid()
    data["instruments"][0]["type"] = "model_law"
    data["instruments"][0].pop("commenced_on")
    data["instruments"][0].pop("commencement_overrides")
    data["instruments"][0].pop("amendments")
    data["documents"][0]["status"] = "model_law"
    data["documents"][0]["verifications"] = [_verification("status")]
    return data


def test_model_law_indexes_with_status_check_only_and_is_not_binding() -> None:
    manifest, errors = parse_manifest(_model_law())
    assert errors == [], errors
    assert manifest is not None
    inst = manifest.instruments["IN.TESTACT2000"]
    assert not inst.binding
    assert inst.authority_rank == 6
    doc = next(iter(manifest.documents.values()))
    assert not doc.is_current(date(2030, 1, 1))


def test_model_law_cannot_have_commencement() -> None:
    data = _model_law()
    data["instruments"][0]["commenced_on"] = "2021-06-02"
    assert any("cannot have commenced_on" in e for e in _errors(data))


def test_model_law_documents_need_model_law_status() -> None:
    data = _model_law()
    data["documents"][0]["status"] = "in_force"
    data["documents"][0]["verifications"] = [_verification("status"), _verification("commencement")]
    assert any("need status model_law" in e for e in _errors(data))


def test_model_law_index_still_needs_confirmed_status() -> None:
    data = _model_law()
    data["documents"][0]["verifications"] = [_verification("text_matches_source")]
    assert any("index gate" in e and "'status'" in e for e in _errors(data))
