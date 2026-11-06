"""SessionStart hook (matcher "compact"): re-inject a short PROGRESS.md summary after compaction.

Plain-text stdout from a SessionStart hook is added to Claude's context.
Hook contract: https://code.claude.com/docs/en/hooks
(SessionStart source "compact"), checked 2026-11-06.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ACTIVE = re.compile(r"\|\s*(in progress|blocked)\s*\|", re.IGNORECASE)


def summarise(progress: str, decisions: str | None) -> str:
    lines = progress.splitlines()
    active = [ln.strip() for ln in lines if ACTIVE.search(ln)]

    last_entry: list[str] = []
    if "## Session log" in progress:
        log = progress.split("## Session log", 1)[1].splitlines()
        started = False
        for ln in log:
            if ln.startswith("### "):
                if started:
                    break
                started = True
            if started:
                last_entry.append(ln)

    pending: list[str] = []
    if decisions and "## Pending decisions" in decisions:
        block = decisions.split("## Pending decisions", 1)[1]
        pending = [
            ln.strip()
            for ln in block.splitlines()
            if ln.startswith("|") and not ln.startswith("| ---") and not ln.startswith("| Topic")
        ]

    out = ["[Context restored after compaction — from docs/PROGRESS.md and docs/DECISIONS.md]"]
    out.append("Active roadmap items:")
    out.extend(active or ["  (none marked in progress or blocked)"])
    out.append("Last session-log entry:")
    out.extend(last_entry or ["  (none)"])
    if pending:
        out.append("Pending decisions:")
        out.extend(pending)
    out.append("Re-read CLAUDE.md protocols before continuing. Work only on the agreed task.")
    return "\n".join(out)


def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    progress = root / "docs" / "PROGRESS.md"
    if not progress.exists():
        return 0
    decisions = root / "docs" / "DECISIONS.md"
    text = summarise(
        progress.read_text(encoding="utf-8"),
        decisions.read_text(encoding="utf-8") if decisions.exists() else None,
    )
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
