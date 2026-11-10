# Decisions — Madhya Kanoon Saathi

The decision log for the project. **Where this file and `docs/plan.md` disagree, this file wins.**
New decisions are added at the bottom with the next number. Old entries are never edited silently.
If a decision changes, add a new entry that says `Supersedes DEC-xxx` and set the old one's status to `superseded`.

**Format for every entry**

```
## DEC-NNN — <title>
- Date: YYYY-MM-DD | Status: accepted | deferred | superseded by DEC-xxx | Approved by: Malik
- Context: why a decision was needed (2–3 lines)
- Options: A / B / C with one-line trade-offs
- Decision: what we chose
- Why: plain-English reason
- Effects: efficiency · accuracy · application · cost
- Follow-ups: verification items, related decisions
```

"(not verified)" means the fact came from memory or a third-party page. It must be checked against
official docs before code depends on it. Each one is also listed in OPEN_QUESTIONS.md.

---

## DEC-001 — OCR engine: Bodhan IndicOCR
- Date: 2026-11-05 | Status: accepted | Approved by: Malik
- Context: The plan used Sarvam Document Digitization (₹0.50/page) for scanned gazettes and Hindi PDFs.
- Options: A) Sarvam (paid) · B) Bodhan IndicOCR (free, open source, built by Bodhan AI + AI4Bharat, IIT Madras) · C) Tesseract `hin` (free baseline).
- Decision: **Bodhan IndicOCR** is the OCR engine. It is used only where no born-digital text layer exists.
- Why: It's free and built for the 22 scheduled Indian languages. Its reported printed-Hindi scores (96.0 / 91.0) are close to Sarvam's (95.7 / 93.5). It returns text in reading order, with tables as HTML/Markdown, which suits wage-notification tables.
- Effects: cost ₹0 per page (saves ~₹1,500 vs the plan) · accuracy must be confirmed on our own pages (DEC-014) · needs GPU or Colab for bulk runs (DEC-015).
- Follow-ups: the vendor scores are self-reported. Verify the HF model ID and pin its revision hash.

## DEC-002 — Hosting: always-free serverless AWS (ap-south-1)
- Date: 2026-11-05 | Status: accepted | Approved by: Malik
- Context: The plan's Aurora + Fargate + API Gateway design has a monthly floor (~$44/mo for Aurora alone).
- Options: A) plan as written · B) only AWS always-free services.
- Decision: **B.** Lambda (container image) for compute, Lambda Function URL as the Telegram webhook, SQS between functions, DynamoDB for logs and quotas, EventBridge for schedules. S3 and ECR are used at a few rupees per month. Use the AWS **Paid plan** (it doesn't auto-close) with a **₹100 budget alert**.
- Why: Our traffic and corpus are small. Always-free limits (Lambda 1M requests + 400K GB-s, DynamoDB 25 GB, SQS 1M requests; not verified) cover roughly 20–30K questions a month.
- Effects: cost ~₹0–50/month · cold starts of 10–20 s (DEC-020) · fewer moving parts · a good interview story: "measured the corpus, dropped the database, hosting went from ~$44/mo to ₹0".
- Follow-ups: verify the Free vs Paid plan rules and the always-free limits on official AWS pages.

## DEC-003 — No vector database: FAISS + BM25 index files inside the app
- Date: 2026-11-05 | Status: accepted | Approved by: Malik
- Context: The corpus is ~10–30K chunks, about 100–150 MB of vectors. That fits in memory.
- Options: A) Aurora + pgvector · B) OpenSearch Serverless · C) index files packed into the Lambda image.
- Decision: **C.** A FAISS index for dense vectors and a `bm25s` index for keywords. Both are built offline and shipped in the container image (DEC-024). A law change triggers a rebuild and redeploy after approval (DEC-013).
- Why: A database server is the main fixed cost. At this size, in-memory search is faster and free.
- Effects: cost ₹0 · query search time a few ms · index updates need a redeploy · must re-evaluate past a few million chunks.

## DEC-004 — Embedding model: BGE-M3 default + offline bake-off
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q3)
- Context: The plan recommended Cohere Embed Multilingual v3 on Bedrock. Its possible deprecation (15 Feb 2027) and possible Provisioned-Throughput-only pricing (~$7.12/h) make it unsuitable (both not verified).
- Options: A) BGE-M3 only · B) BGE-M3 default + bake-off vs multilingual-e5-large · C) Cohere Embed v3.
- Decision: **B.** BGE-M3 is the default. Compare it offline with multilingual-e5-large on the golden set and **keep the winner by recall@10 per language** (hi, en).
- Why: Free, runs in our own Lambda, multilingual. The bake-off gives the eval report a "why this model" table backed by numbers.
- Effects: ₹0 per query · ~½ day extra in W1 · the model adds weight to the image (DEC-021).

## DEC-005 — Reranker: self-hosted bge-reranker-v2-m3
- Date: 2026-11-05 | Status: accepted | Approved by: Malik
- Context: Bedrock Rerank is not offered in ap-south-1 (per plan §5).
- Decision: Self-host **bge-reranker-v2-m3** inside the answer Lambda: RRF top-40 → rerank → top-6. Precision strategy in DEC-021.
- Why: Keeps data in India and costs ₹0 per query.
- Effects: the rerank step dominates CPU time per question; must measure p95.

## DEC-006 — LLMs: Sarvam-105B default; Claude on Bedrock as fallback and judge
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (incl. Q12)
- Context: The plan's A/B: Sarvam-105B (cheapest, Indic-native) vs Claude via Bedrock India geo profile.
- Decision: **Sarvam-105B** is the default generator. **Claude via Bedrock's India (`in.`) profile** is the fallback when the citation validator fails twice or Sarvam returns 402/errors, and is also the LLM-as-judge. **Claude model IDs and prices stay `TODO(verify)`** until checked in the Bedrock console and AWS docs. Then pick the **cheapest model that passes the golden-set gates**.
- Why: The plan's model names and India-profile prices were derived, not read from AWS.
- Effects: per-query model cost ~₹0.10 on the Sarvam path (plan §8, not re-verified) · the judge model choice affects κ calibration (redo if it changes).
- Follow-ups: whether AWS credits cover Bedrock Anthropic models (Marketplace billing?).

## DEC-007 — Channel: Telegram first
- Date: 2026-11-05 | Status: accepted | Approved by: Malik
- Decision: Telegram Bot API is the first and only channel for the November demo. WhatsApp is later.
- Why: Free, no business verification, ships in a day.

## DEC-008 — plan.md stays; banner + this file overrides
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q1, Q2)
- Context: The two changes (DEC-001, DEC-002) were made after `docs/plan.md` was written.
- Options: A) rewrite plan.md · B) banner + DECISIONS.md overrides · C) PLAN-v2.md.
- Decision: **B.** Add a short banner at the top of `docs/plan.md` pointing here, and leave the body unchanged. The file keeps its name **`docs/plan.md`** (lowercase). `docs/plan.doc` was added by mistake and is not part of the project.
- Why: Fastest option, and it keeps the original reasoning as history.
- Effects: every session reads plan.md + DECISIONS.md together (CLAUDE.md says so).
- Follow-ups: ask Malik before deleting `docs/plan.doc`. Until then it's kept out of git.

## DEC-009 — Secrets: SSM Parameter Store (standard, SecureString)
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q4)
- Options: A) SSM standard SecureString · B) Secrets Manager (~$0.40/secret/month, not verified).
- Decision: **A.** Values are encrypted with KMS. Each Lambda reads them once at cold start and keeps them in memory. Supersedes the plan's "Secrets Manager".
- Why: Same protection for our needs at ₹0. We don't need automatic rotation.
- Effects: ₹0 · key rotation is manual.

## DEC-010 — Request flow: ingress Lambda → SQS → answer Lambda
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q5)
- Context: Telegram resends a webhook if it doesn't get a quick 2xx. A cold start plus generation is too slow to answer inline.
- Options: A) one Lambda answers inline · B) two Lambdas + queue · C) reply 200 then keep working (unreliable).
- Decision: **B.** The ingress Lambda (Function URL) checks the Telegram secret-token header. It drops duplicates with a conditional DynamoDB write on `update_id`, sends the message to SQS, and returns 200 at once. The answer Lambda consumes SQS, runs the pipeline, and replies via `sendMessage`. Failed messages go to a dead-letter queue.
- Why: No duplicate answers or double LLM bills. Retries are built in. Lambda concurrency can be capped to respect Sarvam's 60 req/min.
- Effects: one extra hop (tens of ms, not measured) · ₹0 within the SQS free tier.

## DEC-011 — Raw corpus storage: local for dev, S3 for production, manifest in git
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q6)
- Decision: In **development**, raw PDFs live on Malik's laptop (git-ignored folder). In **production**, PDFs go to an **S3 bucket with versioning**. In both cases git holds `corpus_manifest.json`: per file, source URL, fetch date, sha256, status (in_force / draft / model_law / repealed / sub_judice_flag) and the S3 path.
- Why: Fast local iteration, plus a provable version history in production.
- Effects: S3 under 1 GB ≈ a few ₹/month (not verified) · the manifest checksums let us detect a local copy that differs from S3.

## DEC-012 — Cost dashboard: nightly summary + static page
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q7)
- Decision: Once a night, a small Lambda (or GitHub Action) reads the previous day's `cost_log` rows from DynamoDB, aggregates them, and writes a summary JSON. A static HTML page on GitHub Pages draws the charts.
- Why: DynamoDB can't do GROUP BY. A daily static page is free, fast and safe to share publicly (no keys exposed).
- Effects: numbers up to 24 h old · ₹0.
- Follow-ups: depends on the DynamoDB schema (pending, see "Pending decisions").

## DEC-013 — Law-watch: detect in AWS, human approves the rebuild
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q8)
- Decision: A weekly EventBridge rule triggers a Lambda in ap-south-1. It re-fetches watched URLs (including the contact source pages, DEC-018) and compares sha256 with the manifest. On a change it **opens a GitHub issue**. Malik reviews it (draft vs final, parse check). The index rebuild and redeploy run only after approval. Affected golden-set rows re-run first.
- Why: Legal text should never change in production unchecked. Fetching from Mumbai avoids possible foreign-IP blocking by Indian government sites (not verified).
- Effects: ~10–30 min of Malik's time per real change · ₹0 · needs a fine-grained GitHub token in SSM.

## DEC-014 — OCR bake-off: Bodhan vs Tesseract vs Sarvam on 20 pages
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q9)
- Decision: Compare **Bodhan IndicOCR, Tesseract `hin` and Sarvam** on the same 20 hand-verified pages (MP gazette scans, wage tables, Hindi Act text). The metric is character error rate (CER). Scheduled in W0 per the kickoff.
- Why: OCR errors become wrong exact-quote citations. This is the cheapest accuracy check in the project.
- Effects: Sarvam cost ≈ 20 × ₹0.50 ≈ ₹10 (price not re-verified) · several hours of Malik's time to correct the ground truth.

## DEC-015 — Where OCR runs: CPU for the test, Colab for the bulk
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q10)
- Decision: Run the **20-page test on the laptop CPU**, and the **full corpus on Google Colab** (free GPU). If CPU proves impractical, use Colab for everything. Check the model licence and pin the model revision first.
- Effects: ₹0 · Colab sessions time out, so the batch script must resume from where it stopped.

## DEC-016 — Scope: Madhya Pradesh + central laws only; Hindi + English; no Marathi
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q11)
- Decision: **No Marathi and no Maharashtra.** Scope is MP + central laws, in Hindi (incl. Hinglish) and English.
- Effects (supersedes parts of plan.md): golden-set language mix drops the "≥10% Marathi" floor · roadmap items "Marathi slice" (W4–5) and "Maharashtra corpus" (W6–9) are removed · the language-detection and eval slices are hi / hinglish / en.

## DEC-017 — Project name: Madhya Kanoon Saathi
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q13)
- Decision: Product **Madhya Kanoon Saathi**; GitHub repo `Madhya-Kanoon-Saathi`; Python package `madhya_kanoon_saathi`; AWS resource prefix `mks-` (short, because some AWS names have length limits). Replaces "Niyam Saathi" / "Kanoon Saathi" in older docs.
- Follow-ups: check the Telegram bot username is available (must end in "bot").

## DEC-018 — Escalation contacts come from a sourced file
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q14)
- Decision: `contacts.yaml` holds, per contact: value, saved official source page (file + page), and `verified_on`. A unit test checks that every value appears in its saved source. The law-watch (DEC-013) also watches those pages.
- Why: A wrong helpline number is real harm. This is the same citation discipline as for statutes.

## DEC-019 — AWS account: Malik creates it
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (Q15)
- Decision: Malik creates the AWS account (Paid plan per DEC-002, root MFA, ₹100 budget alert). Claude never uses root or admin keys. CI deploys via GitHub OIDC.

## DEC-020 — Latency gate: warm p95 gated, cold starts reported
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R1)
- Decision: **v1:** the ops gate "p95 < 8 s (text)" applies to **warm** requests only. Cold-start latency is measured and reported separately. **Next version:** add a 5-minute EventBridge keep-warm ping (option C).
- Why: A gate that fails because of cold starts says nothing about answer quality.

## DEC-021 — Model precision: start int8, keep fp32 and top-20 as fallbacks
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R2; margin delegated to Claude)
- Decision: Start with **int8 ONNX** BGE-M3 + reranker, reranking the **top 40** (option B). If warm p95 is too slow, rerank the **top 20** (C). If accuracy is too low, use **fp32** (A). All three stay as configurable options.
- **Acceptance margin (chosen by Claude):** int8 is accepted only if its **recall@10 is no more than 0.02 (2 points) below fp32**, both **overall and on each language slice (hi, en)**, on the same golden set.
- Why for the margin: 2 points is about 2–3 questions out of 120. That's small enough that users wouldn't notice, and large enough not to fail on noise. Checking per language stops a Hindi drop from hiding behind a good English score.
- Effects: int8 is ~4× smaller to load (faster cold start) and fits a 3–6 GB Lambda.

## DEC-022 — Embedding parity between index build and Lambda
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R3)
- Decision: Build **both** an int8 and an fp32 index artifact, so DEC-021's fallback is ready. **Start with int8** for both corpus and queries. A **parity test** embeds a fixed sentence in the build environment and inside the Lambda image, and fails if the vectors differ beyond a tiny tolerance. The corpus and query model must always be the same file (checksum-pinned).
- Why: Prevents silent "train/serve skew" in retrieval.

## DEC-023 — LLM-judge runs on demand only (v1)
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R4)
- Decision: **v1:** judged evals (faithfulness, κ calibration) run **only on demand**, with a judge-result cache keyed by (question, cited chunk IDs, answer, judge model, rubric version). Deterministic scorers (recall, MRR, citation precision, quote match) are free and run in CI. **Next version:** move to option B (free checks on every PR + cached 40-row judged smoke + weekly full run).
- Effects: ~₹150 per full 120-row judged run (my calculation from plan prices, not verified).
- Follow-ups: the monthly eval budget and whether to add a second, higher AWS alert are not yet set (see Pending).

## DEC-024 — Packaging: models + index in the image, built in GitHub Actions
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R5)
- Decision: The Lambda container image holds code, models and index (A). Images are built and pushed to ECR by **GitHub Actions** (C). The image tag carries the corpus manifest hash. ECR lifecycle keeps the last 3 images.
- Why: One image = one exact snapshot of law + code. Rollback restores both. No Docker needed on the Windows laptop.
- Effects: rebuild ~10–20 min per law change (not measured) · ECR ~₹15–45/month (not verified).

## DEC-025 — FAISS exact search (IndexFlatIP)
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R6)
- Decision: Exact inner-product search on normalised vectors (= cosine). Metadata filters (state, status, valid-on date) are applied exactly. No HNSW/IVF.
- Why: Approximate search trades accuracy for speed. At ~30K chunks we have no speed problem. Revisit only past a few million chunks.

## DEC-026 — Custom Hindi-aware BM25 tokeniser
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R7)
- Decision: Our own tokeniser does the following:
  - Unicode NFC normalisation and nukta folding
  - Devanagari digits → ASCII
  - section references kept as one token (`s8_1_j`) plus their parts
  - Latin text lowercased
  - a small Hindi/English stop-word list
  - धारा / section / s. / dhara mapped to one token

  Each rule has unit tests built from real examples. The same code runs at index time and query time.

## DEC-027 — Licences: educational/research project
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R8)
- Decision: The project is **educational/research and non-commercial**. A detailed licence review is not required now. Minimum kept anyway: attribution for CC BY data (e.g., Vaquill) and citing the official source for every statute.
- Effects: if the plan's B2B/paid tiers (plan §8–9) are ever pursued, this decision must be reopened first.

## DEC-028 — Schedule unchanged
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R9: "don't panic")
- Decision: Keep the plan's week dates. If W0 slips by a day or two, that's acceptable. The plan's cut-line stays the backup.

## DEC-029 — No VPC; security design without private subnets
- Date: 2026-11-05 | Status: accepted | Approved by: Malik (R11)
- Decision: No VPC. A VPC would require a NAT gateway (~₹3,000/month, not verified) for Lambda to reach Sarvam and Telegram. Security comes from:
  - least-privilege IAM role per function
  - encryption at rest for DynamoDB, S3 and SSM (AWS-managed keys)
  - Telegram secret-token header check on every webhook
  - PII redaction before any log or trace
  - 90-day TTL on raw chats (DPDP)

  Replaces "private subnets" in plan §3's DPDP table.

## DEC-030 — Repo structure and Python tooling
- Date: 2026-11-06 | Status: accepted | Approved by: Malik (kickoff step 2)
- Decision:
  - **Layout:** `src/madhya_kanoon_saathi/` with sub-packages `common`, `ingestion`, `retrieval`, `generation`, `eval`, `bot`, `handlers` (thin Lambda entry points), plus top-level `scripts/`, `notebooks/`, `data/`, `infra/terraform/`, `docker/`, `tests/{unit,integration,golden}`.
  - **Data in git:** `data/corpus_manifest.json`, `data/contacts.yaml` and `data/golden/` are committed. `data/{raw,parsed,index,ocr}` are git-ignored.
  - **Tooling:** Python **3.12**, **uv** + `uv.lock`, dependency groups `dev` / `ingest` / `eval` / `serve` (the Lambda image installs only `serve`), **ruff** (lint + format), **mypy** on `src/`, **pytest** + pytest-cov with markers `slow`, `paid` (skipped by default) and `golden`, **pre-commit** (as a uv tool) with ruff + gitleaks, and GitHub Actions running the same commands.
  - **Dev dependencies approved:** ruff, mypy, pytest, pytest-cov, and pre-commit as a uv tool. Runtime libraries are added one task at a time, with approval.
- Why:
  - The src layout tests the installed package, so packaging bugs show up early.
  - Thin handlers keep the logic testable without AWS.
  - Per-area dependency groups keep the Lambda image small, which means faster cold starts.
  - uv gives one pinned lockfile.
- Follow-ups: verify the Lambda Python 3.12 base image and faiss-cpu / onnxruntime wheels for 3.12; verify the gitleaks install route on Windows. Terraform is not installed yet; ask before installing.

## DEC-031 — Accepted Claude-made choices from 2026-11-05 review
- Date: 2026-11-06 | Status: accepted | Approved by: Malik
- Decision: Confirms the interpretations Claude recorded on 2026-11-05:
  - DEC-016: Marathi and Maharashtra fully removed.
  - DEC-017: package name and the `mks-` prefix.
  - DEC-021: the 2-point recall@10 margin, applied overall and per language.
  - DEC-028: schedule unchanged.
  - DEC-008: `docs/plan.doc` deleted on 2026-11-06.

## DEC-032 — Corpus expansion roadmap (phased)
- Date: 2026-11-06 | Status: accepted | Approved by: Malik
- Context: The plan's corpus covers tenancy, labour, consumer, RTI, legal aid and a few schemes. Malik shared a domain-expansion research report on 6 Nov 2026 listing new areas to add.
- Decision: Adopt the report's phased corpus roadmap, kept in **`docs/CORPUS.md`**:
  - **Nov 2026 MVP:** the plan's 14 items, plus the MP Lok Seva Guarantee Act 2010 and certificate *procedure* (income, domicile, caste), plus grievance routes (CM Helpline, CPGRAMS). The existing domains also gain the MP labour Sanhita 2026 and the Registration (MP Amendment) Act 2025.
  - **Dec 2026:** land records + farmer schemes.
  - **Q1 2027:** students, cyber/FIR basics, banking/insurance, women's safety, senior citizens.
  - **Q2 2027:** panchayat/PESA/VB-G RAM G, SC/ST + forest rights, disability.
  - **H2 2027+:** family/UCC, RERA, motor accidents, electricity, ration, Ayushman, birth/death.
- Why: The Lok Seva module is a single born-digital Act with low-risk procedural content and a strong MP focus. Higher-risk areas wait until the safety guardrails have been validated.
- Effects: MVP adds ~1–2 days of ingestion · the golden set needs public-services rows · the MGNREGA → VB-G RAM G change replaces the earlier MGNREGA suggestion.
- Follow-ups: every fact in the report is unverified (some come from secondary sources) and must be checked against official text before ingestion (OPEN_QUESTIONS group G). The report's design changes (crisis router, new status flags, golden set → 200, sensitive-data rule, jurisdiction guard, dispute detector) are **not** part of this decision; see DEC-033 (pending). The report's mention of a "planned Marathi expansion" doesn't apply (DEC-016).

## DEC-033 — Safety and schema design changes from the expansion report
- Date: 2026-11-06 | Status: accepted ("all as recommended") | Approved by: Malik
- Decision:
  1. **Crisis router (Nov MVP):** every message is checked for danger signals *before* retrieval, in Hindi, Hinglish and English. If one is found, the reply shows emergency/helpline numbers first. Numbers come only from `contacts.yaml` with sources (DEC-018). Gate: **crisis-trigger recall = 100%** on test rows.
  2. **Status flags (now, before W0.4):** the full set is `in_force | draft | model_law | repealed | sub_judice_flag | passed_awaiting_assent | proposal`. Instruments and schemes also get an optional **`expires_on`**. Answers that rely on an expired instrument abstain automatically.
  3. **Golden set:** v1.0 (Nov) stays at **120 rows**, with ~10 public-services rows and ~6 status-trap rows taken from other slices. It grows toward 200 as each new phase is added (v1.1+).
  4. **Sensitive data (now):** never ask for caste, disability, health or religion. If a user volunteers it, use it only within that session, never store it, and redact it from all logs, traces and DynamoDB writes.
  5. **Jurisdiction guard:** formal rule that land/family retrieval uses only MP-tagged (or central) documents. Enforced together with the land module in Dec.
  6. **Dispute detector (Dec, with land):** for land, SC/ST, family and criminal questions, answer the procedure and route "who is right" questions to DLSA.
- Why: Safety-critical behaviour (crisis, sensitive data) must exist before any user sees the bot. Schema fields are cheapest to add before the first manifest is written.
- Effects: ~2 extra days in W1–W2 (router + redaction) · golden-set composition shifts (DEC-016 language mix unchanged) · chunk/manifest metadata gains `expires_on` and the two new flags.

## DEC-034 — Claude Code permissions and hooks
- Date: 2026-11-06 | Status: accepted | Approved by: Malik (kickoff step 4)
- Decision: `.claude/settings.json` sets three tiers of permission rules:
  - **allow:** repo edits; uv test/lint/type/python runs; lockfile-only sync; pre-commit; git status/diff/log/add/commit; terraform fmt/validate.
  - **ask:** protected files; dependency changes; push/branch/gh; deletes; paid tests; terraform init/plan/apply; all aws.
  - **deny:** secrets files; `rm -rf`; force-push; `terraform destroy`; env printing.

  Three hooks, each stdlib-only Python in `.claude/hooks/`:
  - **Stop:** fast ruff + pytest after each turn, with failures reported back; `stop_hook_active` skip prevents loops.
  - **PreToolUse (Edit|Write|NotebookEdit):** protected files → `ask`.
  - **SessionStart (`compact`):** re-adds a PROGRESS/DECISIONS summary after compaction.
- Why: Routine work runs without prompts, while risky or irreversible actions always need Malik. Syntax was checked against code.claude.com/docs/en/permissions and /hooks on 2026-11-06.
- Known limits (from the docs): Bash rules match command text, not a security boundary. Read-deny doesn't stop a script that opens files itself. Paid calls are guarded by the `paid` marker + an ask rule + convention. Secrets in commits are caught by gitleaks. Sandbox mode is a possible later hardening.

## DEC-035 — Narrow the protected-file list
- Date: 2026-11-06 | Status: accepted | Approved by: Malik | Supersedes the protected-file list in DEC-034
- Decision: Only **`docs/DECISIONS.md`** and **`docs/CORPUS.md`** need Malik's approval to edit (ask rule + PreToolUse hook). `docs/plan.md`, `CLAUDE.md`, `.claude/settings.json`, `.claude/hooks/**` and the golden-set files are edited without prompts.
- Why: Fewer interruptions for routine changes. The decision log and the corpus scope are the two files whose changes alter what the project is.
- Effects: The plan.md body staying unchanged (DEC-008) and frozen golden versions never being edited (plan §1) remain **conventions** in CLAUDE.md and `.claude/rules/eval.md`, not hook-enforced. Claude Code may still prompt on some `.claude/` edits by its own built-in rules (not verified).

## DEC-036 — Public GitHub repo; AGENTS.md stays personal
- Date: 2026-11-06 | Status: accepted | Approved by: Malik
- Decision: The GitHub repo `Madhya-Kanoon-Saathi` is **public**. `AGENTS.md` (Malik's Codex copy of CLAUDE.md) stays **untracked** as a personal file.
- Why: A public repo lets interviewers browse it, and GitHub Pages and Actions are free for public repos (not verified). Gitleaks passed and `.env` is ignored.
- Effects: Everything committed is world-readable, so the no-secrets/no-PII rules and gitleaks matter even more. Raw user questions never go in git; golden rows are stored redacted only.

## DEC-037 — Phase 0 corpus review
- Date: 2026-11-06 | Status: accepted ("all as recommended") | Approved by: Malik
- Context: Item-by-item check of the November corpus before W0.4 starts.
- Decision (details in `docs/CORPUS.md` Phase 0 table):
  - **Index:** RTI Act; RTI Rules 2012; DPDP s.44(3) + needed definitions only; CPA 2019 + Jurisdiction Rules + E-Commerce Rules; four Labour Codes in full; Central Rules 2026; MP draft labour rules; MP Accommodation Control Act 1961; MTA 2021 (model_law); TPA ss.105–111 + Registration Act s.17; LSA Act s.12; e-Shram + PM-SVANidhi.
  - **Gated on verification:**
    - MP Shram Shakti Sanhita (G4)
    - current MP minimum-wage notification (L4)
    - Lok Seva Act + certificate procedure (G6)
    - **added:** MP RTI fee rules (G12), MP SLSA free-legal-aid income limit (G13)
  - **Archive only (not indexed):** MP Parisar Kirayedari Adhiniyam 2010, until L1 is resolved.
  - **Official guides, not law:** e-Jagriti filing steps; CM Helpline / CPGRAMS (plus `contacts.yaml`).
  - **Decide after G14:** MP Shops and Establishments Act.
  - **Moved out:**
    - Registration (MP Amendment) 2025 → Dec land phase
    - one MP scheme → Dec
    - Model Standing Orders → later
    - commission procedure regulations → later
  - **Excluded:** DPDP Rules 2025.
  - **Golden set:** schemes slice 10 → ~5; ~5 rows move to public-services and state-RTI; total stays 120.
- Why:
  - The 31 Mar 2026 MP wage notification expired on 30 Sep 2026 (per plan.md), so the current one is mandatory before wage answers.
  - Most MP RTI applications go to state authorities, so central rules alone would give state-incorrect fee answers.
  - Indexing a law of unknown status risks citing non-law.
- Effects: ~18 indexed or gated instruments · W0.4 starts with the wage notification and the verification items · fewer time-bound scheme documents to maintain.

## DEC-038 — Thin land-procedure slice in the November MVP
- Date: 2026-11-06 | Status: accepted (option C) | Approved by: Malik | Supersedes part of DEC-032 (land wholly in Dec) and DEC-033.6 (dispute detector in Dec)
- Context: Malik asked what adding land + farmers to the November phase would cost. Money impact is ~₹0–50/month; the real costs are 2.5–3.5 weeks of work and accuracy risk.
- Options:
  - A) keep land + farmers in Dec (demo 30 Nov)
  - B) add all of land + farmers now (demo ~mid–late Dec, high risk)
  - C) thin land-procedure slice now (demo ~3–5 Dec, medium risk)
  - D) farmer schemes only now (demo ~2–3 Dec, high upkeep)
- Decision: **C.**
  - Add MPLRC **ss.109–110 (mutation), s.129 (demarcation)** + Mutation Rules 2018 + demarcation rules + a Bhulekh/Cyber Tehsil copy guide (CORPUS.md items 19–22).
  - **Procedure only.**
  - **Dispute detector moves to November** (W2) and the **jurisdiction guard** is enforced for land in November.
  - Farmer schemes and the rest of land stay in Dec.
- Golden set: ~8–10 land-procedure rows (of which ~3 should-abstain "who owns it" / dispute rows). Default plan keeps v1.0 at 120 by trimming tenancy 35→31, labour 30→28 and consumer 25→23. Final composition is confirmed when the set is built (W2.6).
- Why: Land is the top rural question in MP. Procedure questions (mutation, demarcation, record copies) are well defined and low-risk when merits questions are routed to DLSA. It's a strong demo and interview story for ~4–5 extra days.
- Effects:
  - **Demo date ~3–5 Dec** instead of 30 Nov.
  - +~3–4 days ingestion/verification, +~1 day dispute detector, +~1 day golden rows.
  - Money ≈ +₹0–50/month; a full judged eval run costs the same (total rows unchanged).
  - G8 (conflicting mutation time limits, demarcation-rules year, unverified 2022/2023 amendments) becomes MVP-blocking for this slice.

## DEC-039 — Fewer permission prompts (Malik's settings edit)
- Date: 2026-11-06 | Status: accepted | Approved by: Malik (edited `.claude/settings.json` directly) | Amends DEC-034
- Decision: These moved from `ask` to `allow`:
  - `uv run pytest -m paid`
  - `uv add / remove / lock`, `uv pip`, `pip`
  - `git push`, `git branch`, `git checkout -b`, `git switch -c`, `git rm / reset / rebase`
  - `gh *`
  - `rm *`

  Still `ask`: edits to DECISIONS.md and CORPUS.md, terraform init/plan/apply/import/state, all `aws`, PowerShell `Remove-Item` and `git push`. Still `deny`: secrets files, `rm -rf`, force-push, `terraform destroy`, env printing.
- Why: Fewer interruptions during routine work.
- Effects: The tool no longer prompts for these. **The CLAUDE.md decision protocol is unchanged**: Claude still asks Malik first before adding/removing dependencies, pushing, deleting files or making paid API calls beyond a tiny test. The guard is now Claude's protocol rather than a prompt.

## DEC-040 — `section_uid` scheme and corpus manifest schema
- Date: 2026-11-06 | Status: accepted ("all as recommended" + Malik's five additions, "finalise as above") | Approved by: Malik
- Context: W0.3. Every chunk, golden row, citation and law-watch alert refers to law units by one ID, and every downloaded file needs one manifest record. Changing either later means re-labelling everything.
- Options: uid A) plan style `RTI2005:s8:ss1:cl_j` · **B) jurisdiction prefix `IN.RTI2005:s8:ss1:cl_j`** · C) Akoma Ntoso eIds. Manifest **A) JSON + stdlib validator** · B) JSON + pydantic · C) YAML.
- Decision:
  1. **`section_uid` = `<JUR>.<CODE><YEAR>:<segment>:…`**, with JUR `IN` (central) or `MP`. Segments: `s` section, `ss` sub-section, `cl_` clause, `scl_` sub-clause, `prov` proviso, `expl` explanation, `r` rule, `reg` regulation, `para` paragraph, `sch` schedule, `form_` form; inserted units take an uppercase suffix (`s13A`). The uid names the *provision*, not a version of its text.
  2. **`chunk_id = <section_uid>@<lang>@<valid_from>`**. The citation validator checks `chunk_id`; eval scores on `section_uid`.
  3. **Hindi uids come from structural alignment with the English text**, never from mapping Devanagari clause letters to Latin ones.
  4. **Coverage rule:** a retrieved uid covers an expected uid if it is equal to it or an ancestor of it.
  5. **State amendments to a central Act** keep the central uid and are stored as an MP-only text version.
  6. **Manifest = `data/corpus_manifest.json`** (`instruments` + `documents`), validated by our own stdlib code. Full field list in `docs/specs/manifest.md`.
  7. Malik's additions (2026-11-06), as narrowed by Claude's review:
     - **Parent-child:** provision parents are *computed* from the uid (`parent()` / `ancestors()`); instruments carry `parent_instrument` + `made_under`.
     - **Amendment history:** per instrument `enacted_on`, `commenced_on` (+ per-provision override), `amendments` list, `supersedes`/`superseded_by`; per document `valid_from`/`valid_to`/`expires_on`. "Current" is computed, never stored. No full point-in-time consolidation.
     - **Authority level:** only `type` is stored; `authority_rank` and `binding` are derived from a fixed mapping. Rank is **not** a retrieval weight; it drives the law-beats-guide conflict flag and the "rights claims cite binding law" rule (answer wording decided in W2.1).
     - **Applicability:** `applies_to {level, states, districts, areas, note}` per document with optional per-provision override. State level enforced now; districts/areas stored only (LGD codes, not verified).
     - **Verification provenance:** a list of records `{what, by (claude|malik|advocate), on, method, evidence, result, note}` plus `last_checked_on` from law-watch. **Index gate:** `mode=index` requires `confirmed` records for both `status` and `commencement`; legal-interpretation checks need `malik` or `advocate`.
- Why: The jurisdiction in the ID makes state-vs-central visible everywhere and backs the jurisdiction guard. Computing parents, rank and "current" from one source means they cannot drift. The verification gate makes "unverified law never reaches users" a code rule, not a habit. Stdlib validation avoids a new dependency today.
- Effects: efficiency: no new dependency, uid parsing is O(length) · accuracy: unverified or expired documents can't be indexed or cited as current · application: every later module (chunker, tokeniser, eval, law-watch) uses these IDs · cost ₹0 · time: W0.3 ~1 day, W0.4 +~2–3 h to fill fields.
- Follow-ups: LGD district codes (OPEN_QUESTIONS); move manifest validation to pydantic if it is added in W2 for LLM JSON output (needs approval); fix the unverified Hindi example in `.claude/rules/retrieval.md`.

## DEC-041 — W0.4 approach and `pypdf` for text-layer detection
- Date: 2026-11-06 | Status: accepted ("ok, A") | Approved by: Malik
- Context: Each manifest document needs `text_layer` (born_digital / scanned / mixed), so the downloader must tell whether a PDF already contains text. W0.4 also needed a work order.
- Options: **A) add `pypdf` to the `ingest` group** · B) stdlib byte-scan for font markers (unreliable on scanned gazettes) · C) set by hand per file (slow, doesn't scale).
- Decision: **A.** `pypdf==6.21.4` (pinned in `uv.lock`) in the `ingest` group, which is now also a uv default group for local dev. The Lambda image still installs only `serve`. Licence **BSD-3-Clause** (read from the installed package metadata, `License-Expression`, 2026-11-06); no required dependencies on Python 3.12.
  W0.4 order: (1) stdlib `urllib` downloader driven by `data/corpus_sources.json`, which writes draft manifest rows; (2) read-only research of gates L4 → G13 → G12 → G6 → G4/G14 → G8; (3) born-digital central texts; (4) MP items as gates clear, then guides.
- Why: A wrong `text_layer` sends a file down the wrong path (OCR or not), the main source of bad quotes. W1.1 needs a PDF text reader anyway.
- Effects: ₹0 · ~1 MB pure-Python dependency · W0.4 likely runs past 9 Nov because MP sources are slow to find.

## DEC-042 — Minimum wages: Code on Wages governs; MW Act 1948 notifications handled by s.69 savings
- Date: 2026-11-06 | Status: accepted | Approved by: Malik (legal determination on L7)
- Context: The current MP wage notification (22288-337, 30.09.2026) says it is issued "under the Minimum Wages Act, 1948", which was repealed when the Code on Wages took effect.
- Decision (Malik's determination):
  - **Governing law:** the Code on Wages, 2019 is the current governing statute.
  - **Before 21.11.2025:** MW Act notifications issued before that date may continue under s.69(2), subject to consistency with the Code.
  - **After 21.11.2025:** notifications citing the repealed Act do **not** automatically get s.69(2) protection. Their validity needs the competent authority's continuing appointment, the statutory power used, and procedural compliance with the Code to be verified. A continuity argument exists via the saved CPI-linked structure and s.7(1)–(2).
  - **Corpus treatment:**
    1. Index the Code on Wages as the governing law.
    2. Keep pre-commencement wage notifications as *potentially saved*, subject to verification.
    3. Keep post-commencement notifications that cite the repealed Act in a **transitional legal-review state**.
    4. Never present the MW Act 1948 as operative.
    5. Preserve original references, dates, periods, historical rates and supersession links.
- Claude's verification (2026-11-06, official India Code PDF of the Code, "As on the 21th November, 2025", `IN.COW2019@en@1`):
  - s.69(1)–(3) text confirmed (p.30).
  - The S.O. 5322(E) dt 21.11.2025 commencement footnote is confirmed (p.5).
  - s.7(1)–(2) (cost of living allowance) confirmed (pp.9–10).
  - **Not verified:** *Garment and Textile Workers Union (R) v. Chief Secretary, Govt. of Karnataka*, 3 June 2026. Searches found only reports of related Karnataka HC writ appeals (1684–1685/2026) pending on s.69. Persuasive authority at most; not relied on until the judgment text is found.
- How it maps onto the schema (no schema change, chosen by Claude):
  - "Transitional legal review" = `mode: gated` with gate **L7**, so these notifications are never indexed while under review.
  - "Potentially saved" pre-commencement notifications = `gated` with gate **L8**.
  - The MW Act is an instrument with `superseded_by: ["IN.COW2019"]` and no indexed document.
- Effects: accuracy: the bot can't quote a wage amount from a notification whose legal basis is unsettled · application: wage-amount answers abstain until L7 clears or a W2.1 caveat wording is approved · cost ₹0.
- Follow-ups: L7 narrowed to the post-commencement MP VDA notifications (authority, power, procedure). L8 covers the 04.03.2024 MP base-rate notification (Extraordinary Gazette No. 68) as potentially saved. Answer wording for wages is decided in W2.1.

## DEC-043 — Interim source for the Shram Shakti Sanhita: PRS copy matched to the official gazette listing
- Date: 2026-11-07 | Status: accepted ("A") | Approved by: Malik
- Context: The official govtpress.mp.gov.in listing shows MP Rajpatra (Asadharan) No. 257 dt 10-08-2026, "मध्यप्रदेश कार्यस्थल सशक्तिकरण संहिता (श्रम शक्ति संहिता), अधिनियम, २०२६", Law and Legislative Affairs Dept. But its PDF link (`/uploads/gazette/2026-08-10-Ex-257.pdf`) returns 404. Malik confirmed that all the 2026 download links there are broken. PRS hosts a scan of that gazette issue.
- Options: **A) use the PRS copy, with its number, date, title and department matched to the official listing** · B) get a copy from the Government Press · C) wait for India Code / MP Code.
- Decision: **A, as an interim exception to the "never cite an aggregator" rule (ingestion rules).**
  - The manifest records the PRS URL as `source_url`, plus the official listing as evidence.
  - A `text_matches_source` verification is recorded with `by: malik`, method "official listing match".
  - Blank patches in the scan (preamble, s.1(3), s.2(घ), s.2(छ), s.3(2)) stay flagged; those provisions can't be quoted until a clean official copy exists.
  - Replace it with the official file as soon as govtpress, India Code or MP Code serves it (law-watch item).
- Why: the listing proves the gazette exists with this exact identity. The PRS scan shows the same gazette header and pages, so the risk is limited to the scan defects, which are flagged.
- Effects: accuracy: provisions in blank areas abstain · application: G4/G14 analysis can proceed · cost ₹0.
- Follow-ups: the status flag for "enacted, not yet commenced" (schema decision in the W0.4 review) must be settled before the manifest row is added.

## DEC-044 — Manifest schema: not-yet-commenced status, ordinances, amending instruments
- Date: 2026-11-07 | Status: accepted ("A" on all three) | Approved by: Malik | Amends DEC-033.2 (status flags) and DEC-040 (manifest)
- Context: W0.4 found three things the manifest couldn't describe honestly:
  - an Act that is assented and published but not in force (MP Act 7/2026, s.1(3))
  - an ordinance (Lok Seva 2020)
  - amendments that change an Act vs its Rules (Lok Seva 2026 amended the 2010 Rules)
- Options per gap: A) add a proper field/value · B) reuse an existing value with a note · C) mis-label or leave out.
- Decision: **A** for all three.
  1. New document status **`enacted_not_commenced`**.
     - Never current (`is_current` stays false).
     - The bot may explain the law only with a "not yet in force" caveat (wording in W2.1).
     - The validator errors if the instrument has a `commenced_on` while a document still uses this status, which forces a move to `in_force`.
  2. New instrument type **`ordinance`**: binding, authority rank 1 (same as an Act). Lapse/replacement is recorded via `superseded_by` / `valid_to`.
  3. New instrument field **`amends`**: a list of instrument ids this instrument changes. Each amending law is its own instrument (e.g. Lok Seva 2026 amendment → `amends: ["MP.LSGR2010"]`); the existing `amendments` list on the amended instrument stays as the per-section summary.
- Why: false statuses or wrong parents would leak into answers ("in force") and citations (wrong instrument). Later phases will hit all three cases again.
- Effects: ₹0 · ~½ day (validator, spec, tests, data migration) · status set grows to 8 flags.
- Follow-ups: move Lok Seva releases 2–5 to their own instruments once read; add the Sanhita document row as `enacted_not_commenced`.

## DEC-045 — W0.4 findings review: corpus treatment of the open gates (Malik's solution, v1)
- Date: 2026-11-07 | Status: accepted (v1; Malik may revisit in v2) | Approved by: Malik
- Context: The review of `docs/W0.4_FINDINGS.md` covered eight items. Malik approved Claude's recommendations with refinements, plus four cross-cutting improvements. `docs/W0.4_FINDINGS.md` is **kept unchanged** as the v1 record (not folded or deleted) so it can be revisited in v2.
- Decision:
  1. **L7 wages:**
     - Notifications stay gated; historical wage data is preserved.
     - Fetch the March 2024 base-rate notification (L8).
     - No definitive current wage amounts until an advocate verifies the post-repeal legal authority.
  2. **G13 legal aid:**
     - The MPSLSA Rules 1996 stay gated.
     - The ₹2 lakh figure from the official MPSLSA web page may be given as **qualified official guidance**: say explicitly that the notification reference is unresolved, and direct users to the DLSA.
     - Answers must also cover the other s.12 eligibility categories (not only income).
  3. **G12 RTI:**
     - Index the MP RTI (Fees and Appeal) Rules 2005 only after OCR correction and an amendment check.
     - Copy fees stay "actual cost, as decided by the PIO".
     - Implement state-vs-central public-authority routing.
  4. **G6 Lok Seva:**
     - The 2013 gazette list (via RCMS) is a **historical official source**; search for later notifications.
     - Any unverified deadline must state its source date and the uncertainty.
     - The 2025 services list must not be treated as the statutory time-limit notification.
  5. **G14 Shops Act / Sanhita:**
     - The MP Shops and Establishments Act 1958 + its 2025 amendments stay the applicable framework until commencement of the Sanhita is verified.
     - The Sanhita is registered as `enacted_not_commenced` (done, DEC-044).
     - Monitor commencement notifications; preserve provision-level commencement dates (`commencement_overrides`).
  6. **G8 land:**
     - Retry official sources for the complete Code, amendments and Rules. **Deadline 16 Nov 2026.**
     - If official texts are still unavailable, remove land-law advice from the November demo and move the module to December.
     - Never substitute secondary sources for verified legislation.
  7. **Roman clause IDs:**
     - Support roman numerals alongside alphabetic clauses, preserving the original numbering system.
     - Validate identifiers against the provision hierarchy. (Amends DEC-040.)
  8. **MP Acts 260 and 264 of 2026:**
     - Obtain and examine both.
     - First the Repeal Act (No. 260): affected corpus instruments, repeal dates, savings.
     - Then the Ease of Doing Business Act (No. 264): amendments to corpus laws.
  9. **Cross-cutting improvements (direction accepted; each gets a plan before implementation):**
     - (a) effective-date-based legal retrieval (answer "as of" a date)
     - (b) separate **legal-authority** and **source-quality** metadata (e.g. official file vs official-listing-matched copy vs scan with defects)
     - (c) a legal-impact analysis for every amendment and repeal (which instruments and provisions change, from when)
     - (d) re-run the affected golden-set evaluations after every legal change
  10. Keep unresolved documents gated; preserve original files and their hashes.
- Why: Each item keeps unverified law out of the index while preserving the evidence trail. The 16 Nov deadline protects the demo date (DEC-038).
- Effects: CORPUS.md and OPEN_QUESTIONS updated · schema changes in 9(b) and the uid change in 7 are implemented with tests · golden-set re-runs become part of the law-change flow (DEC-013) · cost ₹0.
- Follow-ups: implement item 7 (section_uid); plan 9(a)–(d); research items 1, 6, 8; the G13 notification number via Malik.

## DEC-046 — G8 demarcation: statute verified, Demarcation Rules 2018 qualified/gated
- Date: 2026-11-07 | Status: accepted | Approved by: Malik (research update on G8)
- Context: s.129 (as substituted by MP Act 23/2018 and amended by MP Act 1/2023) is verified from official copies. Malik located a full **reproduced** text of the MP Bhu-Rajasva Sanhita (Seemankan) Niyam, 2018. The original gazette is reported unavailable, and revenue.mp.gov.in is down.
- Decision:
  1. **Commencement:** MP Act 23/2018 commenced **25.09.2018**. Evidence: the official recital in the Nirdharan Rules 2018 r.1(2) (MP Code). Malik also reports a separately indexed commencement notification **No. 24-2018-VII-Sec-6 dated 16.08.2018** (not yet seen by Claude). The task to retrieve the original gazette stays open.
  2. **Demarcation Rules 2018 are registered as a separate instrument** (`MP.LRCDR2018`):
     - notification **No. F-2-13-2018-7-Se.7**, recorded date **28.01.2019**, parent `MP.LRC1959`
     - per the reproduced text: Rules 3–11, Forms I–III, agency provisions, team composition, fees and boundary-mark specifications
  3. **The reproduced text is not treated as source-verified.** The rules stay **qualified/gated** until the original gazette or an authoritative government copy is obtained.
  4. **The verified s.129 statutory content is not blocked** by the rules' status.
  5. **The bot must keep two provisions apart:**
     - **s.129(5):** an application to the **SDO** to set aside the confirmed demarcation, within **45 days** of confirmation or knowledge, whichever is later
     - **s.129(8):** **no appeal or revision** lies against orders or proceedings under s.129 (notwithstanding ss.44, 50)
  6. **No universal demarcation fee.** Rule 4 (reproduced) provides for **Collector-fixed fees with Commissioner approval**, so fees vary by district. Answers must not state a single amount.
  7. **To obtain:**
     - Forms I–III
     - current district Collector fee orders
     - orders authorising agencies
     - technical instructions under Rule 10
  8. **To investigate:** the reported in-force date of 01.02.2019 vs the reproduced notification/publication date of 28.01.2019.
- Why: The statute is verified, but the rules' text is a reproduction of unknown fidelity. Fees are local and changeable, and the SDO route vs the no-appeal bar is a common point of user confusion.
- Effects: the demarcation module is **not production-ready**. Answers come from s.129 only, plus "rules exist; procedure/fees vary by district; contact the Tahsil." · cost ₹0.
- Follow-ups: G8 sub-items in OPEN_QUESTIONS; the source URL/file of the reproduced copy from Malik (to keep its hash).

## DEC-047 — MP Code on Wages Rules drafts: version history; L7 stays gated
- Date: 2026-11-07 | Status: accepted | Approved by: Malik
- Context: MP has published two drafts of its Code on Wages Rules. Neither is final. L7 asks whether the post-repeal MP VDA notifications have a valid basis under the Code.
- Decision:
  1. **Draft versions:**
     - The **30.04.2026 revised draft** (No. 83/2026/A-16) is the **latest draft** in the corpus, labelled `draft` (never current, i.e. not in force).
     - The **05.01.2026 draft** is kept as an **archived historical version**, linked by `supersedes` / `superseded_by`.
     - Neither version is treated as final or operative rules.
  2. **L7 record:**
     - Proposed **Rule 5** supports the existing twice-yearly CPI-IW-based VDA revision cycle (before 1 April and 1 October).
     - Proposed **Rule 4** sets up an **advisory Technical Committee**; it is **not** the s.7(2) VDA computation authority.
  3. **S.O. 2451(E), 12.05.2026** is added to the research corpus. It appoints the **Director General, Labour Bureau** under s.7(2) for establishments where the **Central Government** is the appropriate Government. It does **not** resolve the MP state-sphere authority question.
  4. **L7 stays gated** until three things are verified:
     - (a) the MP s.7(2) appointment notification
     - (b) the 2024 base-rate notification (L8)
     - (c) the legal basis of the September 2026 VDA revision
  5. **Watch for a final MP Code on Wages Rules notification** periodically, preserving the draft-to-final version history (law-watch item).
- Why: Drafts are not law. The central appointment covers only the central sphere. Keeping the version chain preserves provenance for when final rules appear.
- Effects: no wage-amount answers (unchanged) · version history kept in the manifest · no new dependencies · ₹0.
- Follow-ups:
  - **Gate gap:** the DEC-040 index gate requires a confirmed `commencement` check, which a draft cannot have. Indexing drafts (DEC-037 row 7) needs a small schema/gate decision; until then the latest draft stays `gated`.
  - The official DMS copies of the drafts and the objection/action-taken reports (24–25.06.2026) are archived.

## DEC-048 — Index gate for drafts: a confirmed status check is enough
- Date: 2026-11-07 | Status: accepted | Approved by: Malik | Amends DEC-040 (index gate)
- Context: The DEC-040 index gate requires confirmed `status` and `commencement` checks. A draft has no commencement, so drafts could never be indexed, contradicting DEC-037 (draft rules are indexed with a `draft` label).
- Decision: A document with `status: draft` may be `mode: index` with a confirmed **`status`** verification alone. All other statuses keep the `status` + `commencement` requirement. The "no `conflict` verification" rule still applies to everything.
- Why: For a draft, what matters is proving it *is* the published draft. It is never current (`is_current` is false), so the bot always labels it as a draft and never as operative law.
- Effects: the 30.04.2026 MP Code on Wages Rules draft (`MP.WCR2026@en@1`) moves `gated → index` · validator + tests + spec updated · ₹0.

## DEC-049 — Internet Archive copies of official files count as authoritative government copies
- Date: 2026-11-07 | Status: accepted ("yes") | Approved by: Malik | Follows up DEC-046
- Context: revenue.mp.gov.in is down. The Internet Archive holds the Revenue Department's own PDFs. The Demarcation Rules PDF contains the gazette itself (MP Rajpatra Part 4(ग), 01.02.2019).
- Decision:
  1. **Which copies count:** an Internet Archive copy of a file served by an **official government domain** counts as an authoritative government copy, under four conditions:
     - (a) it is fetched with the archive's original-bytes form (`id_` URL)
     - (b) the manifest records the **original URL**, the **snapshot timestamp** and the **sha256**
     - (c) the content is read and verified like any other official file
     - (d) copies of aggregator sites do not qualify
  2. **Demarcation Rules 2018** (`MP.LRCDR2018@bi@1`) move **gated → index**.
     - Status and commencement are confirmed: in force 01.02.2019.
     - **Fee amounts stay gated:** the bot says fees are fixed by the Collector with the Commissioner's approval and vary by district, and never states an amount until Collector fee orders are obtained (G8d).
- Why: The archive stores the bytes the government server returned. With the original URL, timestamp and hash, the copy is as traceable as a live download.
- Effects: the demarcation procedure (Forms, team, agencies, boundary marks, SDO route) becomes answerable · fees remain qualified · ₹0.
- Follow-ups: G8c Forms I–III extraction; G8d–f operational orders; consider re-fetching from the live site when it returns (law-watch).

## DEC-050 — Wage amounts: state official schedule-specific rates with a legal qualification
- Date: 2026-11-08 | Status: accepted ("B") | Approved by: Malik | Supersedes the "no definitive current wage amounts" parts of DEC-045 item 1 and DEC-047 item 4 (L7 itself stays open)
- Context: The MP VDA notifications after 21.11.2025 cite the repealed MW Act 1948. An AI research note (not an advocate opinion; `docs/briefs/research_note_L7_L8_2026-11-07.md`) recommends publishing the officially notified rates with a qualification. The Oct 2026 notification's schedules were verified from the official copy.
- Options: A) keep the gate (no amounts) · **B) state official amounts with a legal qualification** · C) B only after a human advocate confirms.
- Decision: **B.**
  1. The bot may state the **officially notified** minimum-wage rates, always:
     - (a) for the **specific schedule** (67 general employments; the 3 new employments: textiles/made-ups, apparel, footwear; agriculture; beedi; agarbatti; slate pencil; printing press; government daily-wage …) **and skill category** asked about; **never one universal "MP minimum wage"**
     - (b) with the **notification number, issuing authority and validity period**
     - (c) with the qualification that the notification is issued under the 1948 Act, that a substantial s.69(2) continuity argument exists, that **its validity under the Code has not been decided by a court**, and that disputes go to the Labour Office, with DLSA for free legal aid
  2. Final answer wording is set in W2.1 (generation).
  3. `MP.MWVDAOCT2026@hi@1` moves `gated → index` (status, commencement and validity confirmed). The 47-page Book (`@hi@2`) stays gated until it is read and its number (22283-337) reconciled.
  4. **L7 stays open** for a human MP labour-law advocate. Their findings may change the qualification or the rates shown.
- Why: These are the operative, government-enforced figures. Disclosing the unsettled legal basis is more useful to workers than silence. Schedule specificity prevents the most likely user error (applying the general rate to textiles or agriculture).
- Effects: wage questions become answerable (after OCR of the notification) · law-watch must flag any court ruling or new notification (LW1) · ₹0.

## DEC-051 — `index_scope`: index only listed provisions of a document
- Date: 2026-11-08 | Status: accepted ("A") | Approved by: Malik | Amends DEC-040 (manifest)
- Context: DEC-037 indexes only parts of some Acts (TPA ss.105–111, Registration Act s.17, LSA Act s.12, DPDP s.44(3)). The manifest had no way to say so. Indexing the whole file would let the bot answer from out-of-scope text, e.g. DPDP sections not yet in force.
- Options: **A) optional per-document `index_scope` list of section_uids** · B) index the whole file and filter at answer time · C) keep such documents out of the index.
- Decision: **A.**
  1. New optional document field **`index_scope`**: a non-empty list of `section_uid`s. When present, only those provisions **and their descendants** (DEC-040 `covers()`) are chunked and indexed; when absent, the whole document is in scope.
  2. The validator rejects uids that are malformed, belong to another instrument, are the instrument itself, are duplicated, or are already covered by another listed uid.
  3. The chunker (W1.2) must apply it; a golden/unit test checks that no out-of-scope chunk is emitted.
  4. TPA, Registration Act and LSA move `archive → index` with their DEC-037 scopes. DPDP stays `archive`: its only in-scope change (s.44(3)) is already served by the amended RTI s.8(1)(j).
- Why: Scope written in the manifest and checked by code, like every other corpus rule; out-of-scope text never reaches the index.
- Effects: ₹0 · ~2 h (validator, spec, tests) · W1.2 chunker gains one filter.

## DEC-052 — `model_law` instrument type; status-only index gate for model laws
- Date: 2026-11-08 | Status: accepted ("A") | Approved by: Malik | Amends DEC-040 (manifest) and DEC-048 (index gate)
- Context: The Model Tenancy Act 2021 (MoHUA, 02.06.2021) is in the corpus as a model law (DEC-037), but the manifest had no fitting type (`act` = binding, `bill` = wrong) and the index gate required a commencement check a model law can never have.
- Options: **A) new `model_law` type, non-binding, lowest rank; status-only index gate** · B) register as `official_guide` (mislabel) · C) leave the MTA out.
- Decision: **A.**
  1. New instrument type **`model_law`**: not binding, authority rank 6 (with `bill`).
  2. A document with `status: model_law` may be `mode: index` with a confirmed **`status`** check alone (as drafts, DEC-048). It is never current.
  3. The validator requires every document of a `model_law` instrument to carry `status: model_law`, and a `model_law` instrument may not have `commenced_on`.
  4. The bot always labels it "model law; not in force in MP unless the state adopts it" (wording in W2.1).
- Why: An honest label stops the bot presenting a model law as MP law, while keeping a frequently asked-about text answerable.
- Effects: ₹0 · ~1 h · MTA EN indexed; the Hindi copy stays archive (N1 glyph corruption).

## DEC-053 — W0.5 OCR bake-off setup
- Date: 2026-11-10 | Status: accepted | Approved by: Malik ("run bodhan on colab directly"; "Tesseract on Colab too"; rest as recommended) | Refines DEC-014/015
- Context: Bodhan IndicOCR is a 33M layout model + 0.8B OCR model (~1.8 GB, gated on Hugging Face). The laptop GPU (MX450, 2 GB) is too small; Windows support of its installer is unclear. No PDF renderer or Tesseract was installed.
- Decision:
  1. **Bodhan runs on Google Colab only** (free GPU); no laptop CPU attempt (supersedes DEC-015's "20-page test on the laptop CPU").
  2. **Tesseract 5 (`hin` + `eng`) also runs in the same Colab notebook**; nothing is installed on the laptop.
  3. **`pypdfium2` + `pillow` join the `ingest` group** to render PDF pages to images locally (page selection, visual checks, Sarvam upload).
  4. Bodhan's own packages (torch etc.) are installed **only in the Colab notebook**, not in `uv.lock`; only text outputs come back to the repo.
  5. **One paid Sarvam Document Digitization run of the same 20 pages** (₹0.5/page per docs.sarvam.ai pricing, ~₹10 + GST; price re-checked on the live page before the run).
  6. **Ground truth:** each page is pre-filled from Tesseract and fully corrected by Malik. Uncorrected leftovers can only favour the baseline, so the comparison is conservative for Bodhan; the report states this.
  7. **Corrected ground-truth texts are committed** under `data/ocr_gt/` (public law text, small) so the CER table is reproducible.
  8. Metric: CER and WER per engine and per page type, on raw text and after the project's NFC + nukta-folding normaliser.
- Why: Colab is the only practical GPU; one environment for both free engines keeps the comparison fair; the lockfile stays free of torch/CUDA; committed ground truth makes the eval report checkable.
- Effects: ~₹10 + GST · ~1.5 days Claude + 2–3 h Malik · W1 slips ~1 day · Malik actions: accept the Bodhan licence on Hugging Face, put `SARVAM_API_KEY` (and an HF read token in Colab secrets) in place.
- Follow-ups: verify pypdfium2/pillow licences from installed metadata; record the Bodhan model revision hash used; licence = Indic Open Model License v1.0 (internal use; credit "Built with IndicOCR from Bodhan AI / AI4Bharat" in the README).

## DEC-054 — Stored text keeps the nukta; folding only for comparison keys
- Date: 2026-11-10 | Status: accepted ("yes") | Approved by: Malik | Amends the "normalise before storing" line in `.claude/rules/ingestion.md` (OPEN_QUESTIONS S10)
- Context: The ingestion rule said all text passes through the NFC + nukta-folding normaliser before it is stored. Folding is lossy (ज़ → ज), so stored chunks, and the quotes the bot shows users, would be misspelt.
- Options: A) fold everything at storage (rule as written) · **B) store NFC text with invisible characters removed; fold only when building comparison keys** · C) store raw text, normalise nothing at storage.
- Decision: **B.** Stored and displayed text = `normalize(text, fold_nukta=False)` (NFC, zero-width/BOM/soft-hyphen removed). The full fold (`fold_nukta=True`) is applied only to comparison keys: BM25 tokens, the citation validator's quote check (both sides folded), dedup keys and OCR metrics. Embeddings use the stored (unfolded) text.
- Why: Users see the law spelt as printed. Matching still works when a user or an OCR engine drops the nukta, because both sides are folded the same way before comparing.
- Effects: `common/normalize.py` already supports both modes · the quote check compares folded forms, so a dropped nukta never fails a correct citation · ₹0.

---

## Pending decisions (not yet made)

| Topic | Raised in | Status |
| --- | --- | --- |
| DynamoDB table design + capacity mode (provisioned vs on-demand) + TTL | R10 | Malik: "will decide later". Must be decided before DEC-010/012 code |
| Monthly budget for paid eval API calls | R4 | To discuss later |
| Second (higher) AWS alert that includes Bedrock | R4 | To discuss later |
