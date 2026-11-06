---
paths:
  - "src/madhya_kanoon_saathi/eval/**"
  - "data/golden/**"
  - "tests/golden/**"
---

# Eval rules

- Frozen golden-set versions (e.g., `data/golden/v1.0.jsonl`) are protected: never edit; add rows in a new version.
- Golden-set schema, metrics and pass/fail gates are major decisions.
- Golden rows are stored redacted only (no names, phones, addresses).
- Deterministic scorers (recall@k, MRR, nDCG, citation precision, quote exact match) need no LLM and run in CI.
- Judged runs (faithfulness, κ) are on demand only in v1 and use the judge cache (DEC-023). Ask before a full run;
  state the expected cost first.
- Latency gate applies to warm requests; report cold starts separately (DEC-020).
- Every report breaks results down by slice (language × domain × answerability).
