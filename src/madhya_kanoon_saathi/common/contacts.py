"""Escalation contacts with official sources (DEC-018). Data: ``data/contacts.yaml``.

The file is written in JSON syntax (JSON is valid YAML 1.2), so it is read with the standard
library and no YAML dependency is needed. Every contact carries one or more official ``sources``;
each source names the saved page (``file``, under ``data/``), its ``sha256`` and an exact
``quote`` from the page text that contains the number. A number may be shown to users only if its
contact validates and every source quote is found in the saved page (:func:`check_sources`).
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PURPOSES = frozenset(
    {
        "emergency",  # police / fire / ambulance (ERSS)
        "women_helpline",
        "child_helpline",
        "cybercrime",
        "mental_health",
        "legal_aid",  # statutory free legal aid only (BCI Rule 36: never private lawyers)
        "grievance",  # public-service grievance routes (not crisis numbers)
    }
)
SCOPES = frozenset({"IN", "MP"})
_FIELDS = {"id", "number", "name_en", "name_hi", "scope", "purpose", "verified_on", "verified_by"}
_SOURCE_FIELDS = {"url", "file", "sha256", "fetched_on", "quote"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NUMBER = re.compile(r"^\d{3,5}$|^1800-\d{3}-\d{4}$")


@dataclass(frozen=True)
class Source:
    url: str
    file: str
    sha256: str
    fetched_on: str
    quote: str


@dataclass(frozen=True)
class Contact:
    id: str
    number: str
    name_en: str
    name_hi: str | None
    scope: str
    purpose: tuple[str, ...]
    verified_on: str
    verified_by: str
    sources: tuple[Source, ...]


def page_text(data: bytes) -> str:
    """Visible text of a saved HTML page: scripts/styles and tags dropped, entities decoded,
    whitespace collapsed, NFC. Quotes are compared against this."""
    t = data.decode("utf-8", errors="replace")
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", t)).strip()


def validate(data: Any) -> list[str]:
    """Schema errors in the parsed contacts file (empty list = valid)."""
    errs: list[str] = []
    contacts = data.get("contacts") if isinstance(data, dict) else None
    if not isinstance(contacts, list) or not contacts:
        return ["'contacts' must be a non-empty list"]
    seen: set[str] = set()
    for c in contacts:
        cid = c.get("id", "?") if isinstance(c, dict) else "?"
        if not isinstance(c, dict) or set(c) != _FIELDS | {"sources"}:
            errs.append(f"{cid}: fields must be exactly {sorted(_FIELDS | {'sources'})}")
            continue
        if cid in seen:
            errs.append(f"{cid}: duplicate id")
        seen.add(cid)
        if not _NUMBER.match(str(c["number"])):
            errs.append(f"{cid}: bad number {c['number']!r}")
        if c["scope"] not in SCOPES:
            errs.append(f"{cid}: scope must be one of {sorted(SCOPES)}")
        if not c["purpose"] or not set(c["purpose"]) <= PURPOSES:
            errs.append(f"{cid}: purpose must be a non-empty subset of {sorted(PURPOSES)}")
        if not _DATE.match(str(c["verified_on"])) or c["verified_by"] not in ("claude", "malik"):
            errs.append(f"{cid}: verified_on (YYYY-MM-DD) and verified_by (claude|malik) needed")
        if not c["sources"]:
            errs.append(f"{cid}: at least one official source is required (DEC-018)")
        for s in c["sources"]:
            if not isinstance(s, dict) or set(s) != _SOURCE_FIELDS:
                errs.append(f"{cid}: source fields must be exactly {sorted(_SOURCE_FIELDS)}")
                continue
            if str(c["number"]) not in s["quote"]:
                errs.append(f"{cid}: quote does not contain the number {c['number']}")
            if not re.fullmatch(r"[0-9a-f]{64}", s["sha256"]):
                errs.append(f"{cid}: source sha256 missing (run scripts/fetch_contacts.py)")
            if not str(s["url"]).startswith("https://"):
                errs.append(f"{cid}: source url must be https")
    return errs


def load(path: Path) -> list[Contact]:
    """Parse and validate the contacts file; raises ValueError listing all problems."""
    data = json.loads(path.read_text(encoding="utf-8"))
    errs = validate(data)
    if errs:
        raise ValueError("contacts invalid:\n  " + "\n  ".join(errs))
    return [
        Contact(
            id=c["id"],
            number=str(c["number"]),
            name_en=c["name_en"],
            name_hi=c["name_hi"],
            scope=c["scope"],
            purpose=tuple(c["purpose"]),
            verified_on=c["verified_on"],
            verified_by=c["verified_by"],
            sources=tuple(Source(**s) for s in c["sources"]),
        )
        for c in data["contacts"]
    ]


def check_sources(contact: Contact, data_dir: Path) -> list[str]:
    """Errors if a saved source page is missing, changed, or lacks its quote."""
    errs: list[str] = []
    for s in contact.sources:
        f = data_dir / s.file
        if not f.is_file():
            errs.append(f"{contact.id}: saved source missing: {s.file}")
            continue
        data = f.read_bytes()
        if hashlib.sha256(data).hexdigest() != s.sha256:
            errs.append(f"{contact.id}: {s.file} differs from the recorded sha256")
        if unicodedata.normalize("NFC", s.quote) not in page_text(data):
            errs.append(f"{contact.id}: quote not found in {s.file}: {s.quote!r}")
    return errs
