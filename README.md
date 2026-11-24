# Madhya Kanoon Saathi

A Hindi-first **legal-information** Telegram bot for Madhya Pradesh and central Indian law, in Hindi, Hinglish and
English. Every claim quotes the provision it relies on, code checks that the quote is in the retrieved law, and
the bot abstains when it has no support, pointing to free legal aid (DLSA, NALSA 15100).
**This is legal information, not legal advice.** Educational / research project (DEC-027).

> **Status (24 Nov 2026):** live on Google Cloud Run (Mumbai). Warm replies ~6.5 s; ₹0.023 model cost per answer.
> Full results, including known failures: **[docs/EVAL_REPORT.md](docs/EVAL_REPORT.md)**.

## What makes it different
- **State-correct:** MP + central law only, each source with a verified legal status (in force / draft / model law /
  not yet commenced) and a "law as of" date; other states' questions are declined.
- **Checked citations:** the answer model must return claims with exact quotes; any quote not found in the
  retrieved text is dropped, and the bot abstains if nothing survives.
- **Safety first:** a crisis router runs before anything else (100% recall on the crisis test splits), merits
  questions ("who is right?") get procedure + DLSA referral, personal and sensitive data is redacted before any
  log or external call.
- **Measured:** a 130-row golden set verified by a human, retrieval and answer metrics per language and domain,
  every design choice backed by a committed report.
- **Cheap to run:** no vector database (indexes ship in the container), scale-to-zero Cloud Run, free query
  rewriting, a ₹20/day spend cap and a 20-questions-per-chat daily quota.

## Results (golden v1.0, as deployed)

| Metric | Value |
| --- | --- |
| Retrieval Recall@10 / Recall@6 / MRR@10 (62 indexed rows, strict) | 0.667 / 0.642 / 0.527 |
| Answerable rows answered with an expected provision cited | 34 of 45 answered (45 of 60 answered) |
| Refer / abstain rows handled correctly | 18 / 19 |
| Crisis messages routed (golden / crisis-set holdout) | 5 / 5 · 20 / 20 |
| Warm reply time on Cloud Run (4 vCPU) | mean 6.5 s, max 8.1 s |

Known limits, including one wrong answer that passed the citation check, are in
[EVAL_REPORT.md §8](docs/EVAL_REPORT.md#8-known-failures-and-limitations).

## How it works
```
Telegram → ingress (secret check, dedup) → Pub/Sub → answer service (Cloud Run):
  crisis router → topic list → other-state guard → dispute detector
  → query rewrite (free LLM, redacted) → BM25 + BGE-M3 → RRF → int8 cross-encoder rerank → top 6
  → Sarvam-105B JSON claims with quotes → citation validator → reply with citations and caveats
```
Diagram and details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Docs
| File | What's in it |
| --- | --- |
| [docs/EVAL_REPORT.md](docs/EVAL_REPORT.md) | **Evaluation report** (main deliverable) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram and answer path |
| [docs/OPTIMIZATION.md](docs/OPTIMIZATION.md) | What changed after the first deployment, with measurements |
| [docs/RERANKER.md](docs/RERANKER.md) | Reranker internals and speed options |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Every decision (DEC-001 …), which overrides the plan |
| [docs/CONCEPTS.md](docs/CONCEPTS.md) | Concepts and flows, incl. the cloud setup step by step |
| [docs/CORPUS.md](docs/CORPUS.md) | Which laws, by phase, with sources and status traps |
| [docs/TOOLS.md](docs/TOOLS.md) · [docs/PROGRESS.md](docs/PROGRESS.md) · [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) | Tools, roadmap, unverified items |
| [docs/plan.md](docs/plan.md) | Original build plan |

## Setup
Requires [uv](https://docs.astral.sh/uv/). Models and indexes are large and not in git (private release; see
`data/artifacts.json`).
```bash
uv sync                      # Python 3.12 + pinned dependencies from uv.lock
uv tool install pre-commit && pre-commit install
cp .env.example .env         # fill in keys locally; never commit .env
```

## Checks and evaluation
```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
uv run python scripts/eval_retrieval.py --configs dense,rerank-int8,deployed --tag deployed
uv run python scripts/eval_answers.py --sample indexed --deployed --tag deployed   # cached answers re-score free
```
Paid model calls go through a hard ₹10 local cap (DEC-078); tests never call paid APIs unless marked `paid`.

## Run the bot locally
```bash
uv run python scripts/telegram_webhook.py delete   # only if the cloud webhook is set
uv run python scripts/run_bot.py                   # long polling; MKS_BOT_ALLOWED_CHATS limits who can use it
```

## Deploy (Google Cloud)
Terraform in `infra/terraform/bootstrap` (identities, IAM, Firestore, secrets, image store) and
`infra/terraform/app` (queue, services); image built by the **Build image** GitHub Actions workflow with keyless
login. Walkthrough: [CONCEPTS.md §10](docs/CONCEPTS.md).

## Layout
`src/madhya_kanoon_saathi/` (common, ingestion, retrieval, generation, eval, bot, handlers) · `scripts/` ·
`data/` (manifest, contacts, golden set, approved wording; raw data git-ignored) · `reports/` · `infra/terraform/` ·
`docker/` · `tests/`.

## Credits and licences
- Statute text is cited to official sources (India Code, eGazette, MP government portals); see `data/corpus_manifest.json`.
- Embeddings: [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) (MIT). Reranker: [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) (Apache-2.0).
- OCR: Built with IndicOCR from Bodhan AI / AI4Bharat (Indic Open Model License v1.0).
- Answer generation: Sarvam AI (Sarvam-105B). Query rewriting: Groq (open-weight Qwen model).
- Educational / research use, non-commercial (DEC-027).
