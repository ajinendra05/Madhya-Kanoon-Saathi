# Tools, services and techniques — Madhya Kanoon Saathi

Every external service, model, library and dev tool the project uses (or considered and dropped), with what it is,
how we use it, why we chose it, and its cost or limits. Concepts behind them are in `CONCEPTS.md`; the reasons are in
`DECISIONS.md`.

**Status legend:** `decided` (in DECISIONS.md) · `planned` (in plan.md, not yet re-decided) · `proposed` (awaiting
Malik's approval, e.g., kickoff step 2) · `later` (after the November demo) · `dropped`.

**Verification rule.** Prices, free-tier limits, model sizes and IDs below are **not verified** unless a doc link and
check date are given. Verify against the official page before code depends on it, then add `Verified: <url>, <date>`.

**Add a tool:** copy the template below into the right section and add a row to the summary table.

```
### <Tool name>  — status
- What: one line
- How we use it: where in the pipeline / repo
- Why: reason + DEC link
- Cost / limits: (not verified unless linked)
- Alternatives considered:
- Verified: <url>, <date>   ← or TODO(verify)
```

---

## Summary

| Area | Tool | Role | Status |
| --- | --- | --- | --- |
| AWS | Lambda (container image) | Ingress, answer, law-watch, nightly cost summary | decided (DEC-002) |
| AWS | Lambda Function URL | Public HTTPS endpoint for the Telegram webhook | decided (DEC-002, 010) |
| AWS | SQS + dead-letter queue | Queue between ingress and answer Lambdas | decided (DEC-010) |
| AWS | DynamoDB | Dedup, query log, cost log, quotas | decided (DEC-002); schema pending |
| AWS | EventBridge Scheduler/rules | Weekly law-watch; nightly cost summary | decided (DEC-012, 013) |
| AWS | S3 | Production raw corpus, versioned | decided (DEC-011) |
| AWS | ECR | Stores Lambda container images | decided (DEC-024) |
| AWS | SSM Parameter Store | Secrets (SecureString) | decided (DEC-009) |
| AWS | KMS | Encryption for SSM / S3 / DynamoDB | decided (DEC-029) |
| AWS | IAM | Least-privilege roles; GitHub OIDC role | decided (DEC-019, 029) |
| AWS | CloudWatch Logs + Alarms | Logs (PII-redacted), metrics, alarms | planned |
| AWS | AWS Budgets | ₹100 budget alert | decided (DEC-002, 019) |
| AWS | Amazon Bedrock (Claude) | LLM fallback + LLM-as-judge | decided (DEC-006) |
| AWS | X-Ray / OpenTelemetry | Per-query traces | planned |
| GitHub | Repo, Actions, OIDC, Pages, Issues | Code, CI/CD, image builds, dashboard, law-watch alerts | decided |
| Models | Sarvam-105B | Default answer generator | decided (DEC-006) |
| Models | BGE-M3 | Embeddings (dense) | decided (DEC-004) |
| Models | multilingual-e5-large | Embedding bake-off challenger | decided (DEC-004) |
| Models | bge-reranker-v2-m3 | Cross-encoder reranker | decided (DEC-005) |
| Models | Bodhan IndicOCR | OCR for scanned PDFs | decided (DEC-001) |
| Models | Tesseract `hin` | OCR baseline in bake-off | decided (DEC-014) |
| Models | Sarvam Document Digitization | OCR comparison in bake-off only (~₹10) | decided (DEC-014) |
| Library | FAISS | Exact vector search (`IndexFlatIP`) | decided (DEC-003, 025) |
| Library | bm25s | Keyword (BM25) search | decided (DEC-003) |
| Library | pypdf | PDF text-layer detection + extraction | decided (DEC-041) |
| Library | pypdfium2 + Pillow | Render PDF pages to images (OCR input, visual checks) | decided (DEC-053) |
| Library | ONNX Runtime | Runs int8/fp32 models on CPU in Lambda | decided (DEC-021) |
| Library | Ragas, DeepEval | RAG metrics, pytest-style eval assertions | planned |
| Dev | Terraform | Infrastructure as code | planned |
| Dev | Docker | Build Lambda images (in CI) | decided (DEC-024) |
| Dev | pre-commit + gitleaks | Lint/format + secret scanning before commits | proposed (kickoff) |
| Dev | Python toolchain (version, package manager, linter, test runner) | — | proposed (kickoff step 2) |
| Dev | Claude Code | Implementation partner, with hooks/permissions/skills | in use |
| Compute | Google Colab | Bulk OCR on free GPU | decided (DEC-015) |
| Channel | Telegram Bot API | The only user channel for v1 | decided (DEC-007) |
| Ops | Google Sheets | Logging validation questions before they become golden rows | planned (plan §1) |
| Data | India Code, eGazette, MP Labour DMS, ministry portals | Primary legal sources | planned (plan §2) |
| Data | Vaquill open-india-law (CC BY 4.0) | Bootstrap for section parsing; never cited directly | planned (plan §2) |

---

## 1. AWS (region ap-south-1, Mumbai)

### AWS Lambda — decided (DEC-002)
- **What:** Runs our code on demand in response to events; no server to manage. Supports container images.
- **How we use it:** Four functions:
  - **ingress:** small; checks the webhook, dedupes, enqueues.
  - **answer:** container image with models + index; does retrieval, reranking, generation and validation.
  - **law-watch:** weekly; fetches sources and compares checksums.
  - **cost-summary:** nightly; aggregates `cost_log`.
- **Why:** Idle most of the time, so we pay only for use. Always-free tier covers our volume.
- **Cost / limits (not verified):**
  - always-free: 1M requests + 400K GB-seconds per month
  - memory 128 MB–10,240 MB; CPU scales with memory (~1 vCPU per ~1.8 GB)
  - container image up to 10 GB
- **Watch out for:** cold starts (DEC-020); answer-Lambda memory sizing (DEC-021).
- **Verified:** TODO(verify)

### Lambda Function URL — decided (DEC-010)
- **What:** A built-in HTTPS URL for a Lambda, no API Gateway needed.
- **How we use it:** Telegram's webhook target (ingress Lambda only). Auth type NONE at the URL level; we verify
  Telegram's `X-Telegram-Bot-Api-Secret-Token` header in code.
- **Why:** Free. Replaces API Gateway from the plan.
- **Verified:** TODO(verify)

### Amazon SQS (+ dead-letter queue) — decided (DEC-010)
- **What:** Managed message queue.
- **How we use it:** The ingress Lambda sends each new message to SQS. The answer Lambda is triggered by SQS. After repeated
  failures a message moves to a DLQ for inspection. Answer-Lambda concurrency is capped to protect Sarvam's rate limit.
- **Cost (not verified):** always-free 1M requests/month.
- **Verified:** TODO(verify)

### Amazon DynamoDB — decided (DEC-002); table design pending (R10)
- **What:** Serverless key-value / document database.
- **How we use it:** `seen_updates` (Telegram dedup), query log, `cost_log` (₹ per step), per-user quotas. TTL deletes
  raw chats after 90 days (DPDP).
- **Why:** Always-free; no server. Not good at ad-hoc aggregation, so the dashboard uses a nightly summary (DEC-012).
- **Cost / limits (not verified):** always-free 25 GB storage + 25 RCU / 25 WCU. That likely applies to *provisioned*
  capacity mode; on-demand mode may bill per request. Decide before creating tables.
- **Verified:** TODO(verify)

### Amazon EventBridge — decided (DEC-012, 013)
- **What:** Scheduler and event bus.
- **How we use it:** Weekly trigger for law-watch; nightly trigger for cost summary; later, a 5-min keep-warm ping
  (DEC-020, v2).
- **Cost (not verified):** scheduled rules are free or near-free at our volume.
- **Verified:** TODO(verify)

### Amazon S3 — decided (DEC-011)
- **What:** Object storage.
- **How we use it:** Production copy of raw PDFs and parsed JSON, with **versioning on** (audit trail of law text);
  eval artifacts. In development, PDFs stay on the laptop.
- **Cost (not verified):** < 1 GB ≈ a few ₹/month; covered by credits.
- **Verified:** TODO(verify)

### Amazon ECR — decided (DEC-024)
- **What:** Private registry for container images.
- **How we use it:** Stores answer-Lambda images pushed by GitHub Actions; lifecycle rule keeps the last 3.
- **Cost (not verified):** ~$0.10/GB-month → ~₹15–45/month for 1.5–5 GB.
- **Verified:** TODO(verify)

### AWS Systems Manager Parameter Store — decided (DEC-009)
- **What:** Key-value store for config and secrets; `SecureString` values are KMS-encrypted.
- **How we use it:** Sarvam API key, Telegram bot token, webhook secret token, GitHub token (for law-watch issues). Read
  once per cold start, cached in memory, never logged.
- **Cost (not verified):** standard tier free.
- **Alternative dropped:** AWS Secrets Manager (~$0.40/secret/month, not verified).
- **Verified:** TODO(verify)

### AWS KMS — decided (DEC-029)
- **What:** Key management for encryption.
- **How we use it:** AWS-managed keys encrypt SSM SecureStrings, S3 and DynamoDB at rest. No customer-managed keys
  in v1 (they cost ~$1/month each, not verified).

### AWS IAM — decided (DEC-019, 029)
- **What:** Identities and permissions.
- **How we use it:** One least-privilege role per Lambda; a GitHub OIDC role for CI deploys (no stored keys); Malik's
  root account with MFA, never used for daily work.

### Amazon CloudWatch — planned
- **What:** Logs, metrics, alarms, dashboards.
- **How we use it:** Structured JSON logs (PII redacted) from every Lambda; alarms on errors, DLQ depth and spend.
- **Cost (not verified):** free tier covers small log volumes and a few alarms/metrics.

### AWS Budgets — decided (DEC-002, 019)
- **What:** Spend alerts.
- **How we use it:** ₹100 alert, created by Malik. A second, higher alert that includes Bedrock is pending (DEC-023).

### Amazon Bedrock (Anthropic Claude) — decided (DEC-006)
- **What:** Managed access to foundation models, including Claude, through AWS.
- **How we use it:** Fallback generator when Sarvam fails validation twice or errors; LLM-as-judge for faithfulness
  (on demand, cached). Uses the **India geographic cross-Region inference profile** (`in.` prefix), which per plan.md
  routes only within ap-south-1 ↔ ap-south-2.
- **Model IDs and prices:** `TODO(verify)` in the Bedrock console and AWS docs. Pick the cheapest model that passes
  the golden-set gates.
- **Open:** whether AWS credits cover Anthropic models (possible Marketplace billing).
- **Note:** Bedrock **Rerank** isn't offered in ap-south-1 (plan §Key Findings), so we self-host the reranker.

### AWS X-Ray / OpenTelemetry — planned
- **What:** Distributed tracing.
- **How we use it:** One trace per question across ingress → SQS → answer, with per-step timings feeding p95.

---

## 2. GitHub

### GitHub repository — decided (DEC-017, DEC-036)
- Public repo https://github.com/ajinendra05/Madhya-Kanoon-Saathi; remote `origin` over SSH; branch `main`.
- GitHub CLI `gh` 2.103.3 is installed at `C:\Program Files\GitHub CLI\gh.exe` but isn't on the Claude Bash PATH,
  so call it by full path. `gh` commands always ask for approval (DEC-034).

### GitHub Actions — decided (DEC-024)
- **How we use it:**
  - **CI on every PR:** lint, unit tests, deterministic eval scorers (free).
  - **Image build:** builds the answer-Lambda image (models + index), tags it with the corpus manifest hash, pushes to ECR, deploys.
  - **On demand:** judged eval runs (DEC-023).
- **Cost (not verified):** free for public repos; a monthly minutes quota for private repos.

### GitHub OIDC → AWS — planned (plan §7)
- **What:** Lets a workflow assume an AWS IAM role with short-lived credentials.
- **Why:** No AWS keys stored in GitHub secrets.

### GitHub Pages — decided (DEC-012)
- **How we use it:** Hosts the static cost dashboard built from the nightly summary JSON; shareable with interviewers.

### GitHub Issues — decided (DEC-013)
- **How we use it:** Law-watch opens an issue per detected source change. Malik approves before rebuild.

---

## 3. Models

### Sarvam-105B (`sarvam-105b`) — decided (DEC-006)
- **What:** Indic-native LLM from Sarvam AI, billed in INR.
- **How we use it:** Default generator; outputs strict JSON claims with citations; also the cheap query-rewrite call.
- **Price (from plan.md, not re-verified):** ₹15 in / ₹5 cached / ₹60 out per 1M tokens, excluding GST; 60 req/min on
  pay-as-you-go. Plan notes the price changed several times in 2026, so re-check docs.sarvam.ai monthly.

### Claude via Bedrock — decided (DEC-006)
- See Amazon Bedrock above. Strong instruction-following; costs several times more than Sarvam per query (plan §8 estimate).

### BGE-M3 — decided (DEC-004)
- **What:** Open multilingual embedding model (BAAI). Produces dense vectors (and optional sparse weights). Long input.
- **How we use it:** Embeds corpus chunks offline and the question at query time. Same **int8 ONNX** file on both
  sides (DEC-022); fp32 artifact kept as fallback (DEC-021).
- **Size (not verified):** ~568M parameters (~2.2 GB fp32, ~0.6 GB int8).
- **Licence:** TODO(verify) on the model card.

### multilingual-e5-large — decided as bake-off challenger (DEC-004)
- **What:** Open multilingual embedding model (Microsoft).
- **How we use it:** Offline comparison only; the winner by recall@10 per language is kept.

### bge-reranker-v2-m3 — decided (DEC-005)
- **What:** Open multilingual cross-encoder reranker (BAAI).
- **How we use it:** Scores (question, chunk) pairs for the RRF top-40 (fallback: top-20) → top-6. int8 ONNX by default.
- **Size (not verified):** ~568M parameters.

### Bodhan IndicOCR — decided (DEC-001)
- **What:** Open-source OCR from Bodhan AI and AI4Bharat (IIT Madras). Per Malik's note: a 33M layout model + a 0.8B
  recognition model; English + 22 scheduled Indian languages; text in reading order; tables as HTML/Markdown.
- **How we use it:** Scanned gazettes and Hindi PDFs only. 20-page test on laptop CPU, bulk on Colab GPU (DEC-015).
- **Verify:** Hugging Face model ID, licence, pinned revision hash. Reported Hindi scores are self-reported.

### Tesseract (`hin` language pack) — decided (DEC-014)
- **What:** Classic open-source OCR engine. Free baseline in the bake-off.

### Sarvam Document Digitization — decided for bake-off only (DEC-014)
- **What:** Sarvam's paid OCR (~₹0.50/page per plan, not re-verified). Used on the 20 test pages only (~₹10).

---

## 4. Libraries

### FAISS — decided (DEC-003, 025)
- **What:** Meta's library for vector similarity search.
- **How we use it:** `IndexFlatIP` over L2-normalised vectors (= cosine), exact search; index file built offline and
  shipped in the image.

### bm25s — decided (DEC-003)
- **What:** Fast pure-Python BM25 implementation.
- **How we use it:** Keyword index with our custom Hindi-aware tokeniser (DEC-026); built offline, loaded in memory.

### ONNX Runtime — decided (DEC-021)
- **What:** Fast inference engine for ONNX models on CPU.
- **How we use it:** Runs BGE-M3 and the reranker inside Lambda without PyTorch (smaller image, faster cold start).
- **Related (proposed):** Hugging Face `transformers` / `optimum` to export and quantise models to ONNX int8.

### Ragas — planned (plan §6)
- **What:** RAG evaluation library (faithfulness, context precision/recall).
- **How we use it:** Batch metrics; judged parts run on demand (DEC-023).

### DeepEval — planned (plan §6)
- **What:** pytest-style assertions for LLM outputs.
- **How we use it:** CI-friendly eval tests. Our own deterministic scorers matter most and need no LLM.

### pypdf — PDF text extraction (DEC-041)
- **What:** a pure-Python PDF reader (`pypdf==6.21.4`, BSD-3-Clause per its package metadata). `ingest` group only.
- **How we use it:** the downloader counts extractable characters per page to set `text_layer`
  (born_digital / scanned / mixed; a page needs ≥ 30 non-space characters). W1.1 uses it for text + page numbers.
- **Why this one:** no system install (works on the Windows laptop and Colab), no required dependencies.
- **Limit:** Hindi PDFs with legacy (non-Unicode) fonts can extract as garbage while still counting as text.
  W1.1 must check extracted Devanagari, not just character counts.

### pypdfium2 + Pillow — page rendering (DEC-053)
- **What:** `pypdfium2==5.15.2` (Python binding of Google's PDFium; BSD-3-Clause / Apache-2.0 per package metadata)
  and `pillow==13.0.0` (MIT-CMU). `ingest` group only; wheels for Windows and Colab, no system install.
- **How we use it:** render scanned pages to PNG for OCR (Bodhan, Tesseract, Sarvam) and for visual checks
  (e.g. the RTI Rules G.S.R. number, 2026-11-10).
- **Why this one:** PyMuPDF is AGPL (would bind our public repo); Poppler needs a system binary on Windows.

### urllib (stdlib) — corpus downloader
- **How we use it:** `ingestion/fetch.py` downloads from `data/corpus_sources.json` with retries, a generic
  project User-Agent, a 3 s delay between requests, atomic writes and sha256-based skip. No dependency needed.

---

## 5. Dev tooling

### Terraform — planned (plan §7)
- **What:** Infrastructure as code.
- **How we use it:** Defines Lambdas, SQS, DynamoDB, EventBridge, S3, ECR, IAM, SSM parameter *names* (never values).
  Every `plan`/`apply` that changes resources needs Malik's approval.

### Docker — decided (DEC-024)
- Builds Lambda container images **in GitHub Actions**, so it isn't required on the Windows laptop.

### pre-commit + gitleaks — proposed (kickoff step 3)
- pre-commit runs formatters/linters before each commit; gitleaks blocks commits containing secrets.

### Python toolchain — proposed (kickoff step 2)
- Python version, package manager + lockfile, linter/formatter, test runner: to be proposed for approval.

### Claude Code — in use
- Implementation partner. Project context in `CLAUDE.md`; permissions and hooks in `.claude/settings.json` +
  `.claude/hooks/` (DEC-034/035); area rules in `.claude/rules/`; skills `/start-session`, `/end-session`, `/decision`
  in `.claude/skills/`.

---

## 6. Other services

### Telegram Bot API — decided (DEC-007)
- **What:** HTTP API for Telegram bots.
- **How we use it:** `setWebhook` with a `secret_token` → our Function URL; `sendMessage` for replies. Free.
- **Verify:** bot username availability; webhook retry/timeout behaviour.

### Google Colab — decided (DEC-015)
- Free GPU notebooks for bulk OCR. Sessions time out, so the OCR script must be resumable.

### Google Sheets — planned (plan §1)
- Intake log for validation questions (names/phones stripped) before conversion into golden-set JSONL.

---

## 7. Data sources (primary, per plan §2)

| Source | Used for |
| --- | --- |
| India Code | Central Acts (EN + HI), MP Accommodation Control Act 1961 |
| egazette.gov.in | RTI Rules 2012, Central labour Rules 2026, notifications |
| labour.gov.in | Labour Codes and Central Rules |
| MP Labour DMS (labour.mponline.gov.in) | MP draft rules under the four codes |
| mpvidhansabha.nic.in (MP Legislative Assembly) | Official copies of Acts/Ordinances by year (bill_YYYY.htm); MPLRC amendment Acts 2022/2023 came from here. Pages embed zero-width joiners in Hindi words |
| labour.gov.in | Gazette of India copies of central labour notifications (e.g. S.O. 2451(E)) |
| web.archive.org (Internet Archive) | Retrieval route for official files whose site is down (revenue.mp.gov.in): the CDX index lists archived PDFs, `id_` URLs return the original bytes; sha256 recorded. Such copies count as authoritative government copies if the original URL, snapshot timestamp and sha256 are recorded and the original domain is official (DEC-049); aggregator snapshots don't qualify |
| indiankanoon.org | Reference only, never cited: used to locate the Demarcation Rules 2018 reproduction (itself marked unverified) |
| govtpress.mp.gov.in (MP Government Press) | Official MP Rajpatra listings; on 2026-11-07 the 2026 PDFs all returned 404 and the TLS chain was untrusted from Claude's tools (DEC-043) |
| mpedistrict.gov.in/MPL | Lok Seva Act, Rules and amendments (`getphoto.aspx` direct links), notified services list |
| rcms.mp.gov.in | Revenue Case Management System; hosts a 2013 Lok Seva time-limit gazette (historical source, DEC-045) |
| bor.mp.gov.in | Board of Revenue; lists the MPLRC (as amended 2018) but its links are dead (2026-11-07) |
| MP Labour Commissioner, Indore | MP minimum-wage notifications. DMS listing `labour.mponline.gov.in/.../Display_Documents.aspx?Sid=8`; files open via `ImageShow.aspx?src=<base64 path>` → session-bound `ShowPDF.axd` (resolver `mp_labour_dms`). Files are phone scans: OCR needed |
| consumeraffairs.nic.in, e-jagriti.gov.in | Consumer Protection Act, rules, procedure |
| rti.gov.in | RTI Act and Rules |
| MoHUA | Model Tenancy Act 2021 (model law only) |
| NALSA / DoJ pages | Legal-aid eligibility and escalation contacts (DEC-018) |
| Vaquill open-india-law (CC BY 4.0) | Parsing bootstrap only; cite the official source, never the aggregator |

---

## 8. Considered and dropped

| Tool | Was for | Dropped because | Decision |
| --- | --- | --- | --- |
| Aurora PostgreSQL Serverless v2 + pgvector | Vectors, metadata, logs | Monthly floor; corpus fits in memory | DEC-002, 003 |
| ECS Fargate | Answer service + reranker | Always-on cost | DEC-002 |
| API Gateway | Webhook endpoint | Function URL is free | DEC-002 |
| AWS Secrets Manager | Secrets | Per-secret monthly fee | DEC-009 |
| Cohere Embed Multilingual v3 (Bedrock) | Embeddings | Possible deprecation + Provisioned-Throughput pricing (not verified) | DEC-004 |
| Cohere Rerank 3.5 / Bedrock Rerank | Reranking | Not in ap-south-1; data leaves India | DEC-005 |
| OpenSearch Serverless | Search | OCU floor cost | DEC-003 |
| VPC + NAT gateway | Network isolation | NAT cost; no database to protect | DEC-029 |
| Amazon Textract | OCR | Not a fit for Devanagari (plan §5) | DEC-001 |
| Sarvam OCR as main engine | OCR | Bodhan is free with similar reported Hindi scores | DEC-001 |
| Marathi / Maharashtra corpus | +1 language/state | Out of scope | DEC-016 |
| WhatsApp Cloud API, Sarvam voice (Saaras/Bulbul) | Channels/voice | After November demo | later |
