# CLAUDE.md — Madhya Kanoon Saathi

**One-liner:** A Hindi-first legal-*information* (not advice) Telegram bot for Madhya Pradesh + central Indian laws.
Every claim cites a law clause, and code verifies the citation. The bot abstains when it lacks support.
It's built on always-free serverless AWS, and the eval report is the main deliverable.

**Roles:** Malik decides; Claude builds. Malik is preparing for applied-AI (SDE2) interviews, so explain every
technical choice with a 2–3 line plain-English "why".

## Sources of truth (read in this order)
- `docs/plan.md`: original plan (body unchanged). **`docs/DECISIONS.md` overrides it on any conflict.**
- `docs/DECISIONS.md`: every decision (DEC-NNN), imported below.
- Read on demand, not every session: `docs/CONCEPTS.md` (concepts and flows), `docs/TOOLS.md` (every tool/service),
  `docs/CORPUS.md` (which laws, by phase, with sources and status traps).
- Also: `docs/PROGRESS.md` (roadmap + session log), `docs/OPEN_QUESTIONS.md`, `docs/ARCHITECTURE.md`.
- Area rules load automatically from `.claude/rules/` when working in matching paths.

@docs/DECISIONS.md

## Locked stack (details + reasons in DECISIONS.md)
- Scope: MP + central law; Hindi, Hinglish, English. No Marathi (DEC-016).
- OCR: Bodhan IndicOCR. Born-digital text preferred (DEC-001).
- Retrieval: custom-tokenised BM25 (`bm25s`) + BGE-M3 int8 dense vectors in FAISS `IndexFlatIP`, merged with RRF.
  Then `bge-reranker-v2-m3` reranks top-40 → top-6. No vector DB; indexes ship in the Lambda image.
- Generation: Sarvam-105B default; Claude on Bedrock India `in.` profile as fallback + judge. Model IDs `TODO(verify)`.
- AWS ap-south-1, always-free: Telegram → Function URL → ingress Lambda → SQS → answer Lambda → `sendMessage`.
  DynamoDB for logs/dedup, EventBridge for schedules, S3 (versioned) for prod corpus, ECR for images,
  SSM Parameter Store for secrets. No VPC.
- CI/CD: GitHub Actions builds images + deploys via OIDC; Terraform for infra; GitHub Pages for the cost dashboard.

## Key commands
- Setup: `uv sync` · `uv tool install pre-commit` · `pre-commit install`
- Lint/format: `uv run ruff check .` · `uv run ruff format .`
- Types: `uv run mypy`
- Tests: `uv run pytest` (paid tests skipped; `-m paid` only with approval) · `uv run pytest -m golden`
- All hooks: `pre-commit run --all-files`
- Run bot locally: TBD (W2.5)

## Coding conventions
- Python package: `madhya_kanoon_saathi`. AWS resource prefix: `mks-`.
- Every module gets unit tests. Retrieval/citation code is also checked against golden-set rows once they exist.
- All text that is compared or indexed goes through the same Unicode NFC + nukta-folding normaliser.
- Never hard-code legal facts or contacts. They come from corpus files or `contacts.yaml`, with source + date.
- Config and secrets: names in `.env.example`; values only in `.env` (local) or SSM (prod). Never read, print or log them.
- Pin versions in the lockfile. Don't upgrade anything without asking.
- Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`. Commit after each logical unit.
- Never commit secrets, `.env`, model weights, raw PDFs, large data, or `docs/plan.doc`.

## Accuracy rules (no hallucination)
1. Legal content is never invented. Sections, quotes, dates, amounts and statuses come only from repo source files,
   with file path + page/section. If it's not in the corpus, say so.
2. APIs, model IDs, prices and library signatures are verified (official docs or installed package source), with the URL
   in a code comment or DECISIONS.md. If unverifiable: `TODO(verify)` + add it to OPEN_QUESTIONS.md.
3. Run it before claiming it works. Show the command and its real output.
4. Say "I don't know" or "not verified" plainly.
5. Small steps: one roadmap item at a time. If a change touches more than ~3 files, show a plan and wait for OK.
6. Stay on task. Anything else you notice goes to PROGRESS.md or OPEN_QUESTIONS.md.
7. Before context gets long, update PROGRESS.md.

## Decision protocol
**Major → ask first and wait.** Major means any of:
- changing anything locked in plan.md or DECISIONS.md
- adding or removing a dependency or external service
- anything that costs money or creates, changes or deletes cloud resources
- data schemas (golden set, chunk metadata, DynamoDB tables, index format)
- eval metrics or gates
- anything about what the bot tells users about the law (prompts, disclaimers, refusals)
- deleting files, large cross-module refactors, anything hard to undo
- licence/compliance

Ask in this format: **Decision needed → context (2–3 lines) → options A/B/C with trade-offs, cost, time →
recommendation + why.** After Malik decides, append a DEC-NNN entry to `docs/DECISIONS.md`. Never edit old entries;
supersede them.

**Minor → just do it and mention it in the session summary.** Covers code and tests inside an approved task, naming,
small refactors in files already being edited, docstrings, lint fixes, local scripts and tests, local commits.

When unsure, treat it as major.

## Docs maintenance
- New decision → `docs/DECISIONS.md` (next DEC number; update "Pending decisions").
- New concept, flow or technique introduced → `docs/CONCEPTS.md`.
- New tool, service, model or library (or one dropped) → `docs/TOOLS.md` (summary table + section).
- Unverified fact → `TODO(verify)` + `docs/OPEN_QUESTIONS.md`.

## Session protocol
- **Start (`/start-session`):** read CLAUDE.md, PROGRESS.md (incl. last session-log entry), OPEN_QUESTIONS.md,
  `git log -5`, `git status`. Report where we are, propose one roadmap item as today's goal, wait for OK.
- **End (`/end-session`):** run all checks; update PROGRESS.md (status + session log: done, decisions, problems,
  next step), OPEN_QUESTIONS.md, DECISIONS.md; final commit; show summary; ask before `git push`.

## Protected files (edit only with Malik's explicit approval)
`docs/DECISIONS.md` (append-only via the decision protocol) and `docs/CORPUS.md`, enforced by a hook (DEC-035).
Other files are edited freely. Conventions still apply: the plan.md body stays unchanged, and frozen golden-set
versions are never edited.

## Never
- Read or print `.env` or any secrets file. Run `rm -rf`, `git push --force` or `terraform destroy`.
- Push, create branches/repos, or call paid APIs beyond one tiny test without asking.
- Point users to private lawyers (BCI Rule 36). Escalate only to statutory free legal aid.
