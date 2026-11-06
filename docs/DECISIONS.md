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

---

## Pending decisions (not yet made)

| Topic | Raised in | Status |
| --- | --- | --- |
| DynamoDB table design + capacity mode (provisioned vs on-demand) + TTL | R10 | Malik: "will decide later". Must be decided before DEC-010/012 code |
| Monthly budget for paid eval API calls | R4 | To discuss later |
| Second (higher) AWS alert that includes Bedrock | R4 | To discuss later |
