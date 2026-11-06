# Progress — Madhya Kanoon Saathi

Roadmap from `docs/plan.md` §10, adjusted by `docs/DECISIONS.md` (DEC-016: no Marathi/Maharashtra; DEC-020/023: v2 items).
Status: `todo` · `in progress` · `done` · `blocked`. One item in progress at a time.

## Setup (kickoff)
| # | Item | Status | Notes |
| --- | --- | --- | --- |
| S1 | Read plan, list ambiguities/risks | done | Answers → DEC-008…029 |
| S2 | Repo structure + Python tooling | done | DEC-030; ruff/mypy/pytest green |
| S3 | Control files (PROGRESS, OPEN_QUESTIONS, ARCHITECTURE, .gitignore, .env.example, README, pre-commit, rules) | done | pre-commit installed; hooks run after `git init` (S6) |
| S4 | `.claude/settings.json` permissions + hooks | done | DEC-034/035. Hooks tested: protect (DECISIONS/CORPUS → ask), Stop checks pass, compact summary works. Note: auto mode blocks Claude editing `.claude/hooks/*`, so switch modes when hook changes are needed |
| S5 | Skills: /start-session, /end-session, /decision | done | `.claude/skills/*/SKILL.md`; format checked against official docs; injected commands tested |
| S6 | `git init` + first commit; GitHub repo + push after OK | done | Public repo https://github.com/ajinendra05/Madhya-Kanoon-Saathi (DEC-036); `AGENTS.md` stays untracked |

## W0 — 5–9 Nov: validation + corpus
| # | Item | Status | Definition of done |
| --- | --- | --- | --- |
| W0.1 | Validation posts in 3 groups (Malik) | todo | ≥15 real questions logged (redacted) |
| W0.2 | AWS account: Paid plan, root MFA, ₹100 alert (Malik, DEC-019) | todo | Alert visible in Budgets |
| W0.3 | `section_uid` scheme | todo | Spec + parser tests |
| W0.4 | Corpus download (CORPUS.md Phase 0 per DEC-037: index/gated/archive/guide modes) + `corpus_manifest.json` | todo | All files with sha256 + status + mode; start with the current MP wage notification (L4) and G4/G6/G12/G13/G14 checks |
| W0.5 | OCR bake-off: Bodhan vs Tesseract vs Sarvam, 20 pages (DEC-014/015) | todo | CER table per tool |
| W0.6 | Terraform skeleton (DEC-028: stays in W0) | todo | `terraform plan` shows no resources yet / backend chosen |

## W1 — 10–16 Nov: parsing + retrieval
| # | Item | Status | Definition of done |
| --- | --- | --- | --- |
| W1.1 | Parser + clause-aware chunker (EN + HI) | todo | Chunk tests; chunk viewer works |
| W1.2 | Bulk OCR on Colab | todo | OCR'd pages in manifest |
| W1.3 | Custom tokeniser (DEC-026) + bm25s index | todo | Tokeniser unit tests |
| W1.4 | BGE-M3 int8 + fp32 embeddings, FAISS exact (DEC-021/022/025) | todo | Parity test passes |
| W1.5 | RRF + reranker | todo | |
| W1.6 | Embedding bake-off vs e5-large (DEC-004) | todo | recall@10 per language |
| W1.7 | Deterministic retrieval eval on first 50 golden rows | todo | Recall@10, MRR reported |

## W2 — 17–23 Nov: generation + eval + bot
| # | Item | Status | Definition of done |
| --- | --- | --- | --- |
| W2.0 | Crisis router before retrieval (DEC-033.1) | todo | Crisis-trigger recall = 100% on test rows |
| W2.0b | Sensitive-data redaction: caste/disability/health/religion (DEC-033.4) | todo | Redaction unit tests |
| W2.0c | Dispute detector + land jurisdiction guard (DEC-038, moved from Dec) | todo | Merits/ownership land questions route to DLSA; no non-MP land code cited |
| W2.1 | JSON-claims generation + citation validator + abstention (incl. `expires_on` auto-abstain) | todo | Validator tests |
| W2.2 | Sarvam vs Claude A/B (model IDs verified, DEC-006) | todo | A/B table |
| W2.3 | Eval harness (Ragas/DeepEval + own scorers), judge cache (DEC-023) | todo | Gates computed per slice |
| W2.4 | Judge calibration (40 hand-graded, κ) | todo | κ reported |
| W2.5 | Telegram bot (local) | todo | |
| W2.6 | Golden set 120 rows frozen v1.0 | todo | Frozen + versioned |
| W2.7 | CI job green | todo | |

## W3 — 24 Nov–~5 Dec: deploy + publish (demo target moved from 30 Nov to ~3–5 Dec, DEC-038)
| # | Item | Status | Definition of done |
| --- | --- | --- | --- |
| W3.1 | AWS deploy: Lambdas, Function URL, SQS+DLQ, DynamoDB, EventBridge, SSM, ECR (DEC-010/024) | todo | Bot answers live |
| W3.2 | cost_log + nightly summary + Pages dashboard (DEC-012) | todo | Dashboard URL |
| W3.3 | Law-watch Lambda → GitHub issue (DEC-013) | todo | |
| W3.4 | README, ARCHITECTURE, eval report, 3-min demo video | todo | |
| W3.5 | 2 mock system-design interviews | todo | Interview-ready |

## Corpus expansion (DEC-032, details in CORPUS.md)
| Phase | Areas | Status |
| --- | --- | --- |
| Nov 2026 (MVP) | Land-procedure slice: MPLRC ss.109–110, s.129, Mutation Rules 2018, demarcation rules, Bhulekh guide (DEC-038). Demo ~3–5 Dec | todo |
| Dec 2026 | Rest of land + farmer schemes | todo |
| Q1 2027 | Students (before March RTE cycle), cyber/FIR, banking/insurance, women's safety, senior citizens | todo |
| Q2 2027 | Panchayat/PESA/VB-G RAM G, SC/ST + forest rights, disability | todo |
| H2 2027+ | Family/UCC, RERA, motor accidents, electricity, ration, Ayushman, birth/death | todo |

## Later (after November)
- Keep-warm ping (DEC-020 v2) · judge option B in CI (DEC-023 v2) · WhatsApp Cloud API · voice · NGO console
- DPDP full compliance before 13 May 2027 (per plan §10)

## Session log
<!-- Newest first. Format: ### YYYY-MM-DD — done · decisions · problems · next step -->
### 2026-11-06 (afternoon)
- Done: S3–S5 finished; corpus roadmap (CORPUS.md, DEC-032); safety/schema changes (DEC-033); permissions + hooks
  (DEC-034, narrowed by DEC-035); skills /start-session, /end-session, /decision; `git init -b main`; `.gitattributes`
  (LF everywhere); pre-commit installed. Checks: ruff ✓, format ✓, pytest 1 passed, `pre-commit run --all-files` all 11 hooks passed (incl. gitleaks).
- Decisions: DEC-032, 033, 034, 035.
- Problems: auto mode blocks Claude from editing `.claude/hooks/*` (fixed in manual mode). Found an untracked
  `AGENTS.md` (a Codex copy of CLAUDE.md) not created by Claude, left out of the commit.
- Next: S6 GitHub repo + push (after OK), then W0.

### 2026-11-06
- Done: DEC-030 + DEC-031 recorded; `docs/plan.doc` deleted; uv project (Python 3.12) with ruff, mypy, pytest; package skeleton; smoke test. Checks: ruff ✓, format ✓, mypy ✓, pytest 1 passed.
- Decisions: DEC-030, DEC-031.
- Problems: none. Local Python is 3.12.0 (old patch) — see OPEN_QUESTIONS.
- Next: finish S3 after Malik reviews drafts.

### 2026-11-05
- Done: plan review; decision doc; DECISIONS.md (DEC-001…029), CONCEPTS.md, TOOLS.md, CLAUDE.md; plan.md banner.
- Next: S2.
