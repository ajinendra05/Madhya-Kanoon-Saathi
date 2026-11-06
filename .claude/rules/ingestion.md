---
paths:
  - "src/madhya_kanoon_saathi/ingestion/**"
  - "scripts/**"
  - "notebooks/**"
  - "data/corpus_manifest.json"
---

# Ingestion rules

- Every downloaded file gets a manifest entry per `docs/specs/manifest.md` (DEC-040); IDs per
  `docs/specs/section_uid.md`. Validate with `ingestion/manifest.py` before committing the manifest.
  Changing either schema is a major decision.
- `mode=index` needs confirmed `status` + `commencement` verification records (index gate). Claude may confirm
  text/status against official sources; `interpretation` checks need Malik or an advocate.
- Download only from official sources (India Code, egazette.gov.in, labour.gov.in, MP Labour DMS, ministry portals).
  Aggregators (e.g., Vaquill) may bootstrap parsing but are never the cited source.
- Prefer the born-digital text layer; OCR (Bodhan) only when there is none. Record which path produced each page.
- Never machine-translate statute text. Hindi and English official texts are separate chunks sharing a `section_uid`.
- Chunk unit = sub-section with provisos/explanations attached, 150–450 tokens; keep the parent section reference.
- Keep page numbers through every step — citations need file + page.
- All text passes through the shared NFC + nukta-folding normaliser in `common/` before it is stored.
- Raw PDFs, OCR output and parsed text stay under git-ignored `data/` folders; never commit them.
- Scripts must be resumable (Colab sessions time out) and idempotent (re-running skips files whose sha256 matches).
- Network politeness: identify with a generic project User-Agent (never a personal email), rate-limit requests.
