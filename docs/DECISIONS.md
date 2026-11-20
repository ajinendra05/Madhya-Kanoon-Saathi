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

## DEC-055 — W1.1 chunk schema, extraction and build QA
- Date: 2026-11-10 | Status: accepted (6 choices as recommended + Malik's 5 mandatory amendments; 4 details chosen 2026-11-10) | Approved by: Malik | Amends DEC-041 (W1.1 text reader)
- Context: Every later step (BM25, embeddings, citations, eval) reads chunks, so the chunk fields are a data schema. On the India Code PDFs, pypdf splits words ("reject ion", "sub -section ( 1)"; 7 per sample page) where pypdfium2 gives 0.
- Decision:
  1. **Extractor:** pypdfium2 text extraction for born-digital PDFs (replaces pypdf for W1.1; pypdf stays for text-layer detection).
  2. **Chunk unit:** sub-section with provisos/explanations attached; a section without sub-sections is one chunk; never merge across sections.
  3. **Long units (> 450 tokens):** split at clause boundaries, each part with its own deeper `section_uid`; only a single over-long clause gets a `~n` suffix on its `chunk_id`.
  4. **Amendment footnotes:** footnote numerals removed from canonical text, square brackets kept; footnote text attached as metadata.
  5. **Token count:** estimate now; recalibrate with the BGE-M3 tokenizer in W1.4. 150–450 is a target, not a gate.
  6. **Output:** `data/parsed/chunks.jsonl` (git-ignored), rebuilt by one script.
  7. **Malik's amendments:**
     - (a) **Raw + canonical text:** `raw_text` = the extractor's text for the span unchanged (only page headers/footers removed); `text` = canonical form (DEC-054 normaliser, footnote numerals stripped, line-wraps joined). Quotes are checked against `text`; `text` maps back to `raw_text` for audits.
     - (b) **`section_uid` is a language-independent legal-provision identity** (as DEC-040): Hindi and English chunks of the same provision share it; `chunk_id` carries the language.
     - (c) **`jurisdiction`** (`IN`/`MP`, from the instrument) on every chunk, and **source locators**: `{kind: "pdf_page", pages}` or `{kind: "html", url, anchor/selector, heading path}`.
     - (d) **Version part of `chunk_id`** when the document has no `valid_from`: provision commencement override → instrument `commenced_on` → `enacted_on` → `nd-` + first 8 hex of the document sha256. Never the fetch date.
     - (e) **Extraction QA + reproducible build manifest.** Build **fails** on: invalid `section_uid`, chunk outside `index_scope`, missing page/locator, raw/canonical mismatch, duplicate `chunk_id`. Build **warns** on: token count outside 150–450, suspected split words, section-number gaps, low text per page. `build_manifest.json` (git commit, code + library versions, input sha256s, normaliser version, output sha256, counts) and `qa_report.md` are **committed**; chunks stay git-ignored.
  8. **Scope:** W1.1a = born-digital English PDFs + HTML guides now; W1.1b = scanned/Hindi pages from OCR after the W0.5 ground truth.
- Why: one provision = one citable unit; canonical text keeps quotes exact while raw text keeps an audit trail; hard QA gates turn "no unverified text reaches the index" into code; the committed build record makes every index snapshot traceable.
- Effects: ₹0 · no new dependency · ~1.5–2 days · full field list in `docs/specs/chunks.md`.

## DEC-056 — Chunk version uses the latest amendment to the provision
- Date: 2026-11-11 | Status: accepted ("ok for s12") | Approved by: Malik | Amends DEC-055 item 7d (OPEN_QUESTIONS S12)
- Context: India Code consolidated copies have no `valid_from`, so an amended provision got the Act's commencement date as its version (RTI s.8(1), whose clause (j) was substituted w.e.f. 13.11.2025, showed version 2005-06-15).
- Decision: The version chain becomes: document `valid_from` → provision commencement override → **latest `amendments[].commenced_on` whose `affects` uid covers the chunk uid or is covered by it** → instrument `commenced_on` → `enacted_on` → `nd-<sha8>`. `version_source` = `amendment`. Amendments are recorded in the manifest from official sources (e.g. India Code footnotes), with the amending Act as `by` (it may be outside the corpus).
- Why: the version date should say when the text in the chunk took its current form; that is what "valid from" means to a user.
- Effects: chunk_ids of amended provisions change (rebuild) · needs amendment entries in the manifest (added now for RTI s.8(1)(j) and IRC s.104(1)) · ₹0.

## DEC-057 — `sp` segment for decimal-numbered guideline paragraphs
- Date: 2026-11-11 | Status: accepted | Approved by: Malik | Amends DEC-040 (section_uid grammar)
- Context: Scheme guidelines (PM-SVANidhi 2025) number paragraphs 5 > 5.1 > 5.1.1 > a). The section_uid grammar had no numeric level under a paragraph, but users and citations name "para 5.1.1".
- Options: **A) new repeatable `sp<n>` segment under `para`** · B) flat label `para5_1_1` (loses coverage: para5 would not cover it) · C) chunk only at top level (loses precision).
- Decision: **A.** `sp<n>[A]` = numbered sub-paragraph; it may follow `para` or another `sp` (so it repeats for each decimal level) and can be followed by clauses (`cl_`/`clr_`), sub-clauses, provisos and explanations as usual. Example: para 5.1.1 = `IN.SVANSG2025:para5:sp1:sp1`; its item a) = `…:sp1:sp1:cl_a`.
- Why: keeps the hierarchy, so `covers()` stays correct for eval (a retrieved "para 5" covers a question about 5.1.1) and citations keep the printed precision.
- Effects: `common/section_uid.py` + spec + tests · ₹0 · no change to existing uids.

## DEC-058 — BM25 index: bm25s 0.3.16, one combined index
- Date: 2026-11-11 | Status: accepted | Approved by: Malik | Implements DEC-003 (BM25 part) and DEC-026
- Decision:
  1. **Dependency:** `bm25s==0.3.16` (MIT per PyPI classifiers; only required dependency numpy), pinned in `uv.lock`, in the `serve` group (queried inside the Lambda; the index build uses the same code). Licence re-checked from installed metadata.
  2. **One index** over all chunks (English and Hindi together). Indexed tokens per chunk = `tokenize(text)` + `provision_tokens(section_uid)` + `tokenize(heading)` (DEC-026 tokeniser, shared with queries).
  3. **Scoring:** Okapi BM25, k1 = 1.5, b = 0.75.
  4. **Filters after scoring**, from chunk metadata: jurisdiction guard (`applies_to` state level only MP; central/national always) and currency on the query date (not expired, within `valid_from`/`valid_to`; `draft`, `model_law`, `enacted_not_commenced` chunks are kept but flagged for the answer layer).
  5. **Files:** `data/index/bm25/` (git-ignored) with the chunk_id order and a committed build record next to the chunk record.
- Why: section-number queries ("धारा 8(1)(j)") need exact keyword matching across languages; one index keeps the shared section tokens matching across Hindi and English chunks.
- Effects: +numpy, +bm25s in the Lambda image (small) · ₹0.

## DEC-059 — Instrument titles and aliases as BM25 tokens
- Date: 2026-11-11 | Status: accepted ("A") | Approved by: Malik | Amends DEC-058 item 2
- Context: Keyword search could not tell which Act a bare section number belongs to ("धारा 8(1)(j)" ranked CPA s.8(1) above RTI s.8(1)), and an Act named in a query only matched if its words happened to be in the chunk text.
- Decision: Every chunk also gets the tokens of its instrument's **English and Hindi titles** (manifest `title_en` / `title_hi`) and of a short **alias list** in `data/instrument_aliases.json` (common abbreviations such as "RTI"; Hindi short names only where an official source spells them, with the source recorded). Hindi titles are added to the manifest only from an official Hindi copy (first: RTI Act, India Code Hindi PDF p.1). Aliases are search aids only, never shown to users as titles.
- Why: names the Act a user means ("RTI dhara 8"), and lets a Hindi Act name match English chunks of the same Act.
- Effects: one shared token set per instrument (low IDF, so it only tips ties between Acts) · ₹0 · Hindi titles for other central Acts need their official Hindi copies (OPEN_QUESTIONS S14).

## DEC-060 — W1.4 embedding setup: official BGE-M3 ONNX, own int8, laptop CPU
- Date: 2026-11-12 | Status: accepted (all as recommended) | Approved by: Malik | Implements DEC-004/021/022/025
- Decision:
  1. **Model:** BAAI's own ONNX export of `BAAI/bge-m3` (MIT, not gated), pinned to revision `5617a9f61b028005a4858fdac845db406aefb181`; fp32 = `onnx/model.onnx` + `onnx/model.onnx_data` (~2.27 GB). **int8 is made by us** with onnxruntime dynamic quantization; sha256 of every model file is recorded and checked (DEC-022 checksum pinning).
  2. **Libraries:** `serve` group: onnxruntime 1.31.1 (MIT), tokenizers 0.23.3 (Apache-2.0; loads `tokenizer.json`, no torch), faiss-cpu 1.15.1 (MIT; 1.16.0 was 2 days old). `ingest` group: onnx 1.23.2 (Apache-2.0; only for building the int8 file). Licences re-checked from installed metadata.
  3. **Where:** models in git-ignored `data/models/`; embeddings computed on the laptop CPU (same runtime as the Lambda).
- Why: provenance traceable to BAAI; the same ONNX runtime at build and query time is what DEC-022's parity test needs; no torch in the Lambda image.
- Effects: ~2.3 GB download (free) · W1.5 reranker has no official ONNX file: exporting it needs torch (separate decision) · ₹0.

## DEC-061 — Embed the Act title and heading path with each chunk
- Date: 2026-11-12 | Status: accepted ("S16 - yes") | Approved by: Malik | Amends DEC-054's "Embeddings use the stored (unfolded) text" (OPEN_QUESTIONS S16)
- Decision: The text given to the embedding model is `<instrument title> \n <path joined with " > "> \n <chunk text>` (title in the chunk's language when the manifest has it, else English). Stored and displayed chunk text is unchanged. Queries are embedded as typed (no prefix). The text-only vectors of 2026-11-12 are kept (git-ignored `dense-<variant>-v1`) so the eval can compare both.
- Why: later sub-section chunks do not repeat their section heading or Act name, so their vectors miss what the chunk is about.
- Effects: re-embedding ~30 min (both variants) · ₹0.

## DEC-062 — Reranker: one-time ONNX export on Colab
- Date: 2026-11-12 | Status: accepted ("S18 - A") | Approved by: Malik | Implements DEC-005 (OPEN_QUESTIONS S18)
- Decision: `BAAI/bge-reranker-v2-m3` (Apache-2.0) is exported to ONNX **once on Google Colab** (torch there only), with the revision pinned and sha256 recorded; Malik runs the notebook and downloads the file. int8 is then made locally with the same onnxruntime dynamic quantisation as the embedder. No torch on the laptop or in the Lambda image.
- Why: same runtime as the embedder; no large temporary install on the laptop.
- Effects: one Colab run by Malik · ~2.3 GB download, ~0.6 GB int8 · ₹0.

## DEC-063 — Golden set: adopt Malik's seed schema (v0.1-seed) with fixes
- Date: 2026-11-13 | Status: accepted ("go ahead on 1, 2 and 3a and 4") | Approved by: Malik | Implements plan section 7 / W2.6 early
- Context: Malik supplied a 120-row synthetic seed set (`build_seed.py`, JSONL, review CSV, README). A check against the repo on 2026-11-12 found 58 of 93 cited provisions retrievable, plus id mismatches, an outdated README and no land rows.
- Decision:
  1. **Schema adopted** as written: `expected_behavior` (answer / answer_with_caveat / abstain_refer / ask_clarifying / crisis_route / gated), `answerability`, `unanswerable_reason`, `gates`, `incident_date`, `expected_clauses[]` with `confidence` and `needs_verification`, `key_facts`, `must_include` / `must_not_include` (case-insensitive regexes), `expected_escalation`, empty reference answers, `review_status`, `verified_by/on`, `law_as_of_date`.
  2. **Location:** `data/golden/v0.1-seed/` (DEC-030), generated by `scripts/build_golden_seed.py` (Malik's builder, kept as the single source; edits go there).
  3. **Fixes applied:** `IN.OSH2020` → `IN.OSHC2020`; DPDP s.44(3) clauses replaced by RTI s.8(1)(j) (DEC-051); GS-110 facts per the official e-Shram FAQ (16 and above, no upper limit); invalid scheme-guide ids replaced by corpus ids or set to null with a note; README brought in line with DEC-007/016/017/030.
  4. **Additions:** 8–10 land-procedure rows (DEC-038), about 3 of them should-abstain.
  5. **Coverage checker** (`scripts/check_golden.py`) reports for every expected clause whether it is retrievable now, gated, outside `index_scope`, missing from the manifest or waiting for OCR.
  6. Still not decided here: wider LSA scope (3b) and consumer fee rules (3c, stays later per DEC-037).
- Why: the eval (W1.6/W1.7, DEC-021 int8 check) needs questions now; a checker keeps the set honest about what the corpus can actually answer.
- Effects: v0.1-seed is a draft (`draft_unverified`); v1.0 is frozen only after Malik's verification (eval rules) · ₹0.

## DEC-064 — Wider index scope for the Legal Services Authorities Act
- Date: 2026-11-13 | Status: accepted ("yes for 3b") | Approved by: Malik | Amends DEC-037 (LSA Act: s.12 only)
- Context: 7 golden seed clauses (6 legal-aid rows) cite LSA ss.13, 19, 21, 22A, 22B (who is entitled, Lok Adalats, Permanent Lok Adalats), which the s.12-only scope left unanswerable.
- Options: **A) widen `index_scope` to ss.12, 13, 19–22B** · B) keep s.12 only and rewrite those rows as should-abstain.
- Decision: **A.** `IN.LSA1987@en@1` `index_scope` = s12, s13, s19, s20, s21, s22, s22A, s22B (headings confirmed in the India Code PDF contents, 2026-11-13). ss.22C–22E (Permanent Lok Adalat cognizance and procedure) are not included now.
- Why: Lok Adalats are a free, statutory route that users ask about; the text is born-digital and already verified as the in-force India Code copy.
- Effects: chunks, BM25 and dense indexes rebuilt · CORPUS.md item 13 updated · ₹0.

## DEC-065 — Retrieval eval: strict + lenient matching; indexed-row and all-row sets
- Date: 2026-11-13 | Status: accepted (both as recommended) | Approved by: Malik | Implements plan §7 retrieval metrics (W1.7)
- Context: Seed golden rows often name a broader provision than the chunk that answers it (expected LSA s.12; chunks are s.12 clauses), and many rows cite laws that are gated today.
- Decision:
  1. **Matching:** report both. **Strict** = DEC-040 `covers(chunk, expected)` (chunk equal to or an ancestor of the expected provision); this is the gated metric. **Lenient** = strict or the chunk is a descendant of the expected provision. An act-level expected clause (`section_uid: null`) uses the instrument id.
  2. **Row sets:** headline and gates on rows whose expected clauses all have a chunk in the index now (**indexed**); also report **all** rows with expected clauses (shows corpus gaps).
  3. **Metrics per row, averaged:** Recall@10 = share of expected clauses matched by a top-10 chunk; MRR@10 = 1 / rank of the first matching chunk (0 if none); nDCG@10 with binary gain, where a chunk gains only if it matches an expected clause not matched higher up (IDCG = min(|expected|, 10) hits).
  4. Plan gates (Recall@10 ≥ 0.85, MRR@10 ≥ 0.6) are **reported, not enforced in CI**, while the golden set is the unverified v0.1 seed. Every report is sliced by language × domain × answerability (eval rules).
- Why: strict keeps the citation-precision meaning of DEC-040; lenient shows how much of the gap is labelling granularity that the golden review will fix. Gating on indexed rows measures the retriever, not missing laws.
- Effects: `eval/retrieval_metrics.py` + `scripts/eval_retrieval.py`; committed reports under `reports/` · ₹0.

## DEC-066 — int8 dense model retained provisionally; DEC-021 validation clarified
- Date: 2026-11-13 | Status: accepted (option B, with clarifications) | Approved by: Malik | Clarifies DEC-021 (threshold unchanged)
- Context: W1.7 seed eval (`reports/retrieval/v0.1-seed_2026-11-13_dense-int8-vs-fp32.md`): dense int8 vs fp32 Recall@10 is -0.017 overall, 0.000 en, 0.000 hinglish, **-0.042 hi**, which is one question of 24 on unverified seed labels.
- Options: A) switch to fp32 now · **B) keep int8 provisionally, re-check on the verified golden set** · C) change the margin to a question count (rejected: one allowed miss grows more permissive as the sample grows).
- Decision: **B.** int8 status = **`provisional_pending_validation`**; it is **not** validated for production until it passes on the verified, frozen golden set. The DEC-021 requirement stays: Recall@10 no more than 0.02 below fp32 overall and per language. Added requirements for the final comparison:
  1. Same frozen questions, corpus snapshot, expected provision ids, retrieval configuration and eval code for both.
  2. Coarse parent-section labels corrected to the actual retrievable provision ids first.
  3. Per language: questions, hits, misses and paired disagreements reported.
  4. Paired bootstrap confidence intervals (or another paired test) to quantify uncertainty.
  5. A language slice too small for a meaningful conclusion is marked **`insufficient_sample`**, not pass/fail.
  6. Target at least 50 verified questions per language before the 0.02 tolerance is used as a one-question threshold (a practical minimum, not a significance guarantee).
  - Failure: if the verified eval shows int8 beyond the allowed loss, switch to fp32 or benchmark another quantisation.
- Also decided: plan gates (Recall@10 ≥ 0.85, MRR@10 ≥ 0.60) are **not lowered**. Next order: (1) freeze the W1.7 baseline (commit b856aef + 13 Nov report); (2) correct golden labels; (3) fix genuine misses GS-075, GS-007, GS-057 with regression tests; (4) BM25 (S15) and fusion vs dense-only; (5) re-run int8 vs fp32 paired per language; (6) production precision decision.
- Why: one question on an unverified 24-row slice is too little evidence for a 3.8× larger model, but the result must not be recorded as a pass.
- Effects: no model change · eval script gains paired per-language reporting before step 5 · ₹0.

## DEC-067 — In-force law ranks before not-in-force text after reranking; GS-057 relabelled
- Date: 2026-11-14 | Status: accepted ("yes" to B and A) | Approved by: Malik | Amends DEC-058 item 4 (flagged chunks kept) · DEC-066 step 3
- Context: S21 regressions. GS-007 (monthly-tenancy notice): TPA s.106(1) is retrieved but the reranker puts five Model Tenancy Act chunks (model law, not in force in MP) above it (rank 6). GS-057 (hospital negligence): the expected CPA s.2(42) "service" definition never mentions medical treatment; the statutory hook is s.2(11)(i) "any act of negligence" (chunk text checked), which the reranker already ranks 2nd. GS-075 (neighbour's salary via RTI): vocabulary gap; s.8(1) is at dense rank 137; a clause-only (j) chunk scores lower (0.398 vs 0.436), so chunking is not the fix.
- Options (ordering): A) keep the reranker order; the answer layer handles flags · **B) after reranking, stable-partition: in-force chunks first, not-in-force chunks after** · C) drop not-in-force chunks unless the query names the law. Options (GS-057): **A) expected s.2(11) high + s.2(42) low** · B) keep label.
- Decision:
  1. **B.** `rerank_hits` scores the whole pool, then keeps the reranker order inside two groups: chunks whose status is **not in force** (`draft`, `model_law`, `enacted_not_commenced`, `passed_awaiting_assent`, `proposal`) go after all other chunks; then the top k is cut. `sub_judice_flag` law is in force and is **not** demoted. This orders by in-force status, not by authority rank (DEC-040 unchanged); flags still go to the answer layer.
  2. **GS-057 label A:** expected `IN.CPA2019:s2:ss11` (high) + `IN.CPA2019:s2:ss42` (low); row stays `answer_with_caveat` (coverage of hospitals comes from case law, not in the corpus).
  3. **GS-075:** no retrieval change now; fixed by query rewriting in W2 (no hand-written synonym list: that would encode legal interpretation). Its regression test is `xfail(strict=True)` until then.
  4. Each of the three rows gets a golden regression test on the real index.
- Why: the bot should lead with binding law; model-law text stays available when nothing in force matches. The GS-057 label now names what the statute text supports.
- Effects: estimated rerank-int8 MRR@10 +0.014 on indexed rows (GS-007 rank 6 → 1), recall unchanged · ₹0 · ~1 h.
  Measured (`reports/retrieval/v0.1-seed_2026-11-14_dec067.md`): rerank-int8 strict MRR@10 0.463 → 0.486, R@10 0.606 → 0.615; only GS-007 and GS-057 changed.

## DEC-068 — Reranker candidate pool stays RRF 1:1; S15 deferred
- Date: 2026-11-14 | Status: accepted ("Yes" to A) | Approved by: Malik | DEC-066 step 4 (S15, S20)
- Context: S20 saw RRF below dense-only. But the reranker re-sorts its whole pool, so the measure that matters is **pool recall** (expected provisions inside the pool), not the fused order. The index is 100% English today (3,042 chunks; Hindi copies await OCR, W1.1b), so BM25 finds nothing for 19 of 24 Hindi questions; none of the 130 seed questions cites a section number.
- Evidence (`scripts/compare_fusion.py`, `reports/retrieval/v0.1-seed_2026-11-14_fusion.md`; 58 indexed seed rows, strict): pool@40 dense-only 0.647 · **RRF 1:1 0.681** · RRF with BM25 ×0.5 0.647 · dense 30 + BM25 10 0.672 · RRF without BM25 for Devanagari 0.681. At pool 20: RRF 1:1 0.615 vs Devanagari-skip 0.649 (Hindi 0.507 vs 0.590: BM25 title-token matches push out dense hits). Differences are 1–3 provisions.
- Options: **A) keep RRF 1:1 at pool 40; Devanagari-skip as the pool-20 fallback; defer S15** · B) dense-only (lower pool recall, worst on en/hinglish) · C) add the Devanagari skip now (no gain at 40; a temporary rule).
- Decision: **A.**
  1. No retrieval change: BM25 + dense, RRF K = 60, equal weights, pool 40, then rerank (DEC-021, DEC-067).
  2. If S19 forces a smaller pool, re-run `compare_fusion.py`; "no BM25 for Devanagari queries" is the candidate then, re-checked once Hindi chunks are indexed.
  3. **S15 deferred:** add ~5 section-number questions (e.g. "RTI dhara 8(1)(j)") when golden v1.0 is built (W2.6), then measure before any scoring change.
- Why: the fused order is not what the generator sees; RRF gives the reranker the most expected provisions, mainly through English exact-term matches dense misses (e.g. RTI definitions in s.2).
- Effects: ₹0 · no code change in the pipeline · `compare_fusion.py` kept for re-runs.

## DEC-069 — Bulk OCR may run on Kaggle Notebooks as well as Colab
- Date: 2026-11-15 | Status: accepted ("A") | Approved by: Malik | Amends DEC-053 item 1 ("Bodhan runs on Google Colab only")
- Context: The W1.2 bulk run (635 pages) failed on a CPU runtime because Malik's free Colab GPU quota was used up. The laptop GPU (2 GB) is too small (DEC-053).
- Options: **A) Kaggle Notebooks (free GPU)** · B) wait for the Colab quota to reset · C) paid Colab compute units.
- Decision: **A.** One notebook (`notebooks/ocr_bulk_colab.ipynb`) detects Colab or Kaggle and runs the same pipeline on either:
  - same Bodhan revision (cd50d301…), pypdfium2 pin and 300 dpi, sha256 check of every PDF;
  - on Kaggle: inputs as a **private** Kaggle Dataset (read-only `/kaggle/input`), outputs in `/kaggle/working`, `HF_TOKEN` as a Kaggle secret, accelerator **GPU T4**, run with "Save & Run All";
  - the run stops itself before Kaggle's session limit so outputs are saved; a later version resumes by attaching the previous version's output as input;
  - `run_info.json` records which platform and GPU ran each session.
- Why: free, available today, and the pinned model/renderer keep results identical in kind to the bake-off, so DEC-053's quality basis still holds.
- Effects: ₹0 · new external service (Kaggle; free tier, GPU quota and session limits not verified) · Malik needs a phone-verified Kaggle account for internet access (not verified).
- Follow-ups: record Kaggle's actual GPU quota and session limit from the account's quota page; per-page time from the first session.

## DEC-070 — November land slice: demarcation only; mutation moves to December
- Date: 2026-11-16 | Status: accepted ("B") | Approved by: Malik | Applies DEC-045 item 6 (16 Nov deadline); narrows DEC-038
- Context: The 16 Nov deadline for official land texts (G8) passed with G8a parked: no current official consolidation of MPLRC ss.109–110 (mutation) or verified Mutation Rules 2018. Demarcation is verified: s.129 as substituted by MP Act 23/2018 (commenced 25.09.2018) and amended by MP Act 1/2023 (DEC-046), and the Demarcation Rules 2018 are indexed (DEC-049).
- Options: A) drop land from the November demo (DEC-045 as written) · **B) keep only the verified demarcation procedure** · C) extend the deadline.
- Decision: **B.**
  1. **November demo:** demarcation procedure only. Sources: MPLRC s.129 (current text) and the Demarcation Rules 2018 (Forms, team, agencies, boundary marks, SDO route). Fees stay qualified (no amounts, DEC-049); s.129(5) SDO application vs s.129(8) no-appeal bar kept apart (DEC-046).
  2. **Moved to December (stay gated):** mutation (ss.109–110, Mutation Rules 2018 EN/HI) and the Bhulekh/Cyber Tehsil record-copy guide. Mutation questions get a referral answer (Tahsil office / DLSA) until then; wording in W2.1.
  3. **Still November:** the jurisdiction guard for land and the dispute detector (DEC-038) — "who owns it" and boundary-dispute merits go to DLSA.
  4. **Golden set:** land rows asking about mutation or record copies become out-of-corpus for v1.0 (expected behaviour re-checked at the W2.6 freeze); demarcation rows stay.
- Why: demarcation is fully verified from official copies and is a common rural question; mutation without a verified current text would risk quoting superseded law.
- Effects: ₹0 · less land ingestion work in November · the demo keeps a land story.
- Follow-ups: (a) how to index the current s.129 text, since the MP Code consolidation (`MP.LRC1959@en@1`) is pre-2018 and the current wording sits in the 2018 amending Act plus the 2023 amendment (small schema/ingestion decision before W1.1b reaches land); (b) OCR of MP Act 1/2023 (bulk part p5); (c) G8a resumes in December.

## DEC-071 — OCR text is indexed before the W0.5 error rate is known; key provisions spot-checked
- Date: 2026-11-17 | Status: accepted ("go with recomm.": A + C) | Approved by: Malik | W1.1b
- Context: The bulk Bodhan run (635 pages) is done, but the OCR character error rate is unknown until Malik finishes the W0.5 ground-truth correction. 8 indexed documents (RTI Rules EN/HI, three consumer gazettes, WCR draft, Demarcation Rules, Oct 2026 wage notification) can only be chunked from OCR text, and the bot will eventually quote it.
- Options: **A) index now, every chunk records `extraction: ocr:bodhan@<revision>`; the quoting policy for OCR chunks is set in W2.1 from the W0.5 error rate** · B) wait for the error rate (blocks W1.1b) · **C) Malik spot-checks the golden-set provisions from OCR documents against the PDF pages before the demo**.
- Decision: **A + C.**
  1. OCR chunks are indexed now; `extraction` names the engine and revision (spec field, no schema change).
  2. **Wage tables:** every wage row must pass an arithmetic check (base + VDA = total; daily = monthly ÷ the printed day basis, within rounding) or the build fails.
  3. Before the demo, Malik checks the OCR text of the provisions the golden set expects (now IN.RTIR2012 r3, IN.CPJR2021 r3, MP.LRCDR2018 r3/r4, the wage schedules) against the PDF pages.
  4. W2.1 decides how answers quote OCR chunks, using the W0.5 CER/WER.
- Why: retrieval work and the eval can continue; the pages that matter most get human eyes; a misread wage digit is caught by arithmetic, not luck.
- Effects: ₹0 · ~30 min of Malik's time · OCR chunks are distinguishable everywhere downstream.

## DEC-072 — `sch_<letter>` segment for Hindi-lettered schedules
- Date: 2026-11-17 | Status: accepted ("go with recomm.": C) | Approved by: Malik | Amends DEC-040 (section_uid grammar)
- Context: The Oct 2026 MP wage notification (`MP.MWVDAOCT2026@hi@1`, Hindi only) numbers its schedules with Devanagari letters (अनुसूची क, च, द …). The grammar only had numbered schedules (`sch<n>`), and there is no English text to align with (spec rule 2).
- Options: A) `sch<n>` by alphabet position (क=1 … द=18; opaque) · B) `sch<n>` in printed order (fragile: OCR page order is not alphabet order) · **C) new top-level segment `sch_<x>` with a fixed transliteration**.
- Decision: **C.** `sch_<x>` = schedule labelled with a Devanagari letter, `x` from a fixed table in `docs/specs/section_uid.md` (e.g. क → `ka`, च → `cha`, द → `da`; a conjunct or compound label maps letter by letter). It is top-level like `sch<n>`, may be followed by `para`, and is used only when the source has no English numbering to align with.
- Why: the uid matches what is printed and what users say ("अनुसूची च"), and follows the existing `form_<x>` pattern.
- Effects: `common/section_uid.py` + spec + tests · ₹0 · no change to existing uids.

## DEC-073 — Part (खण्ड) letter appended when two schedules share a letter
- Date: 2026-11-17 | Status: accepted ("confirm ... s25a as yes") | Approved by: Malik | Amends DEC-072 (OPEN_QUESTIONS S25a)
- Context: `MP.MWVDAOCT2026@hi@1` has two schedules lettered अ: "अनुसूची-अ (खण्ड-ब)" (67 scheduled employments) and "(खण्ड-अ - अनुसूची-अ)" (the 3 new employments). `sch_a` alone would give both the same uid.
- Decision: `sch_<x>_<y>`, where `y` is the खण्ड (part) letter with the same fixed transliteration table: `sch_a_ba` (अनुसूची-अ, खण्ड-ब) and `sch_a_a` (खण्ड-अ, अनुसूची-अ). The part is added only when the label carries one; at most one part qualifier.
- Why: keeps the printed label readable in the uid and stays inside the DEC-072 pattern.
- Effects: already implemented in W1.1b (`common/section_uid.py`, `ingestion/wage_tables.py`, spec, tests) · ₹0.

## DEC-074 — W2.0 crisis router: rules + embeddings, per-category replies, six categories
- Date: 2026-11-17 | Status: accepted (all three as recommended) | Approved by: Malik | Implements DEC-033 item 1
- Context: Every message must be checked for danger before retrieval, in Hindi, Hinglish and English; the gate is crisis-trigger recall = 100%. Numbers come only from `data/contacts.yaml` (DEC-018; 112, 181, 1098, 1930, 14416, 15100 sourced 2026-11-17).
- Options: detection A) rules only · B) LLM classifier (paid, latency, non-deterministic) · **C) rules + BGE-M3 similarity to crisis examples**. Reply A) numbers then the normal answer · B) numbers only · **C) per category**. Categories: **six** · or life-safety only.
- Decision:
  1. **Detection = C.** Keyword/phrase rules per category and language (deterministic floor), plus cosine similarity of the query's BGE-M3 vector (already computed for retrieval) to example crisis messages; the threshold is tuned on the crisis test set for 100% recall, false-alarm rate reported. No LLM, no new dependency.
  2. **Reply = per category.** Self-harm: a short supportive line + Tele-MANAS 14416 and 112, no legal content. Violence, child at risk, cyber fraud in progress, forced eviction now: the emergency number(s) first, then the legal answer and free legal aid. The exact Hindi/English wording is approved by Malik before use (generation rules).
  3. **Categories (six):** violence/threat now → 112 · domestic violence/women → 181 + 112 · child at risk → 1098 + 112 · cyber fraud in progress → 1930 · self-harm → 14416 + 112 · forced eviction/lock-out now → 112 + NALSA 15100.
- Why: rules give a predictable floor, embeddings catch paraphrases, both free inside the existing image; legal text is inappropriate for someone at risk of self-harm, while a fraud victim needs both 1930 and the legal steps.
- Effects: ₹0 · ~1 ms rules + reuse of the query vector · a crisis test set (draft, Malik reviews) with recall = 100% as a test gate.

## DEC-075 — Tiered crisis reply: rule hits get the full crisis reply, embedding-only hits a safety line
- Date: 2026-11-17 | Status: accepted ("Tiered (Recommended)") | Approved by: Malik | Amends DEC-074 item 2
- Context: First eval (`reports/safety/crisis_2026-11-17.md`): rules catch 60/60 dev+test crisis rows with 0 false alarms but only **1/20** holdout rows (new wording); the embedding layer catches 19–20/20 holdout rows but also flags ~30–50% of ordinary legal questions (raw BGE-M3 similarities of short Indic messages overlap).
- Options: **A) tiered** · B) full crisis reply on any hit · C) rules only, grow them · D) LLM confirms embedding hits (paid).
- Decision: **A.**
  1. **Rule hit → full crisis reply** (DEC-074 item 2: numbers first; self-harm without legal content).
  2. **Embedding-only hit → the normal answer plus one short safety line at the end** with the category's number(s) (e.g. "If you are in danger, call 112"). Self-harm embedding-only hits also get only the safety line (Tele-MANAS 14416 + 112), not the full mode.
  3. The embedding layer scores **margin = similarity to the nearest crisis example − similarity to the nearest ordinary legal question** (a set of ordinary-question anchors), threshold tuned on the dev split for 100% recall.
  4. Embedding-only hits are logged without PII for review, to grow the rules (logging design with W3.1/DynamoDB).
- Why: keeps recall on unseen phrasings without derailing a third to a half of normal answers; a false safety line costs a sentence, a missed crisis costs much more.
- Effects: ₹0 · reply wording for both tiers needs Malik's approval before use · gate: 100% router recall on the test split; false-alarm rate reported per tier.

## DEC-076 — Redaction by placeholders (W2.0b); dispute detector by rules + embeddings (W2.0c)
- Date: 2026-11-18 | Status: accepted (both as recommended) | Approved by: Malik | Implements DEC-029 (PII), DEC-033 items 4 and 6, DEC-038
- Context: DEC-033.4 requires sensitive data (caste, disability, health, religion) volunteered by users to be used only in-session and redacted from all logs, traces and DynamoDB writes; DEC-029 requires PII redaction before any log. DEC-033.6/038: for land, family, SC/ST and criminal questions, answer the procedure and route "who is right" questions to DLSA.
- Options (redaction): **A) placeholders in place** · B) drop the whole message if anything is found · C) never store user text. Options (disputes): **A) rules + margin embeddings (as DEC-074/075)** · B) rules only · C) the generator decides.
- Decision:
  1. **Redaction = A.** Before anything is stored or logged, PII (phone, Aadhaar, PAN, e-mail, bank account, UPI id, card number) becomes `[PHONE]`, `[AADHAAR]`, …, and self-disclosed caste/tribe category, religion, disability and health conditions become `[CASTE]`, `[RELIGION]`, `[DISABILITY]`, `[HEALTH]`. Neutral topic words stay ("जाति प्रमाण पत्र" is a topic, not a disclosure). The bot never asks for these (generation rule, W2.1).
  2. **Dispute detector = A.** Phrase rules plus margin similarity to example "who is right / who owns" messages; a hit tells the generator to answer procedure only and adds the DLSA referral. Own test set with a holdout split, as for crisis.
- Why: placeholders keep logs useful for debugging while removing the identifying or sensitive part; the detector reuses a design whose limits were measured.
- Effects: ₹0 · known gap: specific caste and community names are not in the v1 lexicon (listed in OPEN_QUESTIONS) · DLSA referral wording needs Malik's approval (W2.1).

## DEC-077 — W2.1 start: Sarvam verified + one tiny test; OCR quotes with a scan label; RTI r.14 says both
- Date: 2026-11-18 | Status: accepted (all three as recommended) | Approved by: Malik | Implements DEC-006, DEC-071 item 4; answers S22
- Context: Generation needs a live model contract, a policy for quoting OCR text (Bodhan CER 2.5% on Hindi Act text, 13.6% overall, W0.5), and a rule for the RTI Rules r.14 difference between the official English (4 modes of service) and Hindi (3, no registered post).
- Options: LLM A) verify Sarvam docs + one tiny paid call, fixtures for tests · B) fully offline · C) Claude/Bedrock first (blocked on AWS). OCR quotes A) quote with a scan label · B) only spot-checked provisions · C) never quote OCR. RTI r.14 A) say both · B) follow English · C) follow each language silently.
- Decision: **A, A, A.**
  1. Sarvam's model id, endpoint, JSON/structured-output support and price are read from official docs and recorded (URL + date); **one** tiny paid call proves the contract (key from `.env`, never printed); all tests use recorded fixtures (`@pytest.mark.paid` only for live calls).
  2. OCR chunks are quoted like any other, with a label: "from a scanned copy — check page N of the official PDF" plus the source link; the validator still requires an exact match to the chunk text.
  3. For RTI Rules r.14 the answer uses the text in the user's language and adds one line that the English text also lists registered post and the Hindi text does not, citing both; no judgment on which prevails.
- Why: proves the real contract cheaply without making tests depend on paid calls; the OCR error rate on statute text is low and the label + page link let users verify; stating the difference is honest without giving a legal opinion.
- Effects: ~a few paise · the scan label and r.14 line join the user-facing wording file for Malik's approval.

## DEC-078 — Hard cap of ₹10 on all paid LLM calls before production
- Date: 2026-11-18 | Status: accepted | Approved by: Malik ("put cap of 10 credit for everything before production") | Resolves the pending "monthly budget for paid eval API calls"
- Decision: every paid model call before production (contract test, `scripts/ask.py`, evals, judge runs) goes through one spend guard with a **cumulative cap of ₹10 including 18% GST**. Before a call the guard adds the worst case (prompt tokens estimated from the text, plus `max_tokens` as output, at the verified Sarvam prices) to what was already spent; if that would exceed the cap, the call is refused. After the call the actual usage is appended to a committed ledger (`data/spend/llm_ledger.jsonl`: time, model, purpose, tokens, cost; never prompts, answers or keys). Raising the cap needs a new decision.
- Interpretation (Claude): "10 credit" = ₹10, since Sarvam prices and free credits are in rupees; GST is counted to stay conservative.
- Why: a hard, code-enforced ceiling, not a habit; the ledger shows exactly where the money went.
- Effects: at ~₹0.02–0.03 per question (~1.2K in / 0.6K out tokens) the cap allows a few hundred questions, enough for the contract test, local trials and roughly one or two golden-set runs.

## DEC-079 — User-facing wording, crisis replies and prompt v1 approved
- Date: 2026-11-18 | Status: accepted ("2 is approved") | Approved by: Malik | Approves the drafts under DEC-074/075/076/077 (OPEN_QUESTIONS S27a, S29b)
- Decision: approved as committed on 2026-11-18:
  1. `data/answer_texts.json` v2 (footer with LSA Act s.12 eligibility, per-source "official copy last checked" line, status caveats, OCR scan labels by source type, RTI r.14 note with both texts, wage qualification with notification number / authority / validity / review date, dispute referral, abstention messages), hi / hinglish / en;
  2. `data/safety/crisis_replies.json` (full tier per category + note tier), hi / hinglish / en;
  3. generator prompt **v1** (`generation/prompt.py`: E-label citations, JSON format in the prompt, procedure-only mode).
  Both JSON files carry `status: approved, approved_by: malik, approved_on: 2026-11-18`; the code refuses unapproved wording.
- Effects: the bot may now show these texts to users; any later wording or prompt change needs a new approval (generation rules). Still recommended: a fluent Hindi/Hinglish read-through before the public demo (not blocking).

## DEC-080 — Prompt v2 (claim-level blocks, short quotes, optional clarifying question); bot texts approved
- Date: 2026-11-19 | Status: accepted | Approved by: Malik ("1 … 2 approved") | Amends DEC-079 (prompt), output contract in generation rules
- Context: the 80-row eval (2026-11-18) failed 11 answerable rows because the model spliced or shortened long quotes, and the prompt had no way to ask about an ambiguous question.
- Decision:
  1. **Prompt v2** (`generation/prompt.py` `SYSTEM_V2`), written from Malik's instructions: (a) one independently checkable claim per answer block, whose citations together support every claim in it; (b) quotes of 5–20 consecutive words copied exactly, no "...", "***" or joined passages; (c) "no outside knowledge" stays: abstain when the excerpts are insufficient, but the model **may ask one brief clarifying question** when the question is ambiguous and the excerpts could answer it once clarified.
  2. **Output contract** gains an optional `clarify` string (no answer blocks, abstain false). Code limits it: at most 200 characters, must be a question, must pass the merits screen; otherwise it is treated as an unsupported answer (retry, then abstain). It carries no citations, so it must contain no legal claim.
  3. v2 is used for the eval; it becomes the production prompt only if the re-run improves on v1 (result recorded in PROGRESS); otherwise v1 stays.
  4. **`data/bot_texts.json` approved** (Telegram greeting, error and not-allowed texts).
- Effects: ~₹1 for the re-run (DEC-078 cap) · golden `ask_clarifying` rows now scored.

## DEC-081 — Golden set v1.0 frozen; faithfulness: stricter v1 prompt now, a free judge model next
- Date: 2026-11-19 | Status: accepted | Approved by: Malik ("golden set is reviewed and verified"; "yes c for now and any good free model after v1")
- Context: (1) Malik reviewed and verified the 130 seed rows. (2) The prompt v2 test showed the validator proves quotes exist but not that they support the claim (OPEN_QUESTIONS S33).
- Decision:
  1. **Golden v1.0** = the 130 verified seed rows, `data/golden/v1.0/golden_set_v1.0.jsonl` (sha256 `386f40b8…`), with only the corrections required by earlier decisions or verified findings (DEC-070 mutation rows out of corpus, DEC-050 wage row answerable with caveat, S31 GS-058 → CPA s.2(6)), listed in `data/golden/v1.0/CHANGES.md`. Protected from now on (eval rules); evals use v1.0. v1.0 keeps 130 rows (plan §7's 120 superseded by DEC-063's seed size).
  2. **Faithfulness (S33) = option (c) for now**: keep prompt v1 and accept more abstentions.
  3. **Next**: evaluate a **good free model** as a claim-support judge after v1 (e.g. a local multilingual NLI / cross-encoder model, or a free hosted model), with its accuracy measured on labelled examples before it gates anything; a paid judge (Claude, needs AWS) stays an option.
- Effects: ₹0 · golden v1.0 unlocks the DEC-066 int8/fp32 comparison (S32) and the W2.6 roadmap item.

## DEC-082 — Topic list: reply to "what can you help with?" and add it to the no-answer abstention
- Date: 2026-11-20 | Status: accepted | Approved by: Malik ("whenever user ask this type of question it will reply with topics … also … add this same helping areas list in our default reply")
- Context: "aap mujhe kis kis topic me help kar sakte hai" went through retrieval + LLM and gave no useful scope answer; an abstention told users nothing about what they *can* ask.
- Decision:
  1. `data/help_topics.json` (hi / hinglish / en): the 7 topic areas of the indexed corpus (RTI, consumer, labour and wages, tenancy, MP land demarcation, free legal aid and Lok Adalat, PM SVANidhi), scope only, no amounts, dates or sections. Each topic lists the instruments it relies on; unit tests require every listed instrument to be indexed or a guide, and every indexed instrument to appear in a topic, so the list cannot drift from the corpus.
  2. `generation/scope.py`: rule detection (a scope cue such as kis kis / kaun se / what can you, plus a help cue, and no named legal subject). Runs after the crisis router and before the jurisdiction guard; a hit returns the topic list with no retrieval and no LLM call (₹0).
  3. The "no reliable answer" abstention (nothing retrieved, or model/validator abstains) appends the topic list. The other-state abstention does not.
- Why: users learn what the bot covers, and an abstention becomes a pointer instead of a dead end.
- Effects: ₹0 · the topic file must be updated whenever the corpus scope changes (test enforces it) · `eval_answers.py` does not pass the list, so eval reports stay comparable.

## DEC-083 — Topic questions: no embedding-only safety line; topic wording confirmed
- Date: 2026-11-20 | Status: accepted ("yes for both") | Approved by: Malik | Amends DEC-075 item 2 for topic questions only
- Context: "aap mujhe kis kis topic me help kar sakte hai" got the note-tier safety line ("Agar aap ya koi aur khatre mein hai … 1098, 112, 1930") from an embedding-only crisis match, a false alarm.
- Decision:
  1. When a message is detected as a topic question (DEC-082), an **embedding-only** (note-tier) crisis match is dropped and logged (`crisis_note_suppressed`). A **rule** hit (full tier) still puts the crisis reply first.
  2. The wording in `data/help_topics.json` is confirmed as written.
- Why: topic questions are detected by rules that exclude any named legal subject, so a note-tier match there is noise; real crisis wording is caught by the rules (100% recall gate unchanged).
- Effects: ₹0 · small risk of missing a crisis phrased like a topic question with no crisis words.

---

## Pending decisions (not yet made)

| Topic | Raised in | Status |
| --- | --- | --- |
| DynamoDB table design + capacity mode (provisioned vs on-demand) + TTL | R10 | Malik: "will decide later". Must be decided before DEC-010/012 code |
| Monthly budget for paid eval API calls | R4 | Resolved 2026-11-18 by DEC-078 (₹10 cap incl. GST before production) |
| Second (higher) AWS alert that includes Bedrock | R4 | To discuss later |
