"""Weekly law-watch (W3.3, DEC-013, DEC-095): what counts as a change. No network."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import urllib.error
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("law_watch", Path("scripts/law_watch.py"))
assert SPEC and SPEC.loader
lw = importlib.util.module_from_spec(SPEC)
sys.modules["law_watch"] = lw
SPEC.loader.exec_module(lw)

PDF_A, PDF_B = b"%PDF-1.4 old", b"%PDF-1.4 new"
MANIFEST = {
    "documents": [
        {"doc_id": "A", "mode": "index", "content_type": "application/pdf", "source_url": "https://x.gov.in/a.pdf", "sha256": hashlib.sha256(PDF_A).hexdigest()},
        {"doc_id": "B", "mode": "gated", "content_type": "application/pdf", "source_url": "https://x.gov.in/b.pdf", "sha256": hashlib.sha256(PDF_A).hexdigest()},
        {"doc_id": "C", "mode": "archive", "content_type": "application/pdf", "source_url": "https://x.gov.in/c.pdf", "sha256": "0"},
        {"doc_id": "D", "mode": "index", "content_type": "application/pdf", "source_url": "https://web.archive.org/web/2026id_/https://x.gov.in/d.pdf", "sha256": "0"},
        {"doc_id": "E", "mode": "guide", "content_type": "text/html", "source_url": "https://x.gov.in/e.html", "sha256": "0"},
        {"doc_id": "F", "mode": "index", "content_type": "application/pdf", "source_url": "https://down.gov.in/f.pdf", "sha256": "0"},
        {"doc_id": "G", "mode": "index", "content_type": "application/pdf", "source_url": "https://x.gov.in/g.pdf", "sha256": "0"},
    ]
}  # fmt: skip
CONTACTS = {
    "contacts": [
        {"id": "nalsa", "number": "15100", "sources": [{"url": "https://nalsa.gov.in/c", "quote": "NALSA Helpline Number 15100"}]},
        {"id": "old", "number": "1234", "sources": [{"url": "https://x.gov.in/old", "quote": "Helpline 1234"}]},
        {"id": "moved", "number": "181", "sources": [{"url": "https://x.gov.in/moved", "quote": "CM Helpline 181"}]},
    ]
}  # fmt: skip
PAGES = {
    "https://x.gov.in/a.pdf": PDF_A,
    "https://x.gov.in/b.pdf": PDF_B,
    "https://nalsa.gov.in/c": b"<p>NALSA <span>Helpline</span>\n  Number&nbsp;15100</p>",
    "https://x.gov.in/old": b"<p>Helpline changed</p>",
    "https://x.gov.in/moved": b"<div>Call <b>181</b> for the CM helpline</div>",
    "https://x.gov.in/g.pdf": b"\r\n<!DOCTYPE html><html>login</html>",
}
fetched: list[str] = []


def fake_fetch(url: str) -> bytes:
    fetched.append(url)
    if url not in PAGES:
        raise urllib.error.URLError("unreachable")
    return PAGES[url]


def test_changes_snapshots_manual_and_unreachable_are_kept_apart() -> None:
    fetched.clear()
    rep = lw.check(MANIFEST, CONTACTS, fake_fetch, pause=0)
    assert rep.unchanged == ["A"]
    assert [c["doc_id"] for c in rep.changed] == ["B", "contact:old"]
    assert rep.changed[0]["now_sha256"] == hashlib.sha256(PDF_B).hexdigest()
    assert rep.changed[1]["missing_quote"] == "Helpline 1234"
    assert rep.snapshots == ["D"]
    assert [m["doc_id"] for m in rep.manual] == ["E", "contact:moved"]  # number still on the page
    assert [u["doc_id"] for u in rep.unreachable] == ["F", "G"]  # G: web page instead of the PDF
    assert "not a PDF" in rep.unreachable[1]["error"]
    assert rep.contacts_ok == ["nalsa"]  # quote found across a line break
    assert "https://x.gov.in/c.pdf" not in fetched  # archive mode is not watched
    assert not any("web.archive.org" in u for u in fetched)  # snapshots are not fetched


def test_markdown_lists_changes_and_next_steps() -> None:
    md = lw.markdown(lw.check(MANIFEST, CONTACTS, fake_fetch, pause=0))
    assert "## Changed" in md and "quote no longer found" in md and "DEC-013" in md
    assert "## Unreachable" in md and "## Check by hand" in md


def test_no_change_report() -> None:
    m = {"documents": MANIFEST["documents"][:1]}
    md = lw.markdown(lw.check(m, {"contacts": []}, fake_fetch, pause=0))
    assert "No changes found." in md
