# Madhya Kanoon Saathi: evaluation report

**Version:** 2026-11-24 · deployed image `bot:m5dd9a6afe7fb-2658fd5` (artifacts `v2026.11.23`) ·
golden set v1.0 (sha256 `386f40b8…`). Every number below comes from a committed report in
[`reports/`](../reports/) or [`docs/eval/`](eval/); each section names its source. Nothing is
estimated unless it says so.

Madhya Kanoon Saathi is a Telegram bot that gives **legal information, not legal advice**, about
Madhya Pradesh and central Indian law, in Hindi, Hinglish and English. Every claim must quote a
provision from the indexed corpus, code checks that the quote exists in what was retrieved, and the
bot abstains when it has no support. Escalation goes only to statutory free legal aid (DLSA, NALSA 15100).

---

## 1. Summary

| What | Result (deployed setup) | Source |
| --- | --- | --- |
| Retrieval, strict Recall@10 / Recall@6 / MRR@10 (62 golden rows whose law is indexed) | **0.667 / 0.642 / 0.527** (dense-only 0.527 / 0.476 / 0.341) | §4 |
| Retrieval on clearly answerable rows (41): Recall@10 / MRR@10 | **0.813 / 0.606** | §4 |
| Hinglish Recall@10 / MRR@10 (9 rows) | 0.611 / 0.522 (before query rewriting 0.444 / 0.259) | §4 |
| Answer-level, 84 golden rows: should answer → answered | 45/60 (answer 32/41, with caveat 13/19) | §5 |
| Answered rows that cited an expected provision | 34/45 | §5 |
| Should refer / abstain → did | 18/19 | §5 |
| Crisis messages routed to the crisis reply (golden) / caught by the router (crisis set, all splits) | 5/5 / 80/80 | §5, §6 |
| Known wrong answer in the eval | 1 (GS-005, see §8) | §8 |
| Warm reply time on Cloud Run (4 vCPU), 10 golden questions | mean **6.5 s**, max 8.1 s | §7 |
| Model cost per answer (Sarvam, GST incl.) / query rewriting | **₹0.023** / ₹0 (Groq free plan) | §7 |
| Plan gates (Recall@10 ≥ 0.85, MRR@10 ≥ 0.60 on indexed rows) | **not met** (0.667, 0.527) | §4 |

---

## 2. System under test

```
Telegram → ingress (secret header, dedup) → Pub/Sub → answer service (Cloud Run, 4 vCPU):
  crisis router → topic list? → jurisdiction guard → dispute detector
  → query rewrite (Groq qwen/qwen3.8-27b, question redacted first; failure = original question)
  → BM25 + BGE-M3 int8 dense (question + 2 rewrites) → RRF → filters (A4, one version per provision)
  → top 20 → cross-encoder bge-reranker-v2-m3 int8 (window 256) → in-force law first → top 6
  → Sarvam-105B answer as JSON claims with quotes → citation validator (exact quote in retrieved text)
  → render with citations, status caveats, "law as of", not-legal-advice footer
```
Decisions: DEC-003/004/005 (retrieval), DEC-021/066 (int8), DEC-067 (in-force first), DEC-068 (RRF),
DEC-077/079 (generation, wording), DEC-086–094 (cloud and optimisation). Change history:
[OPTIMIZATION.md](OPTIMIZATION.md).

**Corpus (indexed):** RTI Act + RTI Rules 2012; Consumer Protection Act 2019 + Jurisdiction and
E-Commerce Rules; the four Labour Codes; MP minimum-wage notification Oct 2026 (with a legal
qualification, DEC-050); MP Code on Wages Rules (draft, labelled); Transfer of Property Act ss.105–111,
Registration Act s.17, Model Tenancy Act (model law, labelled); MP land demarcation (MPLRC s.129 +
Demarcation Rules 2018); Legal Services Authorities Act (ss.12–22B); PM SVANidhi guidelines; e-Shram
FAQ; MP legal-aid guide. 3,410 chunks. Gated (not answerable yet): MP mutation, MP RTI fee rules,
Lok Seva deadlines, MP Shops Act, and others (CORPUS.md).

---

## 3. Golden set and method

**Golden v1.0** (`data/golden/v1.0/golden_set_v1.0.jsonl`, frozen 2026-11-19, DEC-081): **130 rows,
all verified by Malik**. Synthetic questions written for this project (no real-user questions yet:
roadmap W0.1 is open), each with expected behaviour, expected provisions, key facts and
`must_include` / `must_not_include` patterns.

| Language | Rows | | Expected behaviour | Rows |
| --- | --- | --- | --- | --- |
| Hindi | 56 | | answer | 59 |
| English | 55 | | answer with caveat | 44 |
| Hinglish | 19 | | abstain / refer | 19 |
| | | | crisis route | 5 |
| | | | ask clarifying | 2 |
| | | | gated | 1 |

Domains: tenancy 24, labour 24, consumer 20, RTI 18, public services 12, land 10, legal aid 8,
schemes 6, crisis 4, status 4. **101 rows** name expected provisions; **62** of them name only
provisions that are indexed today (the "indexed" set). The other 39 cite law that is gated or out of
corpus and measure corpus gaps, not retrieval (`data/golden/v1.0/coverage.md`).

**Retrieval metrics** (DEC-065): strict = a retrieved chunk equals or contains the expected provision
(DEC-040 `covers`); lenient also accepts a part of it. Recall@k = share of expected provisions in the
top k; Recall@6 = what the answer model sees; MRR@10 = 1 / rank of the first correct chunk; nDCG@10
with binary gain. Reported per language, domain and answerability.

**Answer metrics** (deterministic, no LLM judge yet): behaviour (answered / abstained / referred /
crisis reply as expected), cited an expected provision (lenient), all `must_include` patterns present,
no `must_not_include` pattern present.

---

## 4. Retrieval results

Source: [`reports/retrieval/v1.0_2026-11-24deployed.md`](../reports/retrieval/v1.0_2026-11-24deployed.md)
(101 rows; `deployed` = the cloud's exact retrieval, rewrite failures 0). That file's header line
"Seed set: synthetic, unverified" is outdated generator text (golden v1.0 is verified, DEC-081); the
generator is fixed for later runs.

### 4.1 Indexed rows (62), strict

| Config | R@10 | R@6 | MRR@10 | nDCG@10 | s/query (laptop) |
| --- | --- | --- | --- | --- | --- |
| Dense only (BGE-M3 int8) | 0.527 | 0.476 | 0.341 | 0.378 | |
| Hybrid + rerank, pool 40, window 1,024 (pipeline before DEC-090) | 0.616 | 0.583 | 0.470 | 0.491 | 16.55 |
| **Deployed** (rewrite + pool 20 + one version per provision + window 256) | **0.667** | **0.642** | **0.527** | **0.542** | **11.21** |
| Deployed, lenient | 0.723 | 0.699 | 0.581 | 0.596 | |

### 4.2 Slices (indexed rows, strict R@10 / MRR@10)

| Language | Rows | Dense | Rerank (old) | Deployed |
| --- | --- | --- | --- | --- |
| English | 28 | 0.625 / 0.388 | 0.679 / 0.500 | **0.714 / 0.583** |
| Hindi | 25 | 0.527 / 0.363 | 0.607 / 0.513 | 0.633 / 0.466 |
| Hinglish | 9 | 0.222 / 0.133 | 0.444 / 0.259 | **0.611 / 0.522** |

| Domain | Rows | Rerank (old) | Deployed |
| --- | --- | --- | --- |
| Labour | 20 | 0.633 / 0.517 | 0.717 / 0.517 |
| Consumer | 17 | 0.618 / 0.468 | 0.647 / 0.466 |
| RTI | 12 | 0.500 / 0.326 | **0.667 / 0.625** |
| Legal aid | 6 | 0.750 / 0.583 | 0.750 / 0.486 |
| Tenancy | 4 | 0.750 / 0.750 | 0.750 / 0.750 |

| Answerability | Rows | Rerank (old) | Deployed |
| --- | --- | --- | --- |
| Answerable | 41 | 0.748 / 0.598 | **0.813 / 0.606** |
| Partly answerable | 19 | 0.342 / 0.239 | 0.421 / 0.412 |

**All 101 rows:** deployed strict R@10 0.432, MRR@10 0.347: the 39 rows citing gated or missing law
pull this down (corpus gap, by design: the bot must abstain there).

### 4.3 Design choices, each measured

| Choice | Evidence | Source |
| --- | --- | --- |
| BGE-M3 over multilingual-e5-large | strict R@10 0.559 vs 0.540 (fp32, 62 rows); e5 weaker on Hindi (0.480 vs 0.567) | `reports/retrieval/v0.1-seed_2026-11-18_bakeoff_e5.md` |
| int8 reranker instead of fp32 | R@10 0.583 vs 0.589, paired 95% CI [−0.016, 0]: **pass** (DEC-021 margin 0.02) | `reports/retrieval/v1.0_2026-11-20v1.0_precision.md` |
| int8 dense model alone | 0.511 vs 0.575: **fails** the margin overall; acceptable only because the reranker re-sorts the pool (full path passes) | same (OPEN_QUESTIONS S32) |
| RRF (BM25 + dense) over dense-only | pool recall at 40: 0.681 vs 0.647 | `reports/retrieval/v0.1-seed_2026-11-14_fusion.md` (DEC-068) |
| Query rewriting prompt r1 over r2 (Act-name list) | R@6 0.713 vs 0.563 (50 rows) | `reports/retrieval/opt_2026-11-23/summary.md` (DEC-093) |
| Groq Qwen3.8-27B for rewriting | R@6 0.656 vs Sarvam 0.694 (30 rows; per row 2 better, 2 worse) at ₹0 | same |
| Rerank pool 20 over 40 | R@6 0.697 vs 0.713, time 7.0 s vs 15.3 s (50 rows, laptop) | same |
| Reranker window 256 over 1,024 | −19% time, R@6 −0.016 | `reports/retrieval/v1.0_2026-11-23_rerank_window.md` |
| Batch size 1 | fastest (8.75 s vs 10.09 s at batch 8) and deterministic | [RERANKER.md](RERANKER.md) |

---

## 5. Answer-level results (as deployed)

Source: [`reports/answers/v1.0_2026-11-24_deployed_v1.md`](../reports/answers/v1.0_2026-11-24_deployed_v1.md)
(84 rows: all answerable-now rows plus every refer and crisis row; Sarvam-105B, prompt v1; 106 paid
calls; rewrite failures 0).

| Expected | Rows | Behaviour as expected | Cited an expected provision | All `must_include` | No `must_not_include` |
| --- | --- | --- | --- | --- | --- |
| answer | 41 | 32/41 | 28/32 | 27/41 | 40/41 |
| answer with caveat | 19 | 13/19 | 6/13 | 16/19 | 19/19 |
| abstain / refer | 19 | 18/19 | 1/2 | 15/19 | 19/19 |
| crisis route | 5 | 5/5 | – | 5/5 | 5/5 |

By language (answer + caveat rows answered): English 24/28, Hindi 15/23, Hinglish 6/9. By domain:
consumer 12/17, labour 15/19, RTI 8/12, legal aid 5/6, tenancy 4/4.

**Why answerable rows abstain** (15 of 60): in 11, every quote the model produced failed the exact-match
check against the retrieved text, so the validator removed all claims and the bot abstained (the
safety rule working; a quote-copying weakness, not missing law). The other 4 abstained because the
model judged the excerpts insufficient (e.g. no fixed demarcation fee amount exists in the corpus, which
is correct: fees are set per district, DEC-046).

**Compared with the previous full run** (2026-11-18, unverified seed labels, pipeline before the
optimisations; 59 rows with the same label in both): 10 rows newly answered, 7 newly abstained;
rows citing an expected provision +7 / −1.

---

## 6. Safety

| Check | Result | Source |
| --- | --- | --- |
| Crisis router recall (crisis set v0, synthetic) | dev 24/24, test 36/36, **holdout 20/20** (holdout written with new wording, not used for tuning) | `reports/safety/crisis_2026-11-17.md` |
| Crisis rules alone on holdout | 1/20: the embedding layer catches paraphrases (DEC-075) | same |
| Crisis false alarms on ordinary questions | 8/20 dev, 6/20 test, 5/10 holdout, all "note" tier (one safety line added to a normal answer, DEC-075) | same |
| Golden crisis rows → full crisis reply | 5/5 | §5 |
| Dispute detector ("who is right" → procedure + DLSA) | merits caught: dev 11/11, test 15/15, holdout 8/8; false alarms 1/30 procedural | `reports/safety/dispute_2026-11-18.md` |
| Redaction (PII + volunteered caste/religion/disability/health) before any log or external call | 26 unit tests; applied before Firestore writes and before the Groq rewrite | `common/redact.py`, DEC-076/092 |
| Other-state guard (MP + central only) | abstains on other states' laws | `generation/jurisdiction.py` |
| Abuse and cost limits | 20 questions per chat per day; ₹20/day model-spend cap enforced in Firestore | DEC-088 |

The crisis and dispute sets are synthetic and partly written by the same author as the rules, so the
dev/test numbers are optimistic; the holdout splits are the honest signal.

### OCR quality (scanned sources)
20 pages hand-corrected by Malik ([`docs/eval/ocr_bakeoff.md`](eval/ocr_bakeoff.md)): character error
rate, Bodhan IndicOCR vs Tesseract: all pages 13.6% vs 17.7%; **Hindi Act text 2.5% vs 6.1%**; degraded
scans 3.3% vs 34.9%; wage tables 42.4% vs 38.1% (both poor: wage rows are therefore checked by
arithmetic at build time, DEC-071). OCR-derived answers carry a "from a scanned copy" label (DEC-077).

---

## 7. Latency and cost

Source: `reports/cloud/timing_cpu2.jsonl`, `timing_cpu4.jsonl` (10 golden questions after one
warm-up, published to the live queue, timed by the answer service's own record).

| Answer service | Warm mean | p50 | Max |
| --- | --- | --- | --- |
| First deployment (before optimisation) | 30–70 s | | |
| 2 vCPU | 10.2 s | 10.5 s | 12.8 s |
| **4 vCPU (deployed, DEC-094)** | **6.5 s** | **6.5 s** | **8.1 s** |

Groq rewrite 0.14–0.43 s; Sarvam answer 0.29–0.93 s; retrieval (mostly reranking) the rest.
**Cold start not measured yet.**

**Cost:** model spend per answer **₹0.023** incl. GST (22 cloud answers, 1.36 Sarvam calls each);
query rewriting ₹0 (Groq free plan: 1,000 requests/day, 8,000 tokens/minute). Hosting runs on the
Google Cloud trial credit until 20 Feb 2027; estimated free-allowance capacity ~6,900 answers/month on
4 vCPU (asia-south1 eligibility unverified, OPEN_QUESTIONS P13).

---

## 8. Known failures and limitations

1. **Wrong answer that passes validation (GS-005).** "Does an 11-month rent agreement have to be
   registered?" → "must be registered", quoting Registration Act **s.17(1)(b)**. The quote is genuine,
   so the validator accepted it, but leases fall under **s.17(1)(d)** (year to year or more than a
   year): an 11-month lease is not compulsorily registrable. The validator proves a quote *exists*, not
   that it *supports* the claim (OPEN_QUESTIONS S33). Planned fix: a claim-support check by a free
   model, measured on labelled examples before it gates anything (DEC-081).
2. **Plan gates not met.** Recall@10 0.667 and MRR@10 0.527 on indexed rows vs targets 0.85 / 0.60;
   15 indexed rows are missed by every configuration (listed in the retrieval report), mostly
   consumer definitions (CPA s.2(11), s.2(42), s.2(47)) asked in everyday words, and labour rows that
   name a whole Code.
3. **Abstention from quote copying.** 11 answerable rows abstained because the model's quotes did not
   match the source text exactly (safe, but unhelpful).
4. **Hindi answers.** Answered 15/23 Hindi rows vs 24/28 English.
5. **No guard for questions about a past period** (S34): e.g. wages for April–September 2026.
6. **Synthetic evaluation data.** Golden, crisis and dispute questions are synthetic (golden verified
   by Malik; crisis and dispute sets not yet reviewed). Real user questions (W0.1) are not in the set.
7. **Small slices.** Hinglish has 9 indexed rows; differences of 1–2 rows are noise. Comparisons on 30
   or 50 rows (OPTIMIZATION.md) are indicative only.
8. **Free-plan dependency.** Groq had one window where 32 of 60 rewrite calls failed; the bot then
   answers without rewriting (lower recall for Hinglish). Questions sent to Groq are redacted but leave
   India (DEC-092).
9. **Corpus gaps by design.** 39 of 101 golden rows cite law that is gated or not yet in the corpus
   (mutation, MP RTI fees, Lok Seva deadlines, …); the bot abstains on them.
10. **No LLM judge yet.** Faithfulness and κ calibration (plan §7, W2.3/W2.4) are not measured.

---

## 9. Reproduce

```
uv sync
uv run python scripts/eval_retrieval.py --configs dense,rerank-int8,deployed --tag deployed
uv run python scripts/eval_answers.py --sample indexed --deployed --tag deployed   # cached answers: free
uv run python scripts/compare_optimisations.py --rows 50                            # resumes from saved rows
uv run python scripts/cloud_timing.py --label cpu4 --n 10                           # live service, ~₹0.3
```
Models, indexes and chunks: private release `v2026.11.23` (checksums in `data/artifacts.json`).
`deployed` runs need `GROQ_API_KEY`; paid answer calls go through the ₹10 local cap (DEC-078) and are
cached in `data/eval/llm_cache.jsonl`, so re-scoring is free.

## 10. Next
1. Claim-support check for S33 (free judge model), then re-run §5.
2. Real user questions (W0.1) into golden v1.1; review the crisis and dispute sets.
3. Retrieval misses in §8.2 (definitions asked in everyday words; whole-Code rows).
4. Cold-start measurement; B2 graph fusion if replies need to get faster.
