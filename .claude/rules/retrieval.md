---
paths:
  - "src/madhya_kanoon_saathi/retrieval/**"
  - "tests/**/test_*retriev*"
  - "tests/golden/**"
---

# Retrieval rules

- Index format, tokeniser behaviour and metadata filters are schema decisions — changes need Malik's approval.
- Tokeniser (DEC-026) is shared by index build and query time; never fork it. Every rule has a unit test with a real
  example (e.g., "धारा ८(१)(ज)" ↔ "section 8(1)(j)").
- FAISS: `IndexFlatIP` over L2-normalised vectors only (DEC-025). No HNSW/IVF without a new decision.
- Corpus and query embeddings must come from the same model file (checksum-pinned); the parity test must pass (DEC-022).
- int8 is accepted only if recall@10 ≥ fp32 − 0.02 overall and per language (DEC-021). Keep fp32 and top-20 paths
  configurable.
- Always apply filters: `state ∈ {MP, central}`, status, and validity on the query date.
- Report retrieval metrics per slice (language × domain × answerability), never only overall.
