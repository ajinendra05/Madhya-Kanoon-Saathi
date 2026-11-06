"""Polite, resumable corpus downloader (DEC-011, DEC-041).

Input: ``data/corpus_sources.json`` (what to fetch). Output: files under ``<data dir>/raw/``
plus document rows in ``data/corpus_manifest.json``.

Safety rules:
- A newly fetched document enters the manifest with ``mode="archive"``. Its intended mode stays
  in the sources file as ``target_mode``; promotion to ``index`` is a separate, manual step that
  needs the DEC-040 verification records. The downloader can never put unverified law in the index.
- Idempotent: a document whose local file still matches the manifest sha256 is skipped.
- If the server now returns different bytes, the new copy is saved as ``*.new`` and reported as
  CHANGED; the manifest row is **not** updated (a human reviews law changes, DEC-013).
- Downloads go to a temp file and are renamed when complete, so a crash leaves no half files.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import http.cookiejar
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from madhya_kanoon_saathi.ingestion.manifest import MODES, parse_manifest

# Generic project identity, never a personal email (.claude/rules/ingestion.md). Kept short: on
# 2026-11-06 India Code returned 403 for UAs containing "fetcher" or a URL, but 200 for this one.
USER_AGENT = "MadhyaKanoonSaathi/0.1"
DEFAULT_DELAY_S = 3.0
TIMEOUT_S = 60.0
RETRIES = 3
# A page with at least this many non-space characters of extractable text counts as a text page.
MIN_TEXT_CHARS_PER_PAGE = 30
# Scanner apps often embed a Latin-only OCR layer in Hindi scans (seen 2026-11-06 in the MP Labour
# notification 6445-6650: 0% Devanagari). For Hindi text to count, this share of letters must be
# Devanagari; otherwise the page is treated as having no usable text.
MIN_DEVANAGARI_SHARE = {"hi": 0.5, "bi": 0.2}

# Fields a sources row copies into the manifest document as-is.
_COPIED_FIELDS = (
    "instrument_id",
    "language",
    "status",
    "source_url",
    "publisher",
    "applies_to",
    "gazette_ref",
    "notification_no",
    "valid_from",
    "valid_to",
    "expires_on",
    "notes",
)
_SOURCE_FIELDS = {"doc_id", "url", "resolver", "target_mode", "gate", *_COPIED_FIELDS} - {
    "source_url"
}

Downloader = Callable[[str], tuple[bytes, str]]


@dataclass(frozen=True, slots=True)
class FetchResult:
    doc_id: str
    outcome: str  # added | skipped | changed | error
    detail: str = ""


# --------------------------------------------------------------------------- pure helpers


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _usable_chars(text: str, language: str | None) -> int:
    chars = "".join(text.split())
    min_share = MIN_DEVANAGARI_SHARE.get(language or "")
    if min_share is not None:
        letters = [c for c in chars if c.isalpha()]
        devanagari = sum("ऀ" <= c <= "ॿ" for c in letters)
        if letters and devanagari / len(letters) < min_share:
            return 0
    return len(chars)


def detect_text_layer(data: bytes, content_type: str, language: str | None = None) -> str:
    """born_digital / scanned / mixed for PDFs (via pypdf); other content types are born_digital.

    "scanned" means "no *usable* text layer": for Hindi documents, a page whose extracted text is
    mostly non-Devanagari (a bad embedded OCR layer or legacy font) counts as having no text.
    """
    if "pdf" not in content_type and not data.startswith(b"%PDF"):
        return "born_digital"
    try:
        reader = PdfReader(io.BytesIO(data))
        counts = [_usable_chars(page.extract_text() or "", language) for page in reader.pages]
    except (PdfReadError, ValueError, KeyError) as exc:
        raise ValueError(f"unreadable PDF: {exc}") from exc
    if not counts:
        raise ValueError("PDF has no pages")
    text_pages = sum(c >= MIN_TEXT_CHARS_PER_PAGE for c in counts)
    if text_pages == len(counts):
        return "born_digital"
    if text_pages == 0:
        return "scanned"
    return "mixed"


def local_name(doc_id: str, content_type: str, url: str) -> str:
    ext = ".pdf" if "pdf" in content_type or url.lower().endswith(".pdf") else ".html"
    if "pdf" not in content_type and "html" not in content_type and "." in url.rsplit("/", 1)[-1]:
        ext = "." + url.rsplit(".", 1)[-1].lower()[:5]
    return doc_id.replace(":", "_").replace("@", "_") + ext


def _check_scheme(url: str) -> None:
    if not url.startswith(("https://", "http://")):
        raise ValueError(f"refusing non-http(s) url {url!r}")


def _with_retries(fetch_once: Callable[[], tuple[bytes, str]]) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            return fetch_once()
        except OSError as exc:  # URLError, HTTPError and timeouts are all OSError subclasses
            last_error = exc
            time.sleep(2**attempt)
    raise OSError(f"download failed after {RETRIES} tries: {last_error}")


def http_download(url: str) -> tuple[bytes, str]:
    """GET with retries + backoff. Returns (body, content type without parameters)."""
    _check_scheme(url)

    def once() -> tuple[bytes, str]:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            body: bytes = response.read()
            return body, str(response.headers.get_content_type())

    return _with_retries(once)


# MP Labour DMS (labour.mponline.gov.in), checked 2026-11-06: the listing page's "View" button opens
# ``/portal/services/ImageShow.aspx?src=<base64 of the file path>``; that page links to a
# session-bound ``ShowPDF.axd?Path=...&recID=...`` which returns the PDF. The ImageShow URL is the
# stable, citable source_url; the token link is followed in the same cookie session.
MP_LABOUR_DMS_VIEWER = "https://labour.mponline.gov.in/portal/services/ImageShow.aspx?src="
_SHOW_PDF_RE = re.compile(r'href="(ShowPDF\.axd\?[^"]+)"')


def mp_labour_dms_url(file_path: str) -> str:
    """Stable viewer URL for a DMS file path such as ``/QL_Shram/DMS/Document/<uuid>.pdf``."""
    return MP_LABOUR_DMS_VIEWER + base64.b64encode(file_path.encode("ascii")).decode("ascii")


def mp_labour_dms_download(url: str) -> tuple[bytes, str]:
    """Two-hop download: viewer page -> session-bound ShowPDF.axd link -> PDF bytes."""
    _check_scheme(url)

    def once() -> tuple[bytes, str]:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.addheaders = [("User-Agent", USER_AGENT)]
        with opener.open(url, timeout=TIMEOUT_S) as response:
            page = response.read().decode("utf-8", "replace")
        match = _SHOW_PDF_RE.search(page)
        if match is None:
            raise ValueError("DMS viewer page has no ShowPDF link (portal changed?)")
        pdf_url = urllib.parse.urljoin(url, html.unescape(match.group(1)))
        request = urllib.request.Request(pdf_url, headers={"Referer": url})
        with opener.open(request, timeout=TIMEOUT_S * 3) as response:
            body: bytes = response.read()
            content_type = str(response.headers.get_content_type())
        if content_type != "application/pdf" or not body.startswith(b"%PDF"):
            raise ValueError(f"DMS returned {content_type}, not a PDF")
        return body, content_type

    return _with_retries(once)


RESOLVERS: dict[str, Downloader] = {
    "direct": http_download,
    "mp_labour_dms": mp_labour_dms_download,
}


def build_document(
    source: dict[str, Any], body: bytes, content_type: str, local_path: str, fetched_at: datetime
) -> dict[str, Any]:
    """Manifest document row for a freshly fetched file (always mode=archive, see module doc)."""
    doc: dict[str, Any] = {"doc_id": source["doc_id"], "mode": "archive"}
    for key in _COPIED_FIELDS:
        if key == "source_url":
            doc[key] = source["url"]
        elif source.get(key) is not None:
            doc[key] = copy.deepcopy(source[key])
    doc.update(
        fetched_at=fetched_at.isoformat(timespec="seconds"),
        sha256=sha256_hex(body),
        bytes=len(body),
        content_type=content_type,
        text_layer=detect_text_layer(body, content_type, source.get("language")),
        local_path=local_path,
    )
    target = source.get("target_mode", "archive")
    if target != "archive":
        doc["notes"] = (doc.get("notes", "") + f" [pending: target_mode={target}]").strip()
    return doc


def validate_sources(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return ["sources file must be an object with schema_version 1"]
    rows = data.get("sources")
    if not isinstance(rows, list):
        return ["'sources' must be a list"]
    seen: set[str] = set()
    for i, row in enumerate(rows):
        where = f"sources[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{where}: must be an object")
            continue
        for key in sorted(set(row) - _SOURCE_FIELDS):
            errors.append(f"{where}: unknown field {key!r}")
        for key in ("doc_id", "instrument_id", "url", "language", "status", "publisher"):
            if not isinstance(row.get(key), str) or not row[key]:
                errors.append(f"{where}: missing {key!r}")
        if row.get("resolver", "direct") not in RESOLVERS:
            errors.append(f"{where}: unknown resolver {row.get('resolver')!r}")
        if row.get("target_mode", "archive") not in MODES:
            errors.append(f"{where}: bad target_mode {row.get('target_mode')!r}")
        doc_id = row.get("doc_id")
        if isinstance(doc_id, str):
            if doc_id in seen:
                errors.append(f"{where}: duplicate doc_id {doc_id!r}")
            seen.add(doc_id)
    return errors


# --------------------------------------------------------------------------- run


def fetch_all(
    sources_path: Path,
    manifest_path: Path,
    data_dir: Path,
    *,
    only: Sequence[str] = (),
    delay_s: float = DEFAULT_DELAY_S,
    download: Downloader | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list[FetchResult]:
    sources_data = json.loads(sources_path.read_text(encoding="utf-8"))
    errors = validate_sources(sources_data)
    if errors:
        raise ValueError("invalid sources file:\n- " + "\n- ".join(errors))
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_id = {d["doc_id"]: d for d in manifest.get("documents", [])}

    results: list[FetchResult] = []
    first = True
    for source in sources_data["sources"]:
        doc_id: str = source["doc_id"]
        if only and doc_id not in only:
            continue
        existing = by_id.get(doc_id)
        if existing is not None and _local_matches(data_dir, existing):
            results.append(FetchResult(doc_id, "skipped", "local file matches manifest sha256"))
            continue
        if not first:
            time.sleep(delay_s)
        first = False
        try:
            downloader = download or RESOLVERS[source.get("resolver", "direct")]
            body, content_type = downloader(source["url"])
            name = local_name(doc_id, content_type, source["url"])
            rel = f"raw/{source['instrument_id']}/{name}"
            if existing is not None and existing.get("sha256") != sha256_hex(body):
                _atomic_write(data_dir / (rel + ".new"), body)
                results.append(FetchResult(doc_id, "changed", f"saved {rel}.new; needs review"))
                continue
            doc = build_document(source, body, content_type, rel, now())
            _atomic_write(data_dir / rel, body)
        except (OSError, ValueError) as exc:
            results.append(FetchResult(doc_id, "error", str(exc)))
            continue
        if existing is not None:  # same bytes, file was missing locally: just restore it
            results.append(FetchResult(doc_id, "skipped", "restored local file"))
            continue
        manifest.setdefault("documents", []).append(doc)
        by_id[doc_id] = doc
        results.append(FetchResult(doc_id, "added", f"{doc['text_layer']}, {doc['bytes']} bytes"))

    _, manifest_errors = parse_manifest(manifest)
    if manifest_errors:
        raise ValueError(
            "manifest would be invalid, not written:\n- " + "\n- ".join(manifest_errors)
        )
    _atomic_write(
        manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return results


def _local_matches(data_dir: Path, doc: dict[str, Any]) -> bool:
    path = data_dir / str(doc.get("local_path", ""))
    return path.is_file() and sha256_hex(path.read_bytes()) == doc.get("sha256")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download corpus files listed in corpus_sources.json"
    )
    parser.add_argument("--sources", type=Path, default=Path("data/corpus_sources.json"))
    parser.add_argument("--manifest", type=Path, default=Path("data/corpus_manifest.json"))
    parser.add_argument(
        "--data-dir", type=Path, default=Path(os.environ.get("MKS_DATA_DIR", "data"))
    )
    parser.add_argument("--only", nargs="*", default=[], help="doc_ids to fetch (default: all)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_S)
    args = parser.parse_args(argv)
    results = fetch_all(
        args.sources, args.manifest, args.data_dir, only=args.only, delay_s=args.delay
    )
    for r in results:
        print(f"{r.outcome:8} {r.doc_id}  {r.detail}")
    return 1 if any(r.outcome in {"error", "changed"} for r in results) else 0
