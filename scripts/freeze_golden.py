# ruff: noqa: E501
"""Freeze golden set v1.0 from the reviewed seed (W2.6; DEC-063, eval rules).

Usage:
    uv run python scripts/freeze_golden.py

Malik reviewed and verified all 130 seed rows on 2026-11-19. This writes
data/golden/v1.0/golden_set_v1.0.jsonl with set_version v1.0, review_status verified,
verified_by malik, verified_on 2026-11-19, and applies ONLY the corrections that earlier decisions
or verified findings require, each listed in data/golden/v1.0/CHANGES.md with its reason. The seed
file is not touched. v1.0 is protected once written (eval rules): changes go into a new version.
Refuses to overwrite an existing v1.0.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SEED = Path("data/golden/v0.1-seed/golden_set_v0.1_seed.jsonl")
OUT_DIR = Path("data/golden/v1.0")
OUT = OUT_DIR / "golden_set_v1.0.jsonl"
VERIFIED_ON = "2026-11-19"

OUT_OF_CORPUS = {
    "expected_behavior": "abstain_refer",
    "answerability": "none",
    "unanswerable_reason": "out_of_corpus",
}
# id -> (field changes, reason)
CORRECTIONS: dict[str, tuple[dict[str, Any], str]] = {
    "GS-121": (OUT_OF_CORPUS, "DEC-070: mutation moved to December, MPLRC s.109-110 and Mutation Rules gated (G8a)"),
    "GS-122": (OUT_OF_CORPUS, "DEC-070: mutation moved to December, MPLRC s.109-110 and Mutation Rules gated (G8a)"),
    "GS-123": (OUT_OF_CORPUS, "DEC-070: mutation moved to December, MPLRC s.109-110 and Mutation Rules gated (G8a)"),
    "GS-028": (
        {
            "expected_behavior": "answer_with_caveat",
            "gates": [],
            "expected_clauses": [
                {"act_id": "MP.MWVDAOCT2026", "section_uid": "MP.MWVDAOCT2026:sch_a_ba",
                 "confidence": "high", "version_as_of": VERIFIED_ON, "needs_verification": False},
            ],
        },
        "DEC-050: current official wage rates may be stated with the qualification; the 67 scheduled "
        "employments are Schedule A Part B (sch_a_ba, DEC-073)",
    ),
    "GS-058": (
        {
            "expected_clauses": [
                {"act_id": "IN.CPA2019", "section_uid": "IN.CPA2019:s2:ss6",
                 "confidence": "high", "version_as_of": VERIFIED_ON, "needs_verification": False},
            ],
        },
        "S31: charging above the price displayed on the goods is a ground of complaint in CPA s.2(6)(iv) "
        "(chunk IN.CPA2019:s2:ss6 text checked 2026-11-18), not s.2(47)",
    ),
}  # fmt: skip


def main() -> int:
    if OUT.exists():
        print(f"{OUT} exists and is frozen; make a new version instead")
        return 1
    rows = [json.loads(x) for x in SEED.read_text("utf-8").splitlines() if x.strip()]
    missing = set(CORRECTIONS) - {r["id"] for r in rows}
    if missing:
        raise SystemExit(f"corrections for unknown rows: {sorted(missing)}")
    log = []
    for r in rows:
        r.update(
            set_version="v1.0",
            review_status="verified",
            verified_by="malik",
            verified_on=VERIFIED_ON,
        )
        if r["id"] in CORRECTIONS:
            changes, reason = CORRECTIONS[r["id"]]
            before = {k: r.get(k) for k in changes}
            r.update(changes)
            log.append((r["id"], before, changes, reason))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    OUT.write_text(body, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    L = ["# Golden set v1.0 (frozen 2026-11-19)", "",
         f"- source: `{SEED.as_posix()}` (seed, DEC-063); reviewed and verified by Malik on {VERIFIED_ON}",
         f"- rows: {len(rows)} · sha256 of `{OUT.name}`: `{digest}`",
         "- protected: never edit; corrections go into a new version (eval rules)", "",
         "## Corrections applied at freeze (only those required by decisions or verified findings)", ""]  # fmt: skip
    for rid, before, changes, reason in log:
        L.append(f"- **{rid}**: {reason}")
        for k, v in changes.items():
            L.append(
                f"  - `{k}`: `{json.dumps(before.get(k), ensure_ascii=False)}` → `{json.dumps(v, ensure_ascii=False)}`"
            )
    (OUT_DIR / "CHANGES.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(rows)} rows, {len(log)} corrections, sha256 {digest[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
