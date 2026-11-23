# Reranker: how it is built, how it works, where it can be faster

Written 2026-11-23 from the code and model files in this repo, after the first Cloud Run test showed
30–70 s per answer. Everything marked *measured* was run; *estimate* means not measured yet.

Code: [`retrieval/reranker.py`](../src/madhya_kanoon_saathi/retrieval/reranker.py) (model + scoring),
[`retrieval/hybrid.py`](../src/madhya_kanoon_saathi/retrieval/hybrid.py) (pool, fusion, `rerank_hits`),
[`generation/local.py`](../src/madhya_kanoon_saathi/generation/local.py) (`LocalRuntime.retrieve`, used by the bot),
[`scripts/quantize_bge_m3.py`](../scripts/quantize_bge_m3.py), [`notebooks/reranker_export_colab.ipynb`](../notebooks/reranker_export_colab.ipynb).
Decisions: DEC-005 (self-hosted reranker), DEC-021 (int8, pool 40, fallbacks), DEC-062 (ONNX export),
DEC-066/067 (validation, in-force first), DEC-068 (RRF pool), OPEN_QUESTIONS S19 (latency).

---

## 1. What a reranker is, and why we have one

Retrieval happens in two stages:

| Stage | Method | Sees question and passage… | Speed | Precision |
| --- | --- | --- | --- | --- |
| 1. Candidate search | BM25 (words) + BGE-M3 vectors (meaning), fused with RRF | **separately** (each turned into tokens/vectors on its own) | milliseconds for all 3,410 chunks | coarse |
| 2. Reranking | **cross-encoder** `bge-reranker-v2-m3` | **together**, in one model input | one full model run per passage | fine |

A **bi-encoder** (stage 1) compresses each text into one vector without knowing the question, so it can be precomputed.
A **cross-encoder** (stage 2) reads `question + passage` as one sequence; every word of the question can attend to every
word of the passage, so it can judge "does this passage actually answer this?". That costs one full model run per
pair, so it only re-sorts a short list.

Measured value on golden v1.0 (62 indexed rows, strict, `reports/retrieval/v1.0_2026-11-20v1.0.md`):

| Config | Recall@6 (what Sarvam sees) | MRR@10 | s/query (laptop) |
| --- | --- | --- | --- |
| dense only | 0.457 | 0.342 | — |
| RRF pool 40 → **rerank int8** | **0.567** | **0.473** | 10.74 |
| RRF pool 40 → rerank fp32 | 0.567 | 0.488 | 26.26 |

The reranker adds ~11 points of Recall@6 and ~13 points of MRR. It is worth keeping; the work is to make it cheaper.

---

## 2. The model

| Property | Value | Source |
| --- | --- | --- |
| Model | `BAAI/bge-reranker-v2-m3`, Apache-2.0 | `export_info.json` |
| Revision | `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` (pinned) | `export_info.json` |
| Architecture | XLM-RoBERTa encoder: **24 transformer layers**, hidden size 1024, vocabulary **250,002** tokens, one-logit classification head | ONNX graph inspected 2026-11-23 |
| Weights | **568M** in total; ~256M of them are the word-embedding table (a lookup, little compute); ~300M in the 24 layers do the work | ONNX initializers |
| Input | `input_ids`, `attention_mask` (int64, shape `[batch, seq]`, both dynamic) | ONNX graph |
| Output | `logits` `[batch, 1]`: one relevance score per pair. Higher = more relevant. Only the order matters (not a probability). | ONNX graph |
| Languages | Multilingual (the XLM-R vocabulary covers Hindi and English; romanised Hindi is weaker in practice) | model family; Hinglish weakness observed 2026-11-23 |

### How the file was made
1. **Export (once, Google Colab, DEC-062).** PyTorch 2.14.1 + transformers 5.22.1 loaded the pinned revision and
   `torch.onnx.export` (TorchScript exporter, **opset 17**, dynamic batch and sequence axes) wrote `model.onnx` +
   `model.onnx.data` (2.27 GB fp32). Check: 4 pairs scored by PyTorch and ONNX differ by at most **4.3e-6**.
   No graph optimisation or operator fusion was applied at export.
2. **int8 (laptop, DEC-021/060).** `onnxruntime.quantization.quantize_dynamic(..., weight_type=QInt8)`:
   - *dynamic* quantisation: **weights** stored as 8-bit integers (per-tensor scale and zero point); **activations** are
     quantised on the fly at run time, so no calibration data was needed;
   - result: `model.int8.onnx`, **569 MB** (~4× smaller), with 146 `MatMulInteger` operations (24 layers × 6 matrix
     multiplications + the head);
   - int8 vs fp32 on golden v1.0: identical Recall@6, MRR −0.015 (DEC-066 check).
3. **Provenance.** Every file's sha256 is in `data/parsed_manifest/models.json`; `Reranker.load` refuses a file whose
   checksum differs. The int8 folder also carries `tokenizer.json`.

---

## 3. Loading (once per process)

`Reranker.load("int8", verify=True, max_length=1024, threads=None)`:
1. Looks up `bge-reranker-v2-m3-int8` in `models.json`, **re-hashes all files** (569 MB read once; part of cold start).
2. Creates an ONNX Runtime `InferenceSession` on `CPUExecutionProvider` with default `SessionOptions`;
   `intra_op_num_threads` is left unset (`threads=None`), so ONNX Runtime picks its own thread count.
3. Loads `tokenizer.json` with the Rust `tokenizers` library, **padding and truncation switched off** (our code builds
   the pairs itself, so it controls exactly what is cut).
4. Reads the `<pad>` id (1) for batching.

In the bot, `LocalRuntime.load()` does this at container start, before the port opens (Cloud Run startup probe).

---

## 4. Scoring one question: the exact steps

Called as `LocalRuntime.retrieve(question)` → `rerank_hits(reranker, question, rrf(...), passages, k=6)`.

### 4.1 Building the candidate pool (before the reranker)
1. BM25 top **40** and dense top **40**, both after the shared filters (MP or central; valid on the query date; not
   expired; flagged statuses kept but marked).
2. **RRF**: score = Σ 1/(60 + rank) over the two lists; ranks only (BM25 and cosine scores are not comparable).
   The fused **top 40** (up to 80 unique chunks before the cut) go to the reranker (DEC-068: pool recall 0.681 at 40).

### 4.2 What the reranker reads for each candidate
The **passage** is the same text the embedder used (DEC-061, `embed_text`):
```
<Act title in the chunk's language>
<heading path joined with " > ">
<chunk text>
```
Measured lengths over all 3,410 passages (reranker tokenizer, 2026-11-23): **median 111 tokens, p75 164, p90 243,
p99 497, max 1,657**; 9% are longer than 256 tokens, 1% longer than 512, one longer than 1,024.

### 4.3 Making the pairs (`Reranker.score`)
1. Tokenise the question once: `<s> question </s>`.
2. Tokenise all 40 passages in one call: `<s> passage </s>` each.
3. Build each pair exactly as the model's tokenizer would: `<s> question </s></s> passage </s>`
   (the question's `</s>` is repeated, the passage's `<s>` dropped; a unit test checks this against the real tokenizer).
4. **Window**: `max_length = 1024` tokens for the whole pair. Room for the passage = 1024 − question − 1. A longer
   passage keeps its first tokens and its closing `</s>`; the rest is cut and counted in `last_stats.truncated`.

### 4.4 Running the model
1. Pairs are **sorted by length** (shortest first).
2. Run in **batches of 1** (default `batch_size=1`): each pair is one `session.run` call with its exact length, so no
   padding work. Measured 2026-11-13 on the laptop: 20 passages took 5.4 s at batch 1, 6.2 s at 8, 13.9 s at 20,
   because padding a batch to its longest pair wastes work.
3. Each run: embedding lookup → 24 layers of self-attention + feed-forward over the whole pair → classification head
   → one logit. Cost grows with model size × pair length (attention part with length²).
4. Scores are written back in the original order.

### 4.5 After scoring (`rerank_hits`)
1. Sort the 40 by logit (stable: ties keep RRF order).
2. **In-force first** (DEC-067): a stable partition moves `draft`, `model_law`, `enacted_not_commenced`,
   `passed_awaiting_assent`, `proposal` chunks after all in-force ones (`sub_judice_flag` stays in place).
3. Keep the **top 6**; each carries its `rerank_score` (logged; not yet used as an abstention threshold).

---

## 5. Where the time goes (measured)

| Step | Laptop (i5-1155G7, 8 threads) | Cloud Run (2 vCPU) |
| --- | --- | --- |
| Question embedding + BM25 + FAISS + RRF | < 0.1 s | ~0.1 s |
| **40 reranker runs** | **11–25 s** (≈0.25–0.6 s per pair) | **≈30–50 s** |
| Sarvam generation (per call) | — | 0.65–1.05 s |

Per-pair cost: ~300M "working" weights × ~150 tokens ≈ tens of GFLOP per pair, done 40 times, one after another.
On 2 vCPUs that is the whole latency budget several times over (DEC-020 target: warm p95 < 8 s).

Two things make the Cloud Run number worse than "laptop × 4":
- **Thread count is not set.** ONNX Runtime may start more threads than the container's 2 vCPUs (not measured).
- **Retrieval runs even when no retrieval is needed** (topic questions; observed 2026-11-23: 40 s for a topic list).

Quality problems seen in the same test, which no speed change fixes:
- **Junk candidate**: `MP.LRCDR2018:form_i~2` is 24,671 characters, 98% dashes (a scanned table); its short declaration
  text + Act title scores high for unrelated questions and takes a top-6 slot.
- **Hinglish pool misses**: for "dukaan vaale ne kharab saman diya" the right CPA sections never enter the 40, so the
  reranker cannot rescue them.

---

## 6. Ways to make it faster (and what each costs)

Grouped by idea. *Speed-up* is an estimate unless marked measured; every quality-affecting change must be checked
on golden v1.0 (Recall@6, MRR@10, per language) before it ships (DEC-021 margin, DEC-066 rules).

### A. Do less work
| # | Change | Speed-up | Quality risk | Effort |
| --- | --- | --- | --- | --- |
| A1 | **Skip retrieval when the reply needs none** (topic list, crisis-only, other-state) | 100% for those messages | none | small |
| A2 | **Smaller pool**: rerank RRF top 20 (or 10) instead of 40 | ~2× (4×) — S19 measured 17.5 s / 11.0 s / 5.3 s at 40/20/10 | pool recall drops (DEC-068: 0.681 → 0.615 at 20; "no BM25 for Devanagari" recovers to 0.649) | config |
| A3 | **One language version per provision**: when both `@en` and `@hi` of the same `section_uid` are in the pool, rerank one and attach the other after | up to ~2× on bilingual Acts | low (same provision) | small |
| A4 | **Remove junk/duplicate candidates** (filler chunks, `~n` parts of one form) | small | positive | small |
| A5 | **Shorter window**: 1024 → 256 tokens | **measured 2026-11-23: −19% mean, −26% p95** (12.55 → 10.11 s; 728 of ~4,000 pairs cut) | **measured: R@6 −0.016, MRR −0.023 (indexed); R@10 unchanged; 64/101 top-6 lists changed** — not adopted alone ([report](../reports/retrieval/v1.0_2026-11-23_rerank_window.md)) | config |
| A6 | **Confidence gate**: skip the reranker when BM25 and dense agree on the top hits | varies | needs tuning on golden | medium |
| A7 | **Cache** reranked results per normalised question (repeat/FAQ questions) | 100% on repeats | none | small–medium |

### B. Do the same work faster
| # | Change | Speed-up | Quality risk | Effort |
| --- | --- | --- | --- | --- |
| B1 | **Set threads to the vCPU count** (`intra_op_num_threads=2`, `inter_op=1`) | avoids oversubscription; unknown, could be large in containers | none | config |
| B2 | **Transformer graph optimisation before quantisation** (`onnxruntime.transformers.optimizer`: fused attention, LayerNorm, GELU), then re-quantise | commonly 1.3–2× on CPU (*not verified for this model*) | tiny numeric change; re-check parity + golden | medium (one script) |
| B3 | **Save the optimised graph** (`SessionOptions.optimized_model_filepath`) | faster load (cold start), not per-query | none | small |
| B4 | **Better int8 kernels**: per-channel weights, S8S8 vs U8S8, check CPU has AVX-512 VNNI | maybe 1.2–1.5× (*not verified*) | small; re-check | medium |
| B5 | **OpenVINO execution provider** (Intel CPUs) | sometimes 1.5–3× on Intel (*not verified*; depends on Cloud Run CPU type) | parity check | new dependency (decision) |
| B6 | **More vCPUs** (4 or 8 per container) | ~1.7–1.9× per doubling (*estimate*) | none | config; uses free CPU-seconds faster |
| B7 | **Length-bucketed batching** (batch pairs of similar length) | small; batch 1 was fastest on the laptop | none | small |

### C. Use a smaller model
| # | Change | Speed-up | Quality risk | Effort |
| --- | --- | --- | --- | --- |
| C1 | **Smaller multilingual cross-encoder** (e.g. a ~280M "base" model or a ~120M MiniLM-type model) | 2–5× (*estimate*) | unknown on Hindi/Hinglish legal text; bake-off on golden | medium + decision |
| C2 | **Distil our own small reranker** from bge-reranker-v2-m3 scores on our corpus | 3–5× | needs training data and GPU time | large (later) |

### D. Hide or avoid the wait
| # | Change | Effect | Cost |
| --- | --- | --- | --- |
| D1 | Telegram **"typing…"** indicator (`sendChatAction`) while answering | users see the bot is working | ₹0 |
| D2 | **Keep one container warm** (min instances 1) | removes the ~30 s cold start only | continuous billing (decision) |
| D3 | **Load models faster**: skip the 569 MB re-hash in the image (checksums were checked at build), saved optimised graph | shorter cold start | none (hash checked in CI instead) |

### E. Better candidates (quality, not speed)
| # | Change | Effect |
| --- | --- | --- |
| E1 | **Query rewriting**: one cheap Sarvam call turns Hinglish into English + Hindi legal terms before stage 1 | the right sections enter the pool (main fix for "kharab saman"; also GS-075, GS-058) |
| E2 | Fix junk chunks at ingestion (filler cleanup + build-time QA failure) | removes the always-on false hit |

---

## 7. Suggested order (one at a time, each measured)
1. **E2 / A4** junk chunk → rebuild index (₹0).
2. **A1** skip retrieval when not needed (₹0).
3. **B1** threads = vCPUs; measure warm latency on Cloud Run before/after.
4. ~~**A5** window 256~~: measured 2026-11-23, −19% time for −0.016 R@6 / −0.023 MRR; not adopted on its own.
5. **A2 + A3** smaller pool + one language version per provision: measure pool recall and Recall@6.
6. **B2** graph optimisation + re-quantise: parity test + golden.
7. **D1** typing indicator (small UX win).
8. Decisions: **E1** query rewriting, **C1** smaller model bake-off, **B5/B6** OpenVINO or more vCPUs, **D2** warm instance.
