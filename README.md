# Madhya Kanoon Saathi

A Hindi-first **legal-information** assistant (Telegram bot) for Madhya Pradesh and central Indian laws.
Every answer cites the exact clause it relies on, and code checks that citation. The bot says "I can't answer
that" when it lacks support, and points to free legal aid. **This is not legal advice.**

> Status: early development (setup, November 2026). Educational / research project (DEC-027).

## Why it's different
- **State-correct:** MP law + central law, with status flags (in force / draft / model law / under challenge) and a "law as of" date.
- **Verified citations:** each claim is tied to a retrieved chunk and an exact quote, and code validates it.
- **Measured:** a 120-question golden set, per-language eval report, and CI gates.
- **₹0 hosting:** always-free serverless AWS; no vector database (the index ships inside the app).

## Docs
| File | What's in it |
| --- | --- |
| [docs/plan.md](docs/plan.md) | Original build plan |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Every decision, which overrides the plan |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram + explanation |
| [docs/CONCEPTS.md](docs/CONCEPTS.md) | Key concepts and flows |
| [docs/TOOLS.md](docs/TOOLS.md) | Every tool and service used |
| [docs/PROGRESS.md](docs/PROGRESS.md) | Roadmap status + session log |
| [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) | Unverified facts and open items |

## Setup (Windows / macOS / Linux)
Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # create .venv with Python 3.12 + dev tools from uv.lock
uv tool install pre-commit   # once per machine
pre-commit install           # enable git hooks
cp .env.example .env         # then fill in values locally
```

## Checks
```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy                  # type check (src/)
uv run pytest                # tests (paid-API tests skipped; run with -m paid only when approved)
```

## Layout
`src/madhya_kanoon_saathi/` (common, ingestion, retrieval, generation, eval, bot, handlers) ·
`scripts/` · `data/` (manifest, contacts, golden set; raw data git-ignored) · `infra/terraform/` · `docker/` · `tests/`.

## Licence and data
Educational / research use. Statute text is cited to official sources (India Code, eGazette, state portals).
Third-party datasets are credited where used.
