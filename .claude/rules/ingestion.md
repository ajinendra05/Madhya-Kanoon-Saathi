---
paths:
  - "src/madhya_kanoon_saathi/ingestion/**"
  - "scripts/**"
  - "notebooks/**"
  - "data/corpus_manifest.json"
---

# Ingestion rules

- Every downloaded file gets a manifest entry: `source_url, fetched_at, sha256, gazette_ref, valid_from, valid_to,
  status (in_force|draft|model_law|repealed|sub_judice_flag|passed_awaiting_assent|proposal), expires_on (optional),
  supersedes, local_path, s3_path` (DEC-033).
  Changing that schema is a major decision.
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
