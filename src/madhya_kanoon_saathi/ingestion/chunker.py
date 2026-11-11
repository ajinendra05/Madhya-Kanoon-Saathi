"""Chunks from a parsed statute (DEC-055). Spec: ``docs/specs/chunks.md``.

A chunk is one sub-section (with its provisos and explanations), or a whole section when it has no
sub-sections. Repealed sections are not chunked. A chunk over ``MAX_TOKENS`` is split into its
direct children (clauses, provisos), each keeping its own deeper ``section_uid``; a single unit
that is still too long is cut by lines into ``~n`` parts.

Text (DEC-055 7a, DEC-054):
- ``raw_text`` = the unit lines joined with ``\\n`` exactly as extracted;
- ``raw_map`` = ``{"markers": [[start, end], ...], "breaks": [offset, ...]}`` (footnote marker spans
  and the newlines that are paragraph breaks, as offsets into ``raw_text``);
- ``text`` = ``canonicalise(raw_text, raw_map)``: markers dropped, paragraph breaks kept as
  ``\\n``, other line wraps joined (no space after a line-final hyphen), DEC-054 normaliser.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from madhya_kanoon_saathi.common.normalize import normalize
from madhya_kanoon_saathi.common.section_uid import covers, is_valid, make_chunk_id, parent
from madhya_kanoon_saathi.ingestion.manifest import AppliesTo, Document, Instrument
from madhya_kanoon_saathi.ingestion.pdf_text import Footnote, Line
from madhya_kanoon_saathi.ingestion.structure import Parsed, Unit

CHUNKER_VERSION = "2"  # 2: U+FFFE from pdfium read as a hyphen (IN.SVANSG2025 p.4 "non-NPA")
MIN_TOKENS, MAX_TOKENS = 150, 450
_SPACES = re.compile(r"[ \t]+")


def token_estimate(text: str, lang: str) -> int:
    """Rough token count until the BGE-M3 tokenizer is wired in (W1.4): 1.35/word en, 2/word hi."""
    return math.ceil(len(text.split()) * (2.0 if lang == "hi" else 1.35))


def canonicalise(raw_text: str, raw_map: dict[str, list[Any]]) -> str:
    """Canonical text from raw text + map (pure; the QA check re-runs it on every chunk)."""
    skip = sorted(
        (int(a), int(b)) for a, b in [*raw_map.get("markers", []), *raw_map.get("skips", [])]
    )
    breaks = {int(x) for x in raw_map.get("breaks", [])}
    out: list[str] = []
    i, k = 0, 0
    while i < len(raw_text):
        if k < len(skip) and i == skip[k][0]:
            i = skip[k][1]
            k += 1
            continue
        ch = raw_text[i]
        if ch == "\n":
            if i in breaks:
                out.append("\n")
            elif out and out[-1].endswith("-"):
                pass  # "sub-" + "section" -> "sub-section"
            else:
                out.append(" ")
        else:
            out.append(ch)
        i += 1
    text = normalize("".join(out).replace("\ufffe", "-"), fold_nukta=False)
    paras = [_SPACES.sub(" ", p).strip() for p in text.split("\n")]
    return "\n".join(p for p in paras if p)


@dataclass
class Chunk:
    chunk_id: str
    section_uid: str
    parent_uid: str | None
    instrument_id: str
    doc_id: str
    jurisdiction: str
    lang: str
    version: str
    version_source: str
    text: str
    raw_text: str
    raw_map: dict[str, list[Any]]
    heading: str
    path: list[str]
    footnotes: list[dict[str, str]]
    locator: dict[str, Any]
    source_url: str
    doc_sha256: str
    extraction: str
    status: str
    doc_type: str
    valid_from: str | None
    valid_to: str | None
    expires_on: str | None
    applies_to: dict[str, Any]
    token_estimate: int

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BuildResult:
    chunks: list[Chunk] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # hard QA failures (DEC-055 7e)
    warnings: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # repealed / out of scope units


def _version(uid: str, doc: Document, inst: Instrument) -> tuple[str, str]:
    """DEC-055 7d chain as amended by DEC-056; returns (version, version_source)."""
    if doc.valid_from:
        return doc.valid_from.isoformat(), "valid_from"
    best: date | None = None
    best_len = -1
    for ov in inst.commencement_overrides:
        if covers(ov.uid, uid) and len(ov.uid) > best_len:
            best, best_len = ov.commenced_on, len(ov.uid)
    if best is not None:
        return best.isoformat(), "commencement_override"
    # DEC-056: the latest amendment whose affected provision overlaps this chunk
    amended = [
        a.commenced_on
        for a in inst.amendments
        if a.commenced_on and any(covers(x, uid) or covers(uid, x) for x in a.affects)
    ]
    if amended:
        return max(amended).isoformat(), "amendment"
    if inst.commenced_on:
        return inst.commenced_on.isoformat(), "commenced_on"
    if inst.enacted_on:
        return inst.enacted_on.isoformat(), "enacted_on"
    return f"nd-{doc.sha256[:8]}", "doc_sha256"


def _applies(uid: str, doc: Document) -> dict[str, Any]:
    best: AppliesTo = doc.applies_to
    best_len = -1
    for ov in doc.applies_to_overrides:
        if covers(ov.uid, uid) and len(ov.uid) > best_len:
            best, best_len = ov.applies_to, len(ov.uid)
    d = asdict(best)
    return {
        k: (list(v) if isinstance(v, tuple) else v) for k, v in d.items() if v not in ((), None)
    }


def _subtree(units: Sequence[Unit], root: Unit) -> list[Unit]:
    pre = root.uid + ":"
    return [root] + [u for u in units if u.uid.startswith(pre)]


def _assemble(
    parts: Sequence[Unit], prefix: Sequence[Line] = ()
) -> tuple[str, dict[str, list[Any]], list[Line]]:
    """Join unit lines into raw text; record marker spans and paragraph breaks (new unit starts)."""
    raw: list[str] = []
    markers: list[list[int]] = []
    skips: list[list[int]] = []
    breaks: list[int] = []
    all_lines: list[Line] = []
    pos = 0
    groups: list[list[Line]] = [list(prefix)] if prefix else []
    groups += [list(u.lines) for u in parts]
    first = True
    for gi, group in enumerate(groups):
        for li, ln in enumerate(group):
            if not first:
                if li == 0 and gi > 0:
                    breaks.append(pos)
                raw.append("\n")
                pos += 1
            first = False
            markers += [[pos + a, pos + b] for a, b in ln.markers]
            skips += [[pos + a, pos + b] for a, b in ln.skips]
            raw.append(ln.text)
            pos += len(ln.text)
            all_lines.append(ln)
    rmap: dict[str, list[Any]] = {"markers": markers, "breaks": breaks}
    if skips:
        rmap["skips"] = skips
    return "".join(raw), rmap, all_lines


def build_chunks(
    parsed: Parsed,
    doc: Document,
    inst: Instrument,
    footnotes: Iterable[Footnote],
    extraction: str,
    lang: str = "en",
) -> BuildResult:
    res = BuildResult()
    fn_by_key = {(f.page, f.n): f for f in footnotes}
    units = parsed.units
    sections = [u for u in units if u.kind in ("section", "schedule")]

    def emit(
        uid: str,
        parts: Sequence[Unit],
        sec: Unit,
        prefix: Sequence[Line] = (),
        part: int | None = None,
    ) -> None:
        if not is_valid(uid) or not uid.startswith(doc.instrument_id + ":"):
            res.errors.append(f"{doc.doc_id}: invalid section_uid {uid}")
            return
        if not doc.in_scope(uid):
            res.skipped.append(f"{uid} (outside index_scope)")
            return
        raw_text, raw_map, lines = _assemble(parts, prefix)
        if not raw_text.strip():
            return
        text = canonicalise(raw_text, raw_map)
        pages = sorted({ln.page for ln in lines})
        notes: list[dict[str, str]] = []
        for a, b in raw_map["markers"]:
            label = raw_text[a:b]
            page = _page_at(lines, raw_text, a)
            fn = fn_by_key.get((page, label))
            if fn is None:
                res.warnings.append(
                    f"{uid}: footnote marker {label!r} on p.{page} has no footnote text"
                )
            elif all(n["n"] != label or n["page"] != str(page) for n in notes):
                notes.append(
                    {"n": label, "page": str(page), "text": normalize(fn.text, fold_nukta=False)}
                )
        version, vsrc = _version(uid, doc, inst)
        heading = normalize(sec.heading, fold_nukta=False)
        path = [
            p
            for p in (
                sec.chapter,
                f"{sec.label}. {heading}" if sec.kind == "section" else sec.label,
            )
            if p
        ]
        res.chunks.append(
            Chunk(
                chunk_id=make_chunk_id(
                    uid,
                    lang,
                    date.fromisoformat(version) if vsrc != "doc_sha256" else version,
                    part,
                ),
                section_uid=uid,
                parent_uid=parent(uid),
                instrument_id=doc.instrument_id,
                doc_id=doc.doc_id,
                jurisdiction=inst.jurisdiction,
                lang=lang,
                version=version,
                version_source=vsrc,
                text=text,
                raw_text=raw_text,
                raw_map=raw_map,
                heading=heading,
                path=path,
                footnotes=notes,
                locator={"kind": "pdf_page", "pages": [pages[0], pages[-1]]} if pages else {},
                source_url=doc.source_url,
                doc_sha256=doc.sha256,
                extraction=extraction,
                status=doc.status,
                doc_type=inst.type,
                valid_from=doc.valid_from.isoformat() if doc.valid_from else None,
                valid_to=doc.valid_to.isoformat() if doc.valid_to else None,
                expires_on=doc.expires_on.isoformat() if doc.expires_on else None,
                applies_to=_applies(uid, doc),
                token_estimate=token_estimate(text, lang),
            )
        )

    def emit_tree(root: Unit, sec: Unit, prefix: Sequence[Line] = ()) -> None:
        """Emit root with all descendants; split into direct children when too long."""
        tree = _subtree(units, root)
        raw, rmap, _ = _assemble(tree, prefix)
        if token_estimate(canonicalise(raw, rmap), lang) <= MAX_TOKENS:
            emit(root.uid, tree, sec, prefix)
            return
        kids = [u for u in tree[1:] if parent(u.uid) == root.uid]
        if not kids:
            _emit_long_leaf(root, sec, prefix)
            return
        # the unit's own lines (intro / heading), size-limited like any leaf
        own_raw, own_map, _ = _assemble([root], prefix)
        if token_estimate(canonicalise(own_raw, own_map), lang) > MAX_TOKENS:
            _emit_long_leaf(root, sec, prefix)
        else:
            emit(root.uid, [root], sec, prefix)
        for kid in kids:
            emit_tree(kid, sec)

    def _emit_long_leaf(root: Unit, sec: Unit, prefix: Sequence[Line]) -> None:
        all_lines = list(prefix) + list(root.lines)
        piece: list[Line] = []
        part = 1
        for ln in all_lines:
            if piece and token_estimate(" ".join(x.text for x in [*piece, ln]), lang) > MAX_TOKENS:
                emit(
                    root.uid,
                    [Unit(root.uid, root.kind, root.label, lines=piece)],
                    sec,
                    part=None if part == 1 else part,
                )
                piece, part = [], part + 1
            piece.append(ln)
        if piece:
            emit(
                root.uid,
                [Unit(root.uid, root.kind, root.label, lines=piece)],
                sec,
                part=None if part == 1 else part,
            )

    for sec in sections:
        if sec.repealed:
            res.skipped.append(f"{sec.uid} (repealed in text)")
            continue
        if sec.kind == "schedule" and sec.para_restart:
            # numbering restarts inside the schedule (Part A / Part B): one uid, size-split pieces
            whole = [ln for u in _subtree(units, sec) for ln in u.lines]
            _emit_long_leaf(Unit(sec.uid, sec.kind, sec.label, lines=whole), sec, ())
            continue
        children = [u for u in units if parent(u.uid) == sec.uid]
        subs = [u for u in children if u.kind == "ss"]
        if not subs:
            emit_tree(sec, sec)
            continue
        others = [u for u in children if u.kind != "ss"]  # section-level provisos/explanations
        for i, ss in enumerate(subs):
            emit_tree(ss, sec, prefix=sec.lines if i == 0 else ())
        for o in others:
            emit_tree(o, sec)
    return res


def _page_at(lines: Sequence[Line], raw_text: str, offset: int) -> int:
    pos = 0
    for ln in lines:
        end = pos + len(ln.text)
        if offset <= end:
            return ln.page
        pos = end + 1
    return lines[-1].page


def qa(result: BuildResult, page_chars: dict[int, int] | None = None) -> BuildResult:
    """Run DEC-055 7e checks on built chunks; appends to result.errors / result.warnings."""
    seen: set[str] = set()
    for c in result.chunks:
        if c.chunk_id in seen:
            result.errors.append(f"duplicate chunk_id {c.chunk_id}")
        seen.add(c.chunk_id)
        if not c.locator or not c.locator.get("pages"):
            result.errors.append(f"{c.chunk_id}: missing locator")
        if canonicalise(c.raw_text, c.raw_map) != c.text:
            result.errors.append(f"{c.chunk_id}: raw/canonical mismatch")
        if any(0xFDD0 <= ord(ch) <= 0xFDEF or (ord(ch) & 0xFFFE) == 0xFFFE for ch in c.text):
            result.errors.append(f"{c.chunk_id}: Unicode non-character in canonical text")
        if not (MIN_TOKENS <= c.token_estimate <= MAX_TOKENS):
            result.warnings.append(
                f"{c.chunk_id}: token_estimate {c.token_estimate} outside {MIN_TOKENS}-{MAX_TOKENS}"
            )
        if re.search(r"\b(sub -section|\( \d)", c.text):
            result.warnings.append(f"{c.chunk_id}: suspected split words")
    for page, n in sorted((page_chars or {}).items()):
        if 0 < n < 200:
            result.warnings.append(f"p.{page}: only {n} characters of text")
    return result
