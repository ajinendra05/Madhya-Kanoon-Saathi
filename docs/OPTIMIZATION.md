# Optimisation log: first deployment → second deployment (2026-11-23)

What changed in retrieval and the answer service after the first Cloud Run deployment
(image `bot:m5dd9a6afe7fb-187dea0`, app stack applied at commit `26278b7`), why, and what each change
did on the golden set. Commits `35e5c94` … `50913c4`. Decisions DEC-090 to DEC-093. Technical
background: [RERANKER.md](RERANKER.md). Raw results: [`reports/retrieval/opt_2026-11-23/`](../reports/retrieval/opt_2026-11-23/summary.md).

**Status: none of this is deployed yet.** The cloud still runs the first image.

---

## 1. Starting point (first deployment, measured 2026-11-23)

| Symptom | Measured | Cause found |
| --- | --- | --- |
| Every reply took 30–70 s, even with a warm container | Cloud Run logs + Firestore query records | the reranker scored 40 candidates one by one on 2 vCPU (30–50 s); embedding, search and the Sarvam call together < 2 s |
| First reply after ~15 idle minutes slower still | ~30 s extra | cold start (container start + 1.2 GB of models) |
| "What can you help with?" took 40 s | topic list needs no law text | retrieval ran before the pipeline noticed it was a topic question |
| Consumer questions in Hinglish ("dukaan vaale ne kharab saman diya") went unanswered | top 6 were e-Shram, SVANidhi, land forms | colloquial words share nothing with statute text; the right CPA sections never entered the candidate pool |
| One land-demarcation form appeared for unrelated questions | 1st place for 4 of 5 test questions | chunk `MP.LRCDR2018:form_i~2` was 24,671 characters, 98% dashes (a scanned table rule) |

---

## 2. Every change, and what happened to it

| ID | Change | Where | Decision | Kept? | Measured effect |
| --- | --- | --- | --- | --- | --- |
| **E2** | Remove separator rules (8+ dashes/`=`) and turn form blanks (4+ `_`) into "…" in all chunk text; build fails if a chunk is under 25% letters/marks/digits | `ingestion/chunker.py` (CHUNKER_VERSION 4) | DEC-090 | ✅ | 3 chunks changed, 0 QA errors; the junk chunk went from 24,671 to 398 characters and stopped winning |
| **A1** | Retrieval is lazy: runs only when the reply needs law text | `generation/service.py` | DEC-090 | ✅ | topic and other-state replies skip retrieval entirely (the 40 s case) |
| **A4** | Before reranking, drop mostly-filler candidates and duplicate passage texts | `generation/local.py` | DEC-090 | ✅ | part of "optimised" below |
| **A5** | Reranker window 1,024 → 256 tokens | `RetrievalConfig.rerank_window` | DEC-090 | ✅ | −19% mean / −26% p95 rerank time; R@6 −0.016, MRR −0.023 (101 golden rows) |
| **A7** | Cache of the last 256 retrievals per container | `generation/local.py` | DEC-090 | ✅ | instant on repeated questions (not in the benchmark: cache off for honest timing) |
| **B1** | ONNX Runtime threads = container vCPUs (`MKS_ORT_THREADS`), 1 inter-op thread, sequential | `retrieval/reranker.py`, `embedder.py` | DEC-090 | ✅ | prevents thread oversubscription in containers; **effect to be measured on Cloud Run** |
| **B3** | Reranker graph saved after ONNX Runtime's extended optimisation (`int8-opt`) | `scripts/optimize_reranker.py`, `models.json` | DEC-090 | ✅ | scores identical to plain int8 (max diff 0.00); saves graph-optimisation work at every container start (not measured) |
| **B7** | Reranker batch size configurable | `Reranker.batch_size` | DEC-090 | measured, **batch 1 kept** | 8.75 s at 1, 8.96 at 2, 9.35 at 4, 10.09 at 8; batching also changed int8 scores by up to ~1 logit |
| **D1** | Telegram "typing…" shown while an answer is prepared | `handlers/answer.py`, `bot/telegram.py` | DEC-090 | ✅ | user sees the bot is working (no speed change) |
| **E1** | **Query rewriting**: before search, a model turns the question into a formal English and a formal Hindi search query; BM25 + dense run for all three, fused by RRF; reranker reads question + English rewrite | `generation/rewrite.py`, `local.py` | DEC-090 | ✅ (prompt r1) | the large quality gain: R@6 0.583 → 0.713 at pool 40 (50 q) |
| E1 r2 | Prompt r2: law names in a separate list, kept only if they match an Act we index, official title appended | `rewrite.py` | DEC-091 | ❌ replaced | R@6 0.563 (worse on 10 questions, better on 1); appending full Act titles pulled search to generic sections; without titles 0.663 |
| **A2** | Reranker scores the top **20** fused candidates instead of 40 (each search list still gives 40) | `RetrievalConfig.pool` | DEC-091/093 | ✅ | ~2× less reranking; with r1: R@6 0.697 vs 0.713 at pool 40, time 7.0 s vs 15.3 s (50 q) |
| **A3** | One language version per provision in the pool (question's language preferred; separate parts kept) | `local.py` | DEC-091/093 | ✅ | frees pool slots taken by English + Hindi copies of the same rule |
| Free model | Rewriting moved from Sarvam (paid, ~₹0.004/question) to **Groq `qwen/qwen3.8-27b`** (free plan); question redacted before sending | `generation/free_llm.py` | DEC-092/093 | ✅ | 30 q: R@6 0.656 vs Sarvam 0.694 (per question 2 better, 2 worse); ~0.5–0.6 s per call |
| — | Groq `llama-3.3-70b-versatile` | — | DEC-092 | ❌ | no longer offered by Groq (HTTP 404; its `/models` list) |
| — | Groq `openai/gpt-oss-120b` | — | tested | ❌ | 30 q: R@6 0.622; added "Madhya Pradesh tenancy law" the user never said |
| — | On any Groq failure: use the original question | `rewrite.py`, `answer.py` | DEC-093 | ✅ | ₹0; the bot always answers; failure logged with HTTP status |

---

## 3. Results

### 3.1 50 golden questions (21 Hindi, 9 Hinglish, 20 English), laptop, rewriting on Sarvam

| Config | R@6 | R@10 | MRR@10 | Time mean / p95 |
| --- | --- | --- | --- | --- |
| Baseline (old index, window 1,024, pool 40) | 0.583 | 0.603 | 0.490 | 12.7 / 20.5 s |
| Speed changes only (E2, A4, A5, B1, B3, B7) | 0.603 | 0.623 | 0.470 | 10.2 / 17.7 s |
| + rewriting r1, pool 40 | **0.713** | **0.740** | 0.503 | 15.3 / 27.7 s |
| + rewriting r1, **pool 20 + A3** | 0.697 | 0.723 | 0.470 | **7.0 / 10.5 s** |
| rewriting r2 (titles appended), pool 20 + A3 | 0.580 | 0.630 | 0.456 | 7.3 / 11.1 s |
| rewriting r2 (no titles), pool 20 + A3 | 0.663 | 0.693 | 0.505 | 6.9 / 11.2 s |

Hinglish R@6: 0.444 (baseline) → 0.722 (r1, pool 40).

### 3.2 30 golden questions (11 Hindi, 9 Hinglish, 10 English): which model rewrites (r1, pool 20 + A3)

| Rewrite model | R@6 | R@10 | MRR@10 | R@6 hi / hinglish / en | Cost |
| --- | --- | --- | --- | --- | --- |
| none (baseline) | 0.572 | 0.572 | 0.528 | 0.561 / 0.444 / 0.700 | ₹0 |
| Sarvam-105B | **0.694** | **0.706** | 0.472 | 0.621 / 0.667 / 0.800 | ~₹0.004 |
| **Groq Qwen3.8-27B (chosen)** | 0.656 | 0.656 | **0.537** | **0.652** / 0.611 / 0.700 | **₹0** |
| Groq gpt-oss-120b | 0.622 | 0.656 | 0.498 | 0.561 / 0.611 / 0.700 | ₹0 |

Timings in 3.2 are not comparable across rows: the Sarvam row reused saved rewrites (no call time),
the Groq rows include their call and ran at a different time. Retrieval code is identical; the real
difference is the call itself (Qwen ~0.5–0.6 s, Sarvam ~1 s, measured separately).

### 3.3 What to expect on Cloud Run (estimate, not measured)
Laptop retrieval with the chosen setup is ~7 s mean (8 threads). Cloud Run has 2 vCPU, so expect
roughly 2–3× that before B1's effect is known, plus ~0.5 s for Groq and ~1 s for the Sarvam answer.
That is a large improvement on 30–70 s, but likely still above the 8 s warm target (DEC-020). Next
levers: graph fusion before quantisation (B2), a smaller reranker (C1), more vCPUs (B6).

---

## 4. Problems found on the way (and fixed)

| Problem | Effect | Fix |
| --- | --- | --- |
| Rewrite failures were silent (fallback hid them) | 20 of 50 rewrites lost in one run, invisible | failures logged (`rewrite_failed`, HTTP status); those rows re-run |
| Groq's Cloudflare blocks Python's default `Python-urllib` agent | HTTP 403 "error code: 1010" | plain project User-Agent `madhya-kanoon-saathi/0.1` (no personal details) |
| Dropped connections (`RemoteDisconnected`) were not mapped to the client's error type | caught only by the outer fallback | handled as `FreeLLMError` |
| Groq free plan unstable in one window | 32 of 60 calls failed; 1 of 60 in the re-run | fallback to the original question (DEC-093); watch `rewrite_failed` in logs |
| Committing while a benchmark wrote into the repo (Windows + pre-commit) | pre-commit's rollback reverted 102 unstaged spend-ledger lines | lines recovered from pre-commit's backup patch; rule: no commits during background jobs |
| Dynamic int8 quantisation makes scores depend on batch companions | batch > 1 gives different rankings | batch 1 kept (also fastest) |

---

## 5. Behaviour and data changes users and operators should know
- **Users:** see "typing…" while waiting; answers come from better-matched law text, especially for
  Hinglish; wording, disclaimers, quotas (20/day) and the ₹20/day cap are unchanged.
- **Privacy:** the question, after redaction, now goes to Groq (outside India) for rewriting only
  (DEC-092). Answers are still generated by Sarvam in India.
- **Cost:** rewriting ₹0; Groq free plan: 1,000 requests/day, 8,000 tokens/minute per model (reply
  headers, 2026-11-23).
- **Image:** gains `data/instrument_aliases.json` and the `int8-opt` reranker; rebuilt index (E2).
- **Cloud config to add:** `MKS_ORT_THREADS=2`, `MKS_RERANK_VARIANT=int8-opt`, secret `GROQ_API_KEY`.

---

## 6. Open items
- Measure the chosen setup on Cloud Run (warm and cold) and B1's effect.
- Re-check on the full golden set before the public demo (30–50-question samples; 1–2 question
  differences are noise).
- B2 graph fusion, C1 smaller reranker, B6 more vCPUs if Cloud Run is still above 8 s.
- Groq free-plan data location and terms (OPEN_QUESTIONS P18).

## 7. Interview summary
"Users waited 30–70 s. Profiling showed retrieval was the bottleneck, specifically a 568M-parameter
cross-encoder scoring 40 passages on 2 vCPUs, and quality failed on colloquial Hinglish. I measured
every change on the golden set: data cleanup removed a junk hit, query rewriting lifted Recall@6 from
0.58 to 0.71 (Hinglish 0.44 → 0.72), and a smaller, de-duplicated rerank pool halved retrieval time at
a ~1-point cost. I rejected a prompt variant that measured worse, moved rewriting to a free model after
comparing three, and made every failure fall back safely and show up in the logs."
