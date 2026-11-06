"""PreToolUse hook: edits to protected files need Malik's approval.

Returns permissionDecision "ask" (not "deny") so Malik can approve in the prompt.
Hook contract: https://code.claude.com/docs/en/hooks
(PreToolUse decision control), checked 2026-11-06.
Stdlib only, so it runs on any Python 3 without the project venv.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys

# Repo-relative POSIX glob patterns (CLAUDE.md "Protected files"; DEC-035).
PROTECTED = [
    "docs/DECISIONS.md",
    "docs/CORPUS.md",
]


def _norm(path: str) -> str:
    """POSIX separators; case-folded on Windows (case-insensitive filesystem)."""
    path = path.replace("\\", "/")
    return path.lower() if os.name == "nt" else path


def relative_to_project(file_path: str, project_dir: str) -> str | None:
    fp, root = _norm(os.path.abspath(file_path)), _norm(os.path.abspath(project_dir))
    if fp == root or not fp.startswith(root.rstrip("/") + "/"):
        return None  # outside the project: not our concern here
    return fp[len(root.rstrip("/")) + 1 :]


def is_protected(rel: str) -> bool:
    return any(fnmatch.fnmatchcase(rel, _norm(p)) for p in PROTECTED)


def main() -> int:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    rel = relative_to_project(file_path, project_dir)
    if rel is None or not is_protected(rel):
        return 0  # no decision: normal permission flow
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    f"'{rel}' is a protected file (CLAUDE.md). "
                    "Edit only with Malik's explicit approval."
                ),
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
