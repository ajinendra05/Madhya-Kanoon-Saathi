"""Stop hook: run fast lint + tests when Claude finishes a turn; report failures back.

- Skips when stop_hook_active is true (already continuing because of a stop hook) to avoid loops.
- Fast set only: ruff check, ruff format --check, pytest excluding slow/paid/golden markers.
  mypy and the full suite run in pre-commit/CI and /end-session.
Hook contract: https://code.claude.com/docs/en/hooks
(Stop input + decision control), checked 2026-11-06.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

UV = ["uv", "run", "--frozen"]
FAST_MARKERS = "not slow and not paid and not golden"
CHECKS: list[tuple[str, list[str]]] = [
    ("ruff check", [*UV, "ruff", "check", ".", "--quiet"]),
    ("ruff format", [*UV, "ruff", "format", "--check", ".", "--quiet"]),
    ("pytest (fast)", [*UV, "pytest", "-q", "-x", "-m", FAST_MARKERS]),
]
MAX_CHARS = 2500


def main() -> int:
    data = json.load(sys.stdin)
    if data.get("stop_hook_active"):
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    failures: list[str] = []
    for name, cmd in CHECKS:
        try:
            proc = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=150,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            failures.append(f"[{name}] could not run: {exc}")
            continue
        # pytest exit 5 = no tests collected; not a failure.
        if proc.returncode not in (0, 5) or (name.startswith("ruff") and proc.returncode != 0):
            out = (proc.stdout + proc.stderr).strip()
            failures.append(f"[{name}] exit {proc.returncode}\n{out[-MAX_CHARS:]}")
    if not failures:
        return 0
    json.dump(
        {
            "decision": "block",
            "reason": (
                "Fast checks failed after this turn. Report these failures to Malik. "
                "Fix them only if they are inside the current approved task; "
                "otherwise log them in docs/PROGRESS.md.\n\n" + "\n\n".join(failures)
            ),
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
