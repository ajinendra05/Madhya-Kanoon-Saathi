---
name: start-session
description: Start a Madhya Kanoon Saathi work session. Reads project state, reports where we are, and proposes one roadmap item as today's goal, then waits for Malik's OK.
disable-model-invocation: true
---

# Start session

Format: https://code.claude.com/docs/en/skills, checked 2026-11-06.

## Live repo state (injected)
- Today: !`date +%Y-%m-%d`
- Recent commits: !`git log -5 --oneline 2>&1 || echo "(no git history yet)"`
- Working tree: !`git status --short --branch 2>&1 || echo "(not a git repo yet)"`

## Do this, in order
1. Read `CLAUDE.md` (already in context; re-check the protocols).
2. Read `docs/PROGRESS.md`: every row marked `in progress` or `blocked`, and the **newest** session-log entry.
3. Read `docs/OPEN_QUESTIONS.md`: items still `open` that affect the next roadmap item, plus the deferred decisions (group E).
4. Read the "Pending decisions" table at the end of `docs/DECISIONS.md`.
5. Do **not** start any work and do not edit files.

## Then reply to Malik with (short, plain English)
- **Where we are:** current phase/week, last session's outcome, anything blocked.
- **Repo health:** uncommitted changes or anything odd in the git state above.
- **Open items that block the next step:** only the relevant ones, with their IDs.
- **Proposed goal for today:** exactly **one** roadmap item (by its PROGRESS ID), with:
  - what "done" means (its Definition of done)
  - the files likely touched (if > 3, say a plan will be shown first)
  - any major decision it will need (decision protocol), and any cost or cloud action
- End with: "OK to start <ID>?" and **wait**.
