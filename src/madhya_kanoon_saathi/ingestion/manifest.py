"""Corpus manifest schema + validator (DEC-011, DEC-033, DEC-037, DEC-040).

Spec: ``docs/specs/manifest.md``. The file ``data/corpus_manifest.json`` has two lists:
``instruments`` (one row per law/guide) and ``documents`` (one row per downloaded file).

Validation is stdlib-only and collects *every* error, so a human can fix a manifest in one pass.
Derived values (authority rank, binding, "is current") are computed here and never stored.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from madhya_kanoon_saathi.common.section_uid import JURISDICTIONS, belongs_to, covers, is_valid

SCHEMA_VERSION = 1

INSTRUMENT_TYPES = frozenset(
    {
        "act",
        "rules",
        "regulations",
        "notification",
        "order",
        "scheme_guideline",
        "official_guide",
        "bill",
        "ordinance",
        "model_law",  # DEC-052
    }
)
# Derived authority (DEC-040): lower rank = higher authority. Not a retrieval weight.
AUTHORITY_RANK: dict[str, int] = {
    "act": 1,
    "rules": 2,
    "regulations": 2,
    "notification": 3,
    "order": 3,
    "scheme_guideline": 4,
    "official_guide": 5,
    "bill": 6,
    "ordinance": 1,  # DEC-044: binding like an Act while it lasts
    "model_law": 6,  # DEC-052: a template for states, not law anywhere until adopted
}
BINDING_TYPES = frozenset({"act", "ordinance", "rules", "regulations", "notification", "order"})

STATUSES = frozenset(
    {
        "in_force",
        "draft",
        "model_law",
        "repealed",
        "sub_judice_flag",
        "passed_awaiting_assent",
        "proposal",
        "enacted_not_commenced",  # DEC-044
    }
)
MODES = frozenset({"index", "gated", "archive", "guide"})
DOC_LANGUAGES = frozenset({"hi", "en", "bi"})  # bi = one bilingual file (common in gazettes)
TEXT_LAYERS = frozenset({"born_digital", "scanned", "mixed"})
APPLICABILITY_LEVELS = frozenset({"national", "state", "district", "area"})
STATE_CODES = frozenset(JURISDICTIONS - {"IN"})

VERIFICATION_WHAT = frozenset(
    {
        "status",
        "commencement",
        "validity",
        "text_matches_source",
        "consolidation_current",
        "interpretation",
    }
)
VERIFIERS = frozenset({"claude", "malik", "advocate"})
VERIFICATION_RESULTS = frozenset({"confirmed", "conflict", "unclear"})
# Checks only a human may sign off (DEC-040: legal interpretation needs Malik or an advocate).
HUMAN_ONLY_CHECKS = frozenset({"interpretation"})
# A document in mode=index needs a confirmed record for each of these.
INDEX_GATE_CHECKS = frozenset({"status", "commencement"})
# DEC-048: a draft has no commencement; proving it is the published draft is enough.
DRAFT_INDEX_GATE_CHECKS = frozenset({"status"})
# DEC-048 / DEC-052: statuses that can never commence, so status alone opens the index gate.
STATUS_ONLY_GATE_STATUSES = frozenset({"draft", "model_law"})

_INSTRUMENT_ID_RE = re.compile(r"^[A-Z]{2}\.[A-Z][A-Z0-9]*[0-9]{4}$")
_GATE_ID_RE = re.compile(r"^[A-Z][0-9]+$")  # OPEN_QUESTIONS IDs, e.g. L4, G12
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOC_ID_RE = re.compile(r"^[A-Za-z0-9._:@-]+$")


def _is_instrument_id(text: str) -> bool:
    return bool(_INSTRUMENT_ID_RE.match(text))


def _is_gate_id(text: str) -> bool:
    return bool(_GATE_ID_RE.match(text))


class ManifestError(ValueError):
    """Raised by :func:`load_manifest` with every validation error listed."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("invalid corpus manifest:\n- " + "\n- ".join(errors))
        self.errors = errors


# --------------------------------------------------------------------------- records


@dataclass(frozen=True, slots=True)
class Amendment:
    by: str  # amending instrument id (may be outside the corpus)
    commenced_on: date | None
    affects: tuple[str, ...]  # section_uids of this instrument


@dataclass(frozen=True, slots=True)
class CommencementOverride:
    uid: str
    commenced_on: date


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_id: str
    type: str
    jurisdiction: str
    title_en: str | None = None
    title_hi: str | None = None
    parent_instrument: str | None = None
    made_under: tuple[str, ...] = ()
    enacted_on: date | None = None
    commenced_on: date | None = None
    commencement_overrides: tuple[CommencementOverride, ...] = ()
    amendments: tuple[Amendment, ...] = ()
    supersedes: tuple[str, ...] = ()
    superseded_by: tuple[str, ...] = ()
    amends: tuple[str, ...] = ()  # DEC-044: instruments this one changes
    notes: str | None = None

    @property
    def authority_rank(self) -> int:
        return AUTHORITY_RANK[self.type]

    @property
    def binding(self) -> bool:
        return self.type in BINDING_TYPES


@dataclass(frozen=True, slots=True)
class AppliesTo:
    level: str
    states: tuple[str, ...] = ()
    districts: tuple[str, ...] = ()  # LGD codes (TODO(verify), OPEN_QUESTIONS)
    areas: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True, slots=True)
class AppliesToOverride:
    uid: str
    applies_to: AppliesTo


@dataclass(frozen=True, slots=True)
class Verification:
    what: str
    by: str
    on: date
    method: str
    evidence: str
    result: str
    note: str | None = None


@dataclass(frozen=True, slots=True)
class Document:
    doc_id: str
    instrument_id: str
    language: str
    status: str
    mode: str
    source_url: str
    publisher: str
    fetched_at: datetime
    sha256: str
    bytes: int
    content_type: str
    text_layer: str
    applies_to: AppliesTo
    gate: tuple[str, ...] = ()
    valid_from: date | None = None
    valid_to: date | None = None
    expires_on: date | None = None
    gazette_ref: str | None = None
    notification_no: str | None = None
    ocr_engine: str | None = None
    local_path: str | None = None
    s3_path: str | None = None
    applies_to_overrides: tuple[AppliesToOverride, ...] = ()
    verifications: tuple[Verification, ...] = ()
    last_checked_on: date | None = None
    supersedes: tuple[str, ...] = ()
    superseded_by: tuple[str, ...] = ()
    index_scope: tuple[str, ...] = ()
    notes: str | None = None

    def in_scope(self, uid: str) -> bool:
        """DEC-051: is this provision indexable? No scope = whole document."""
        return not self.index_scope or any(covers(s, uid) for s in self.index_scope)

    def is_current(self, on: date) -> bool:
        """Computed, never stored (DEC-040): in force and inside every validity window."""
        if self.status != "in_force":
            return False
        if self.valid_from is not None and on < self.valid_from:
            return False
        if self.valid_to is not None and on > self.valid_to:
            return False
        return self.expires_on is None or on <= self.expires_on

    def confirmed_checks(self) -> frozenset[str]:
        return frozenset(v.what for v in self.verifications if v.result == "confirmed")


@dataclass(frozen=True, slots=True)
class Manifest:
    schema_version: int
    instruments: dict[str, Instrument] = field(default_factory=dict)
    documents: dict[str, Document] = field(default_factory=dict)


# --------------------------------------------------------------------------- field readers


class _Reader:
    """Reads typed fields from one JSON object and records errors instead of raising."""

    def __init__(self, obj: Mapping[str, Any], where: str, errors: list[str], allowed: set[str]):
        self.obj, self.where, self.errors = obj, where, errors
        for key in sorted(set(obj) - allowed):
            self.err(f"unknown field {key!r}")

    def err(self, message: str) -> None:
        self.errors.append(f"{self.where}: {message}")

    def str_(self, key: str, *, required: bool = False) -> str | None:
        value = self.obj.get(key)
        if value is None:
            if required:
                self.err(f"missing {key!r}")
            return None
        if not isinstance(value, str) or not value.strip():
            self.err(f"{key!r} must be a non-empty string")
            return None
        return value

    def enum(self, key: str, allowed: frozenset[str], *, required: bool = True) -> str | None:
        value = self.str_(key, required=required)
        if value is not None and value not in allowed:
            self.err(f"{key!r}={value!r} not in {sorted(allowed)}")
            return None
        return value

    def date_(self, key: str, *, required: bool = False) -> date | None:
        value = self.str_(key, required=required)
        if value is None:
            return None
        try:
            if len(value) != 10:
                raise ValueError
            return date.fromisoformat(value)
        except ValueError:
            self.err(f"{key!r}={value!r} is not a YYYY-MM-DD date")
            return None

    def datetime_(self, key: str, *, required: bool = False) -> datetime | None:
        value = self.str_(key, required=required)
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            self.err(f"{key!r}={value!r} is not an ISO-8601 datetime")
            return None
        if parsed.tzinfo is None:
            self.err(f"{key!r} must include a timezone offset")
            return None
        return parsed

    def strs(self, key: str, check: Callable[[str], bool] | None = None) -> tuple[str, ...]:
        value = self.obj.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            self.err(f"{key!r} must be a list of strings")
            return ()
        if check is not None:
            for v in value:
                if not check(v):
                    self.err(f"{key!r} has invalid value {v!r}")
        return tuple(value)

    def objs(self, key: str) -> list[Mapping[str, Any]]:
        value = self.obj.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
            self.err(f"{key!r} must be a list of objects")
            return []
        return value

    def obj_(self, key: str) -> Mapping[str, Any] | None:
        value = self.obj.get(key)
        if not isinstance(value, dict):
            self.err(f"missing or invalid object {key!r}")
            return None
        return value

    def int_(self, key: str) -> int | None:
        value = self.obj.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            self.err(f"{key!r} must be a positive integer")
            return None
        return value


def _fields(cls: type[Any]) -> set[str]:
    return set(cls.__dataclass_fields__)


# --------------------------------------------------------------------------- parsers


def _parse_instrument(raw: Mapping[str, Any], idx: int, errors: list[str]) -> Instrument | None:
    iid = raw.get("instrument_id")
    r = _Reader(raw, f"instruments[{idx}] {iid!r}", errors, _fields(Instrument))
    instrument_id = r.str_("instrument_id", required=True)
    type_ = r.enum("type", INSTRUMENT_TYPES)
    jurisdiction = r.enum("jurisdiction", JURISDICTIONS)
    title_en, title_hi = r.str_("title_en"), r.str_("title_hi")
    if title_en is None and title_hi is None:
        r.err("needs at least one of title_en / title_hi")
    if instrument_id is not None:
        if not _INSTRUMENT_ID_RE.match(instrument_id) or not is_valid(instrument_id):
            r.err(f"bad instrument_id {instrument_id!r} (want e.g. 'IN.RTI2005')")
        elif jurisdiction is not None and not instrument_id.startswith(jurisdiction + "."):
            r.err("instrument_id prefix must match jurisdiction")

    parent_instrument = r.str_("parent_instrument")
    made_under = r.strs("made_under", is_valid)
    if made_under and parent_instrument is None:
        r.err("made_under needs parent_instrument")
    for uid in made_under:
        if (
            parent_instrument is not None
            and is_valid(uid)
            and not belongs_to(uid, parent_instrument)
        ):
            r.err(f"made_under {uid!r} is not a provision of {parent_instrument!r}")

    overrides: list[CommencementOverride] = []
    for j, o in enumerate(r.objs("commencement_overrides")):
        sub = _Reader(o, f"{r.where}.commencement_overrides[{j}]", errors, {"uid", "commenced_on"})
        o_uid = sub.str_("uid", required=True)
        o_on = sub.date_("commenced_on", required=True)
        if o_uid is not None and instrument_id is not None and not _uid_in(o_uid, instrument_id):
            sub.err(f"uid {o_uid!r} is not a provision of {instrument_id!r}")
        elif o_uid is not None and o_on is not None:
            overrides.append(CommencementOverride(o_uid, o_on))

    amendments: list[Amendment] = []
    for j, a in enumerate(r.objs("amendments")):
        sub = _Reader(a, f"{r.where}.amendments[{j}]", errors, _fields(Amendment))
        by = sub.str_("by", required=True)
        if by is not None and not _INSTRUMENT_ID_RE.match(by):
            sub.err(f"'by'={by!r} is not an instrument id")
        affects = sub.strs("affects")
        for uid in affects:
            if instrument_id is not None and not _uid_in(uid, instrument_id):
                sub.err(f"affects {uid!r} is not a provision of {instrument_id!r}")
        if by is not None:
            amendments.append(Amendment(by, sub.date_("commenced_on"), affects))

    enacted_on, commenced_on = r.date_("enacted_on"), r.date_("commenced_on")
    if type_ == "model_law" and commenced_on is not None:
        r.err("a model_law instrument cannot have commenced_on (DEC-052)")
    if enacted_on and commenced_on and commenced_on < enacted_on:
        r.err("commenced_on is before enacted_on")

    supersedes = r.strs("supersedes", _is_instrument_id)
    superseded_by = r.strs("superseded_by", _is_instrument_id)
    amends = r.strs("amends", _is_instrument_id)
    if instrument_id is not None and instrument_id in amends:
        r.err("an instrument cannot amend itself")
    notes = r.str_("notes")
    if instrument_id is None or type_ is None or jurisdiction is None:
        return None
    return Instrument(
        instrument_id=instrument_id,
        type=type_,
        jurisdiction=jurisdiction,
        title_en=title_en,
        title_hi=title_hi,
        parent_instrument=parent_instrument,
        made_under=made_under,
        enacted_on=enacted_on,
        commenced_on=commenced_on,
        commencement_overrides=tuple(overrides),
        amendments=tuple(amendments),
        supersedes=supersedes,
        superseded_by=superseded_by,
        amends=amends,
        notes=notes,
    )


def _uid_in(uid: str, instrument_id: str) -> bool:
    return is_valid(uid) and belongs_to(uid, instrument_id) and uid != instrument_id


def _parse_applies_to(raw: Mapping[str, Any], where: str, errors: list[str]) -> AppliesTo | None:
    r = _Reader(raw, where, errors, _fields(AppliesTo))
    level = r.enum("level", APPLICABILITY_LEVELS)
    states = r.strs("states", STATE_CODES.__contains__)
    districts, areas = r.strs("districts"), r.strs("areas")
    if level == "national" and (states or districts or areas):
        r.err("national applicability takes no states/districts/areas")
    if level in {"state", "district", "area"} and not states:
        r.err(f"{level} applicability needs 'states'")
    if level == "district" and not districts:
        r.err("district applicability needs 'districts'")
    if level == "area" and not areas:
        r.err("area applicability needs 'areas'")
    if level is None:
        return None
    return AppliesTo(level, states, districts, areas, r.str_("note"))


def _parse_verification(
    raw: Mapping[str, Any], where: str, errors: list[str]
) -> Verification | None:
    r = _Reader(raw, where, errors, _fields(Verification))
    what = r.enum("what", VERIFICATION_WHAT)
    by = r.enum("by", VERIFIERS)
    on = r.date_("on", required=True)
    method = r.str_("method", required=True)
    evidence = r.str_("evidence", required=True)
    result = r.enum("result", VERIFICATION_RESULTS)
    note = r.str_("note")
    if what in HUMAN_ONLY_CHECKS and by == "claude":
        r.err(f"{what!r} checks must be done by malik or advocate, not claude")
        return None
    if what is None or by is None or on is None or method is None:
        return None
    if evidence is None or result is None:
        return None
    return Verification(what, by, on, method, evidence, result, note)


def _parse_document(raw: Mapping[str, Any], idx: int, errors: list[str]) -> Document | None:
    did = raw.get("doc_id")
    where = f"documents[{idx}] {did!r}"
    r = _Reader(raw, where, errors, _fields(Document))
    doc_id = r.str_("doc_id", required=True)
    instrument_id = r.str_("instrument_id", required=True)
    if doc_id is not None:
        if not _DOC_ID_RE.match(doc_id):
            r.err(f"bad doc_id {doc_id!r}")
        elif instrument_id is not None and not doc_id.startswith(instrument_id + "@"):
            r.err("doc_id must start with '<instrument_id>@'")

    language = r.enum("language", DOC_LANGUAGES)
    status = r.enum("status", STATUSES)
    mode = r.enum("mode", MODES)
    gate = r.strs("gate", _is_gate_id)
    if mode == "gated" and not gate:
        r.err("mode=gated needs at least one 'gate' id (OPEN_QUESTIONS)")
    if mode != "gated" and gate:
        r.err("'gate' is only allowed with mode=gated")

    source_url = r.str_("source_url", required=True)
    if source_url is not None and not source_url.startswith(("https://", "http://")):
        r.err("source_url must be http(s)")
    publisher = r.str_("publisher", required=True)
    fetched_at = r.datetime_("fetched_at", required=True)
    sha256 = r.str_("sha256", required=True)
    if sha256 is not None and not _SHA256_RE.match(sha256):
        r.err("sha256 must be 64 lowercase hex characters")
    size = r.int_("bytes")
    content_type = r.str_("content_type", required=True)

    text_layer = r.enum("text_layer", TEXT_LAYERS)
    ocr_engine = r.str_("ocr_engine")
    if text_layer == "born_digital" and ocr_engine is not None:
        r.err("born_digital documents have no ocr_engine")

    valid_from, valid_to = r.date_("valid_from"), r.date_("valid_to")
    expires_on = r.date_("expires_on")
    if valid_from and valid_to and valid_to < valid_from:
        r.err("valid_to is before valid_from")
    if valid_from and expires_on and expires_on < valid_from:
        r.err("expires_on is before valid_from")

    s3_path = r.str_("s3_path")
    if s3_path is not None and not s3_path.startswith("s3://"):
        r.err("s3_path must start with s3://")
    local_path = r.str_("local_path")
    if local_path is not None and (local_path.startswith(("/", "\\")) or ":" in local_path):
        r.err("local_path must be relative to the data dir")

    applies_raw = r.obj_("applies_to")
    applies_to = (
        _parse_applies_to(applies_raw, f"{where}.applies_to", errors) if applies_raw else None
    )
    overrides: list[AppliesToOverride] = []
    for j, o in enumerate(r.objs("applies_to_overrides")):
        sub = _Reader(o, f"{where}.applies_to_overrides[{j}]", errors, {"uid", "applies_to"})
        uid = sub.str_("uid", required=True)
        if uid is not None and instrument_id is not None and not _uid_in(uid, instrument_id):
            sub.err(f"uid {uid!r} is not a provision of {instrument_id!r}")
            uid = None
        inner = sub.obj_("applies_to")
        parsed = _parse_applies_to(inner, f"{sub.where}.applies_to", errors) if inner else None
        if uid is not None and parsed is not None:
            overrides.append(AppliesToOverride(uid, parsed))

    verifications: list[Verification] = []
    for j, v in enumerate(r.objs("verifications")):
        parsed_v = _parse_verification(v, f"{where}.verifications[{j}]", errors)
        if parsed_v is not None:
            verifications.append(parsed_v)

    if mode == "index":
        confirmed = {v.what for v in verifications if v.result == "confirmed"}
        required_checks = (
            DRAFT_INDEX_GATE_CHECKS if status in STATUS_ONLY_GATE_STATUSES else INDEX_GATE_CHECKS
        )
        missing = sorted(required_checks - confirmed)
        if missing:
            r.err(
                f"mode=index needs confirmed verification of {missing} (DEC-040/DEC-048 index gate)"
            )
        if any(v.result == "conflict" for v in verifications):
            r.err("mode=index is not allowed while a verification has result=conflict")

    supersedes, superseded_by = r.strs("supersedes"), r.strs("superseded_by")
    index_scope = _parse_index_scope(r, instrument_id)
    gazette_ref, notification_no = r.str_("gazette_ref"), r.str_("notification_no")
    last_checked_on, notes = r.date_("last_checked_on"), r.str_("notes")
    if (
        doc_id is None
        or instrument_id is None
        or language is None
        or status is None
        or mode is None
        or source_url is None
        or publisher is None
        or fetched_at is None
        or sha256 is None
        or size is None
        or content_type is None
        or text_layer is None
        or applies_to is None
    ):
        return None
    return Document(
        doc_id=doc_id,
        instrument_id=instrument_id,
        language=language,
        status=status,
        mode=mode,
        source_url=source_url,
        publisher=publisher,
        fetched_at=fetched_at,
        sha256=sha256,
        bytes=size,
        content_type=content_type,
        text_layer=text_layer,
        applies_to=applies_to,
        gate=gate,
        valid_from=valid_from,
        valid_to=valid_to,
        expires_on=expires_on,
        gazette_ref=gazette_ref,
        notification_no=notification_no,
        ocr_engine=ocr_engine,
        local_path=local_path,
        s3_path=s3_path,
        applies_to_overrides=tuple(overrides),
        verifications=tuple(verifications),
        last_checked_on=last_checked_on,
        supersedes=supersedes,
        superseded_by=superseded_by,
        index_scope=index_scope,
        notes=notes,
    )


def _parse_index_scope(r: _Reader, instrument_id: str | None) -> tuple[str, ...]:
    """DEC-051: optional list of provisions to index; each must be a distinct, non-nested uid."""
    if "index_scope" not in r.obj:
        return ()
    scope = r.strs("index_scope")
    if not scope:
        r.err("index_scope, when present, must be a non-empty list of section_uids")
        return ()
    for uid in scope:
        if instrument_id is not None and not _uid_in(uid, instrument_id):
            r.err(f"index_scope uid {uid!r} is not a provision of {instrument_id!r}")
    if len(set(scope)) != len(scope):
        r.err("index_scope has duplicate uids")
    for a in scope:
        for b in scope:
            if a != b and covers(a, b):
                r.err(f"index_scope uid {b!r} is already covered by {a!r}")
    return scope


def parse_manifest(data: object) -> tuple[Manifest | None, list[str]]:
    """Validate a decoded manifest. Returns (manifest or None, every error found)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return None, ["manifest must be a JSON object"]
    top = _Reader(data, "manifest", errors, {"schema_version", "instruments", "documents"})
    if data.get("schema_version") != SCHEMA_VERSION:
        top.err(f"schema_version must be {SCHEMA_VERSION}")

    instruments: dict[str, Instrument] = {}
    for i, raw in enumerate(top.objs("instruments")):
        inst = _parse_instrument(raw, i, errors)
        if inst is None:
            continue
        if inst.instrument_id in instruments:
            errors.append(f"duplicate instrument_id {inst.instrument_id!r}")
        instruments[inst.instrument_id] = inst

    documents: dict[str, Document] = {}
    for i, raw in enumerate(top.objs("documents")):
        doc = _parse_document(raw, i, errors)
        if doc is None:
            continue
        if doc.doc_id in documents:
            errors.append(f"duplicate doc_id {doc.doc_id!r}")
        documents[doc.doc_id] = doc

    _check_cross_references(instruments, documents, errors)
    if errors:
        return None, errors
    return Manifest(SCHEMA_VERSION, instruments, documents), []


def _check_cross_references(
    instruments: dict[str, Instrument], documents: dict[str, Document], errors: list[str]
) -> None:
    for inst in instruments.values():
        if inst.parent_instrument is not None and inst.parent_instrument not in instruments:
            errors.append(
                f"{inst.instrument_id}: unknown parent_instrument {inst.parent_instrument!r}"
            )
        for ref in (*inst.supersedes, *inst.superseded_by):
            if ref not in instruments:
                errors.append(f"{inst.instrument_id}: unknown instrument {ref!r} in supersession")
    for doc in documents.values():
        owner = instruments.get(doc.instrument_id)
        if owner is None:
            errors.append(f"{doc.doc_id}: unknown instrument_id {doc.instrument_id!r}")
            continue
        if doc.status == "enacted_not_commenced" and owner.commenced_on is not None:
            errors.append(
                f"{doc.doc_id}: instrument has commenced_on {owner.commenced_on}; "
                "update status from enacted_not_commenced (DEC-044)"
            )
        if owner.type == "model_law" and doc.status != "model_law":
            errors.append(
                f"{doc.doc_id}: documents of a model_law instrument need status model_law"
            )
        if owner.jurisdiction != "IN" and doc.applies_to.level == "national":
            errors.append(
                f"{doc.doc_id}: a {owner.jurisdiction} instrument cannot apply nationally"
            )
        if owner.jurisdiction != "IN" and owner.jurisdiction not in doc.applies_to.states:
            errors.append(f"{doc.doc_id}: applies_to.states must include {owner.jurisdiction}")
        if doc.mode == "guide" and owner.type not in {"official_guide", "scheme_guideline"}:
            errors.append(f"{doc.doc_id}: mode=guide is only for official_guide/scheme_guideline")
        if doc.mode == "index" and owner.type == "official_guide":
            errors.append(f"{doc.doc_id}: official guides use mode=guide, not index (DEC-037)")
        for ref in (*doc.supersedes, *doc.superseded_by):
            if ref not in documents:
                errors.append(f"{doc.doc_id}: unknown document {ref!r} in supersession")


def load_manifest(path: Path) -> Manifest:
    """Read and validate a manifest file. Raises ManifestError listing every problem."""
    manifest, errors = parse_manifest(json.loads(path.read_text(encoding="utf-8")))
    if manifest is None:
        raise ManifestError(errors)
    return manifest
