# Open questions — Madhya Kanoon Saathi

Everything not yet verified or decided. When resolved, set Status to `resolved`, add the answer + source URL + date,
and move a decision (if any) into DECISIONS.md. Owner: **M** = Malik, **C** = Claude.

## A. Legal content (from plan.md "Caveats") — needs an MP advocate or official source
| ID | Question | Why it matters | Owner | Status |
| --- | --- | --- | --- | --- |
| L1 | Which MP tenancy law governs: Accommodation Control Act 1961 vs Parisar Kirayedari Adhiniyam 2010? | Tenancy answers are wrong if the wrong Act is cited | M (advocate) | open |
| L2 | Most recent official list of states adopting the Model Tenancy Act (RS replies conflict) | "Model law" caveat wording | C | open |
| L3 | Is there a final MP gazette notification of rules under the four Labour Codes (drafts 5 Jan 2026)? Content of the reported Jul 2026 labour bill? | `status=draft` vs `in_force` | C | open |
| L4 | MP minimum-wage notification after 1 Oct 2026 | Time-versioned wage answers | C | open |
| L5 | Status of SC challenges to DPDP s.44(3) / RTI s.8(1)(j) (no stay as of 3 Nov 2026 per plan) | Sub-judice caveat | C | open |
| L6 | Official sources for escalation contacts (NALSA 15100, Nyaya Setu 7217711814, e-Jagriti, RCA) | DEC-018 contacts.yaml | C | open |

## B. Prices, limits and availability (TODO(verify))
| ID | Question | Used in | Owner | Status |
| --- | --- | --- | --- | --- |
| P1 | AWS Free vs Paid plan rules (auto-close after 6 months / credits) | DEC-002, 019 | C | open |
| P2 | Always-free limits: Lambda (1M req, 400K GB-s), SQS (1M), DynamoDB (25 GB, 25 RCU/WCU — provisioned only?) | DEC-002, R10 | C | open |
| P3 | Lambda max memory / vCPU scaling / image size limit; Python 3.12 base image | DEC-021, 024, 030 | C | open |
| P4 | Claude models on Bedrock India `in.` profile: IDs, prices (Mumbai uplift?), whether AWS credits cover them | DEC-006 | C | open |
| P5 | Sarvam-105B price + rate limit; Sarvam Document Digitization price | DEC-006, 014 | C | open |
| P6 | SSM standard tier free; Secrets Manager price | DEC-009 | C | open |
| P7 | S3, ECR, CloudWatch, KMS (customer-managed key) prices in ap-south-1 | DEC-011, 024, 029 | C | open |
| P8 | NAT gateway cost (justification for no VPC) | DEC-029 | C | open |
| P9 | GitHub Actions minutes for private repos | DEC-024 | C | open |

## C. Models and libraries
| ID | Question | Used in | Owner | Status |
| --- | --- | --- | --- | --- |
| M1 | Bodhan IndicOCR: Hugging Face model ID, licence, revision hash, CPU feasibility | DEC-001, 015 | C | open |
| M2 | BGE-M3 and bge-reranker-v2-m3: parameter counts, licences, ONNX int8 export route | DEC-004, 005, 021 | C | open |
| M3 | faiss-cpu and onnxruntime wheels for Python 3.12 on Windows + Linux (Lambda) | DEC-030 | C | open |
| M4 | bm25s: custom tokeniser hook API | DEC-026 | C | open |
| M5 | gitleaks pre-commit hook: does pre-commit bootstrap Go on Windows, or use the docker hook? | DEC-030 | C | resolved 2026-11-06: the `gitleaks` (golang) hook installed and passed via `pre-commit run --all-files`; no Docker fallback needed |

## D. Platform behaviour
| ID | Question | Used in | Owner | Status |
| --- | --- | --- | --- | --- |
| T1 | Telegram webhook timeout / retry behaviour; `secret_token` header name | DEC-010 | C | open |
| T2 | Telegram bot username availability (must end in "bot") | DEC-017 | M | open |
| T3 | Do Indian government sites block non-Indian IPs (GitHub runners)? | DEC-013 | C | open |
| T4 | Lambda behaviour after returning a response (freeze) — confirms DEC-010 option C was unreliable | DEC-010 | C | open |

## E. Pending decisions (to discuss later — Malik)
| ID | Topic | Status |
| --- | --- | --- |
| D1 | DynamoDB table design, capacity mode, TTL (R10) | deferred |
| D2 | Monthly budget for paid eval calls (R4) | deferred |
| D3 | Second, higher AWS alert including Bedrock (R4) | deferred |

## G. Claims from the domain-expansion report (DEC-032) — verify against official text before ingestion
| ID | Claim | Verify at | Phase | Status |
| --- | --- | --- | --- | --- |
| G1 | MGNREGA repealed; VB-G RAM G Act 2025 (assent 21 Dec 2025) in force 1 Jul 2026, 125 days | India Code / e-gazette / PRS | Q2 2027 | open |
| G2 | MP HC struck down 27% OBC quota on 9 Oct 2026; SLP Diary No. 65767/2026 | MP HC judgment; SC case status | Q1 2027 | open |
| G3 | MP UCC 2026 passed 21 Jul 2026, awaiting Presidential assent | Rashtrapati Bhavan assent list; MP e-gazette | later | open |
| G4 | MP Karyasthal Sashaktikaran (Shram Shakti) Sanhita 2026 passed 21 Jul 2026; assent/notification | MP Vidhan Sabha; e-gazette | **MVP (labour)** | open |
| G5 | Registration (MP Amendment) Act 2025, assent 13 Oct 2026; commencement date | MP e-gazette | **MVP (tenancy)** | open |
| G6 | Lok Seva Guarantee: Act 24 of 2010 + amendments; notified service list and time limits (e.g., caste 30 working days; income 3 / domicile 7 per a secondary guide) | lokseva.gov.in/MPL; PRS | **MVP** | open |
| G7 | 181 in MP = women's helpline **and** CM Helpline? Official numbers for 112, 1098, 1930, 14416, 14447, 14555, 14567, 15100 | Official portals → contacts.yaml | **MVP** | open |
| G8 | MPLRC 2022 Ordinance + 2023 Second Amendment contents; mutation timelines (s.110: 1 vs 2 months); demarcation rules 2019 vs 2020 | revenue.mp.gov.in; e-gazette | Dec | open |
| G9 | CM Kisan Kalyan amount (₹6,000 vs ₹4,000); Bhavantar Kharif 2026 dates; stubble-burning disqualification order | Agriculture dept orders | Dec | open |
| G10 | PM-KISAN instalment dates; RTE MP 2026-27 dates | pmkisan.gov.in; rteportal.mp.gov.in | Dec / Q1 | open |
| G11 | SC/ST PoA relief schedule (₹85,000–₹8.25 lakh) and task-force proposal status | PoA Rules Annexure I; MoSJE | Q2 2027 | open |

## F. Environment
| ID | Question | Owner | Status |
| --- | --- | --- | --- |
| E1 | Local Python is 3.12.0. Switch to latest 3.12.x? | M | resolved 2026-11-06: keep the local 3.12 install. The Lambda base image brings its own 3.12.x patch. |
| E2 | Terraform not installed — install via winget before W0.6 (needs OK) | M | open |
