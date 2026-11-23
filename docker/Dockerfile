# One image for both Cloud Run services (DEC-024, DEC-084, DEC-086): code + `serve` dependencies
# + int8 models + indexes + approved wording. Built by GitHub Actions, never on the laptop.
#   ingress: python -m madhya_kanoon_saathi.handlers.ingress
#   answer:  python -m madhya_kanoon_saathi.handlers.answer   (default CMD)
# Build context = repo root, with the release artifacts unpacked into data/ first.
# Only the files whitelisted in .dockerignore can reach the image (no .env, PDFs or fp32 models).

# uv 0.9.17 = the laptop's version, so uv.lock is read identically (ghcr.io digest, 2026-11-21)
FROM ghcr.io/astral-sh/uv:0.9.17@sha256:5cb6b54d2bc3fe2eb9a8483db958a0b9eebf9edff68adedb369df8e7b98711a2 AS uv

# python:3.12.16-slim-bookworm, Docker Hub digest read 2026-11-21 (tag updated 2026-11-05)
FROM python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first (cached layer): only the `serve` group, exactly as pinned in uv.lock
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-default-groups --group serve --no-install-project

# The package itself, installed non-editable into the venv
COPY src ./src
RUN uv sync --frozen --no-default-groups --group serve --no-editable

# Runtime data: what LocalRuntime, the pipeline and the handlers read (paths relative to /app)
COPY data/corpus_manifest.json data/contacts.yaml data/answer_texts.json \
     data/bot_texts.json data/help_topics.json data/instrument_aliases.json ./data/
COPY data/safety/crisis_examples.json data/safety/crisis_replies.json \
     data/safety/crisis_threshold.json data/safety/dispute_examples.json \
     data/safety/dispute_threshold.json ./data/safety/
COPY data/parsed/chunks.jsonl ./data/parsed/
COPY data/parsed_manifest/models.json ./data/parsed_manifest/
COPY data/index/bm25/ ./data/index/bm25/
COPY data/index/dense-int8/ ./data/index/dense-int8/
COPY data/models/bge-m3-int8/ ./data/models/bge-m3-int8/
COPY data/models/bge-reranker-v2-m3-int8-opt/ ./data/models/bge-reranker-v2-m3-int8-opt/

# Run as an unprivileged user; nothing in /app needs to be written at runtime
RUN useradd --system --uid 10001 mks
USER mks

CMD ["python", "-m", "madhya_kanoon_saathi.handlers.answer"]
