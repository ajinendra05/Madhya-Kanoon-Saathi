"""Report how much of a golden set the current corpus can actually answer (DEC-063, read-only).

For every expected clause of every row, prints one status:
  invalid_uid             - not a well-formed section_uid
  not_in_manifest         - instrument not registered in data/corpus_manifest.json
  not_indexed             - instrument has no document in mode index/guide (gated, archive, ...)
  outside_index_scope     - indexed, but outside the document's index_scope (DEC-051)
  retrievable_now         - a built chunk equals, contains or is contained in the provision
  no_matching_chunk       - indexed and in scope, but no chunk yet (e.g. waiting for OCR, W1.1b)

Usage:  uv run python scripts/check_golden.py [path/to/golden.jsonl] [--write]
--write saves the report as coverage.md next to the JSONL file.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from madhya_kanoon_saathi.common.section_uid import covers, is_valid
from madhya_kanoon_saathi.ingestion.manifest import Document, parse_manifest

DEFAULT = Path("data/golden/v0.1-seed/golden_set_v0.1_seed.jsonl")
ORDER = [
    "retrievable_now",
    "no_matching_chunk",
    "outside_index_scope",
    "not_indexed",
    "not_in_manifest",
    "invalid_uid",
]


def classify(
    uid: str, docs: dict[str, list[Document]], chunks: dict[str, list[str]], known: set[str]
) -> str:
    if not is_valid(uid):
        return "invalid_uid"
    inst = uid.split(":")[0]
    if inst not in known:
        return "not_in_manifest"
    live = [d for d in docs[inst] if d.mode in ("index", "guide")]
    if not live:
        return "not_indexed"
    if not any(d.in_scope(uid) for d in live):
        return "outside_index_scope"
    if any(covers(c, uid) or covers(uid, c) for c in chunks.get(inst, [])):
        return "retrievable_now"
    return "no_matching_chunk"


def main(argv: list[str]) -> int:
    write = "--write" in argv
    args = [a for a in argv if a != "--write"]
    path = Path(args[0]) if args else DEFAULT
    manifest, errors = parse_manifest(
        json.loads(Path("data/corpus_manifest.json").read_text(encoding="utf-8"))
    )
    if manifest is None:
        print("manifest invalid:", errors)
        return 1
    docs: dict[str, list[Document]] = defaultdict(list)
    for d in manifest.documents.values():
        docs[d.instrument_id].append(d)
    chunks: dict[str, list[str]] = defaultdict(list)
    chunk_file = Path("data/parsed/chunks.jsonl")
    if chunk_file.exists():
        for line in chunk_file.read_text(encoding="utf-8").splitlines():
            uid = json.loads(line)["section_uid"]
            chunks[uid.split(":")[0]].append(uid)
    known = set(manifest.instruments)

    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    by_status: dict[str, list[str]] = defaultdict(list)
    rows_fully = 0
    rows_with_clauses = 0
    for r in rows:
        uids = [
            c["section_uid"] or c["act_id"] for c in r.get("expected_clauses", [])
        ]  # act-level when no uid
        if not uids:
            continue
        rows_with_clauses += 1
        st = [classify(u, docs, chunks, known) for u in uids]
        rows_fully += all(s == "retrievable_now" for s in st)
        for u, s in zip(uids, st, strict=True):
            by_status[s].append(f"{r['id']} {u}")

    counts = Counter({k: len(v) for k, v in by_status.items()})
    out = [
        f"# Golden-set coverage: {path.name}",
        "",
        f"Rows: {len(rows)} · rows with expected clauses: {rows_with_clauses} · "
        f"rows whose clauses are all retrievable now: {rows_fully}",
        "Chunks file: "
        + ("present" if chunk_file.exists() else "MISSING (run scripts/build_chunks.py)"),
        "",
        "| status | clauses |",
        "| --- | --- |",
        *[f"| {k} | {counts.get(k, 0)} |" for k in ORDER],
        "",
    ]
    for k in ORDER[1:]:
        if by_status.get(k):
            out += [f"## {k}", "", *[f"- {x}" for x in by_status[k]], ""]
    text = "\n".join(out)
    print(text)
    if write:
        (path.parent / "coverage.md").write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
