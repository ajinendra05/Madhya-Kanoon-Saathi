---
name: end-session
description: End a Madhya Kanoon Saathi work session. Runs all checks, updates PROGRESS / OPEN_QUESTIONS / DECISIONS, makes the final commit, summarises, and asks before git push.
disable-model-invocation: true
argument-hint: "[optional note for the session log]"
---

# End session

Format: https://code.claude.com/docs/en/skills, checked 2026-11-06.

Malik's note for the log (may be empty): $ARGUMENTS

## Live repo state (injected)
- Today: !`date +%Y-%m-%d`
- Working tree: !`git status --short --branch 2>&1 || echo "(not a git repo yet)"`

## 1. Run all checks and show real output
Run each and keep the actual output (do not paraphrase a failure as a pass):
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy`
- `uv run pytest` (paid tests stay skipped; never add `-m paid` here)
- `pre-commit run --all-files` (only if this is a git repo)

If something fails: fix it only if the fix is inside today's approved task; otherwise record it as a problem in step 2.

## 2. Update the docs
- `docs/PROGRESS.md`: set each touched item's status (todo / in progress / done / blocked). Add a session-log entry at the **top** of "Session log":
  `### YYYY-MM-DD`, then bullets **Done**, **Decisions** (DEC ids), **Problems**, **Next step** (one roadmap ID), plus Malik's note if given. Include the check results (pass/fail per command).
- `docs/OPEN_QUESTIONS.md`: mark anything resolved (answer + source URL + date); add new unverified facts and `TODO(verify)` items.
- `docs/DECISIONS.md`: confirm every decision Malik made today has a DEC entry (asks Malik for approval to edit; that's expected). Never edit old entries; supersede them instead.
- `docs/CONCEPTS.md`, `docs/TOOLS.md`: add any new concept or tool/dependency introduced today.

## 3. Commit
- `git add` only the intended files; check `git status` shows no `.env`, data, models, or PDFs.
- One Conventional Commit for anything not yet committed (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), with a body listing what changed. End the message with the attribution trailer required by the current Claude Code instructions.
- Never use `--no-verify`. If a pre-commit hook fails, fix the cause and commit again (new commit, no amend).

## 4. Summarise and ask
Reply to Malik with:
- what was done today, check results, decisions recorded, problems, next step
- `git log --oneline` of today's commits
- **"OK to `git push`?"** Then wait. Never push, force-push, or create a branch/repo without an explicit yes.
