# ruff: noqa: E501
"""Weekly law-watch (W3.3, DEC-013, DEC-095). Standard library only.

    python scripts/law_watch.py --out <dir>

Re-fetches the sources the bot relies on and reports what changed; it never edits the corpus (a
rebuild needs Malik's approval, DEC-013). Writes ``<dir>/law_watch.md`` and ``<dir>/law_watch.json``;
the GitHub Actions workflow opens or updates a ``law-watch`` issue when ``changed`` is not empty.

- **PDF documents** of the manifest in modes ``index``, ``guide`` and ``gated``: downloaded again and
  their sha256 compared with ``corpus_manifest.json`` (different = changed).
- **Internet Archive snapshots** (``web.archive.org``) cannot change: listed, not fetched.
- **HTML pages** change on every load (menus, dates), so a hash would always differ: listed for a
  manual check, not compared.
- **Contacts** (``contacts.yaml``): each source page is fetched and its visible text (tags removed,
  entities decoded) checked for the recorded quote (e.g. "NALSA Helpline Number 15100"). Quote found =
  fine; quote missing but the number still on the page = check by hand (wording or layout changed);
  number missing = change.
- Sites that fail (timeouts, 5xx), and "PDF" links that return a web page instead (e.g. a portal that
  needs a browser session), are listed as unreachable, not as changes.

Politeness: generic project User-Agent, one request every ``--pause`` seconds (default 2), 30 s timeout.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "corpus_manifest.json"
CONTACTS = ROOT / "data" / "contacts.yaml"  # JSON syntax (valid YAML 1.2)
WATCHED_MODES = ("index", "guide", "gated")
USER_AGENT = "madhya-kanoon-saathi-lawwatch/0.1"
MAX_BYTES = 60_000_000
_TAGS = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>|<[^>]+>")


def visible_text(page: str) -> str:
    """Page text without tags, scripts or entities, whitespace collapsed (for quote checks)."""
    return " ".join(html.unescape(_TAGS.sub(" ", page)).split())


Fetch = Callable[[str], bytes]


@dataclass
class Report:
    checked_at: str
    changed: list[dict[str, Any]] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    unreachable: list[dict[str, str]] = field(default_factory=list)
    snapshots: list[str] = field(default_factory=list)
    manual: list[dict[str, str]] = field(default_factory=list)
    contacts_ok: list[str] = field(default_factory=list)


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data: bytes = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("response too large")
    return data


def check(manifest: dict[str, Any], contacts: dict[str, Any], fetch: Fetch, pause: float) -> Report:
    rep = Report(checked_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    first = True

    def get(url: str) -> bytes:
        nonlocal first
        if not first:
            time.sleep(pause)
        first = False
        return fetch(url)

    for d in manifest["documents"]:
        if d.get("mode") not in WATCHED_MODES or not d.get("source_url"):
            continue
        url, doc_id = d["source_url"], d["doc_id"]
        if "web.archive.org/" in url:
            rep.snapshots.append(doc_id)
            continue
        if not str(d.get("content_type", "")).startswith("application/pdf"):
            rep.manual.append({"doc_id": doc_id, "url": url})
            continue
        try:
            data = get(url)
        except (urllib.error.URLError, OSError, ValueError) as e:
            rep.unreachable.append({"doc_id": doc_id, "url": url, "error": type(e).__name__})
            continue
        if not data.lstrip()[:5].startswith(b"%PDF"):
            rep.unreachable.append(
                {
                    "doc_id": doc_id,
                    "url": url,
                    "error": f"not a PDF ({len(data)} bytes; site returned a web page)",
                }
            )
            continue
        got = hashlib.sha256(data).hexdigest()
        if got != d.get("sha256"):
            rep.changed.append(
                {"kind": "document", "doc_id": doc_id, "url": url, "mode": d["mode"],
                 "manifest_sha256": d.get("sha256"), "now_sha256": got}
            )  # fmt: skip
        else:
            rep.unchanged.append(doc_id)

    for c in contacts.get("contacts", []):
        for src in c.get("sources", []):
            url, quote = src.get("url"), src.get("quote")
            if not url or not quote:
                continue
            try:
                page = get(url).decode("utf-8", "replace")
            except (urllib.error.URLError, OSError, ValueError) as e:
                rep.unreachable.append(
                    {"doc_id": f"contact:{c['id']}", "url": url, "error": type(e).__name__}
                )
                continue
            text = visible_text(page)
            if quote in text:
                rep.contacts_ok.append(c["id"])
            elif c.get("number") and str(c["number"]) in text:
                rep.manual.append(
                    {"doc_id": f"contact:{c['id']}", "url": url,
                     "note": f"quote “{quote}” not found, number {c['number']} still on the page"}
                )  # fmt: skip
            else:
                rep.changed.append(
                    {"kind": "contact", "doc_id": f"contact:{c['id']}", "url": url,
                     "missing_quote": quote, "number": c.get("number")}
                )  # fmt: skip
    return rep


def markdown(rep: Report) -> str:
    lines = [
        f"Law-watch run {rep.checked_at} (DEC-013, DEC-095). No corpus change is made without Malik's approval.",
        "",
    ]
    if rep.changed:
        lines += ["## Changed", "", "| source | kind | detail | url |", "| --- | --- | --- | --- |"]
        for c in rep.changed:
            detail = (
                f"sha256 {str(c.get('manifest_sha256'))[:12]} → {c['now_sha256'][:12]} ({c['mode']})"
                if c["kind"] == "document"
                else f"quote no longer found: “{c['missing_quote']}” (number {c.get('number')})"
            )
            lines.append(f"| {c['doc_id']} | {c['kind']} | {detail} | {c['url']} |")
        lines += [
            "",
            "Next: download the new file, check whether it is a new version, a correction or a draft, update the manifest, re-run the affected golden rows, then rebuild (DEC-013).",
            "",
        ]
    else:
        lines += ["No changes found.", ""]
    lines += [
        f"- unchanged PDFs: {len(rep.unchanged)} · contact quotes found: {len(rep.contacts_ok)}"
    ]
    if rep.unreachable:
        lines += ["", "## Unreachable (not counted as changes)", ""]
        lines += [f"- {u['doc_id']}: {u['error']} — {u['url']}" for u in rep.unreachable]
    if rep.manual:
        lines += [
            "",
            "## Check by hand (HTML pages change on every load; contact pages whose wording moved)",
            "",
        ]
        lines += [
            f"- {m['doc_id']}: {m['url']}" + (f" ({m['note']})" if m.get("note") else "")
            for m in rep.manual
        ]
    if rep.snapshots:
        lines += [
            "",
            f"Internet Archive snapshots (cannot change, not fetched): {', '.join(rep.snapshots)}",
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pause", type=float, default=2.0)
    a = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    contacts = json.loads(CONTACTS.read_text("utf-8"))
    rep = check(manifest, contacts, fetch_url, a.pause)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "law_watch.json").write_text(
        json.dumps(asdict(rep), indent=1) + "\n", encoding="utf-8"
    )
    (a.out / "law_watch.md").write_text(markdown(rep), encoding="utf-8")
    print(
        f"changed {len(rep.changed)} · unchanged {len(rep.unchanged)} · unreachable {len(rep.unreachable)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
