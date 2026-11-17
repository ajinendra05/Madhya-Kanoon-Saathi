"""Escalation contacts (DEC-018): schema, and every number backed by its saved official page."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from madhya_kanoon_saathi.common.contacts import check_sources, load, page_text, validate

DATA = Path("data")
FILE = DATA / "contacts.yaml"
GOOD = {
    "contacts": [
        {
            "id": "child_1098",
            "number": "1098",
            "name_en": "Child Helpline (1098)",
            "name_hi": None,
            "scope": "IN",
            "purpose": ["child_helpline"],
            "verified_on": "2026-11-17",
            "verified_by": "claude",
            "sources": [
                {
                    "url": "https://www.pib.gov.in/x",
                    "file": "raw/contacts/x.html",
                    "sha256": "0" * 64,
                    "fetched_on": "2026-11-17",
                    "quote": "toll free number (1098)",
                }
            ],
        }
    ]
}


def test_committed_contacts_file_is_valid() -> None:
    contacts = load(FILE)
    numbers = {c.id: c.number for c in contacts}
    assert numbers["erss_112"] == "112" and numbers["nalsa_15100"] == "15100"
    # 181 serves two different purposes in MP; both are listed separately
    assert {c.purpose for c in contacts if c.number == "181"} == {
        ("women_helpline",),
        ("grievance",),
    }


def test_every_number_is_in_its_saved_official_page() -> None:
    contacts = load(FILE)
    if not all((DATA / s.file).is_file() for c in contacts for s in c.sources):
        pytest.skip("source pages not downloaded (scripts/fetch_contacts.py); git-ignored")
    errors = [e for c in contacts for e in check_sources(c, DATA)]
    assert errors == []


def test_valid_example_passes() -> None:
    assert validate(GOOD) == []


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda c: c.update(number="10 98"), "bad number"),
        (lambda c: c.update(scope="MH"), "scope"),
        (lambda c: c.update(purpose=["private_lawyer"]), "purpose"),
        (lambda c: c.update(sources=[]), "official source"),
        (lambda c: c["sources"][0].update(quote="toll free number"), "does not contain"),
        (lambda c: c["sources"][0].update(sha256=""), "sha256 missing"),
        (lambda c: c["sources"][0].update(url="http://x.gov.in"), "https"),
    ],
)
def test_invalid_contacts_are_rejected(change, message: str) -> None:  # type: ignore[no-untyped-def]
    data = copy.deepcopy(GOOD)
    change(data["contacts"][0])
    assert any(message in e for e in validate(data))


def test_check_sources_detects_changed_page_and_missing_quote(tmp_path: Path) -> None:
    page = b"<html><script>var x=1098;</script><p>dial a toll&nbsp;free number (1098)</p></html>"
    (tmp_path / "raw" / "contacts").mkdir(parents=True)
    (tmp_path / "raw/contacts/x.html").write_bytes(page)
    data = copy.deepcopy(GOOD)
    data["contacts"][0]["sources"][0]["sha256"] = hashlib.sha256(page).hexdigest()
    f = tmp_path / "contacts.yaml"
    f.write_text(json.dumps(data), encoding="utf-8")
    (contact,) = load(f)
    assert check_sources(contact, tmp_path) == []
    (tmp_path / "raw/contacts/x.html").write_bytes(page.replace(b"(1098)", b"(1099)"))
    errs = check_sources(contact, tmp_path)
    assert any("sha256" in e for e in errs) and any("quote not found" in e for e in errs)


def test_page_text_ignores_scripts() -> None:
    assert "1098" not in page_text(b"<script>var n='1098'</script><p>help</p>")
