"""Save the official source pages of data/contacts.yaml and check them (DEC-018).

Usage:
    uv run python scripts/fetch_contacts.py            # download missing pages, verify all
    uv run python scripts/fetch_contacts.py --record   # also write sha256 for sources without one

- Pages go to data/raw/contacts/ (git-ignored, like corpus files); contacts.yaml keeps url, file,
  sha256, fetch date and the exact quote that contains the number.
- A page whose bytes differ from the recorded sha256 is saved as *.new and reported; the record is
  never overwritten silently (a human reviews changes, as for law texts, DEC-013).
- Exit code 1 if any contact fails: missing page, changed page, or quote not found.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from madhya_kanoon_saathi.common.contacts import check_sources, load, page_text, validate
from madhya_kanoon_saathi.ingestion.fetch import http_download

DATA = Path("data")
FILE = DATA / "contacts.yaml"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help="write sha256 for sources without one")
    a = ap.parse_args()
    data = json.loads(FILE.read_text(encoding="utf-8"))
    failed = False
    for c in data["contacts"]:
        for s in c["sources"]:
            path = DATA / s["file"]
            if not path.exists():
                body, _ = http_download(s["url"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
                print(f"saved {s['file']} ({len(body)} bytes)")
            body = path.read_bytes()
            digest = hashlib.sha256(body).hexdigest()
            if not s["sha256"] and a.record:
                s["sha256"] = digest
            quote_ok = s["quote"] in page_text(body)
            print(
                f"{c['id']:18s} {c['number']:>6s} quote {'ok' if quote_ok else 'NOT FOUND'}"
                f" | {s['file']}"
            )
            failed |= not quote_ok
    if a.record:
        FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    errs = validate(data)
    if not errs:
        for contact in load(FILE):
            errs += check_sources(contact, DATA)
    for e in errs:
        print("ERROR", e)
    return 1 if (failed or errs) else 0


if __name__ == "__main__":
    sys.exit(main())
