"""Static HTML viewer for data/parsed/chunks.jsonl (W1.1 definition of done).

Usage:
    uv run python scripts/chunk_viewer.py   # data/parsed/viewer/index.html + one page per doc

Each document page lists its chunks in order: chunk_id, pages, token estimate, heading path,
canonical text, footnotes, and (collapsed) the raw extractor text. Output is git-ignored;
open index.html locally in a browser.
"""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

SRC = Path("data/parsed/chunks.jsonl")
OUT = Path("data/parsed/viewer")
SEP = " > "
CSS = """
body{font:15px/1.5 system-ui,sans-serif;margin:16px;max-width:1100px}
.c{border:1px solid #ccc;border-radius:6px;padding:8px 12px;margin:10px 0}
.id{font:12px monospace;color:#555}.t{white-space:pre-wrap}.w{color:#a40}
.fn{font-size:13px;color:#335}details{font-size:12px;color:#444}pre{white-space:pre-wrap}
"""


def page(title: str, body: str) -> str:
    head = "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
    return f"{head}<title>{html.escape(title)}</title><style>{CSS}</style>{body}"


def card(c: dict) -> str:
    esc = html.escape
    warn = "" if 150 <= c["token_estimate"] <= 450 else "w"
    first, last = c["locator"]["pages"]
    fns = "".join(
        f"<div class=fn>[{esc(f['n'])}] p.{f['page']}: {esc(f['text'])}</div>"
        for f in c["footnotes"]
    )
    meta = (
        f"{esc(c['chunk_id'])} | pages {first}-{last} | "
        f"<span class='{warn}'>~{c['token_estimate']} tokens</span> | {esc(SEP.join(c['path']))}"
    )
    raw = f"<details><summary>raw text</summary><pre>{esc(c['raw_text'])}</pre></details>"
    text = f"<div class=t>{esc(c['text'])}</div>"
    return f"<div class=c><div class=id>{meta}</div>{text}{fns}{raw}</div>"


def main() -> None:
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for line in SRC.read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        by_doc[c["doc_id"]].append(c)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for doc_id, chunks in sorted(by_doc.items()):
        name = doc_id.replace("@", "_") + ".html"
        rows.append(f"<li><a href='{name}'>{html.escape(doc_id)}</a> ({len(chunks)} chunks)</li>")
        top = f"<h1>{html.escape(doc_id)}</h1><p><a href='index.html'>all documents</a></p>"
        body = top + "".join(card(c) for c in chunks)
        (OUT / name).write_text(page(doc_id, body), encoding="utf-8")
    index = "<h1>Chunks</h1><ul>" + "".join(rows) + "</ul>"
    (OUT / "index.html").write_text(page("Chunks", index), encoding="utf-8")
    print(f"wrote {len(by_doc)} document pages to {OUT}")


if __name__ == "__main__":
    main()
