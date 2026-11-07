# Open questions — Madhya Kanoon Saathi

Everything not yet verified or decided. When resolved, set Status to `resolved`, add the answer + source URL + date,
and move a decision (if any) into DECISIONS.md. Owner: **M** = Malik, **C** = Claude.

## A. Legal content (from plan.md "Caveats") — needs an MP advocate or official source
| ID | Question | Why it matters | Owner | Status |
| --- | --- | --- | --- | --- |
| L1 | Which MP tenancy law governs: Accommodation Control Act 1961 vs Parisar Kirayedari Adhiniyam 2010? | Tenancy answers are wrong if the wrong Act is cited | M (advocate) | open |
| L2 | Most recent official list of states adopting the Model Tenancy Act (RS replies conflict) | "Model law" caveat wording | C | open |
| L3 | Is there a final MP gazette notification of rules under the four Labour Codes (drafts 5 Jan 2026)? Content of the reported Jul 2026 labour bill? | `status=draft` vs `in_force` | C | open |
| L4 | MP minimum-wage notification after 1 Oct 2026 | Time-versioned wage answers | C | resolved 2026-11-06: notification 1/11/अन्वे./पांच/2024/22288-337 dt 30.09.2026, valid 01.10.2026–31.03.2027, from the MP Labour DMS (`MP.MWVDAOCT2026` in the manifest; read from p.1 of the official scan). Scanned, so needs OCR (W0.5) |
| L7 | Post-commencement MP VDA notifications (Apr 2026 6445-6650, Oct 2026 22288-337) cite the repealed MW Act 1948. Are they valid under the Code on Wages (competent authority's continuing appointment, statutory power, procedure)? Malik's determination (DEC-042): Code governs; these stay in transitional legal review | Wage-amount answers | M (advocate) | open: gates `MP.MWVDAOCT2026`. DEC-045: no definitive current wage amounts until an advocate verifies post-repeal authority; historical data kept |
| L8 | Is the MP base-rate notification F.4(B)1/2014/A-16 (MP Extraordinary Gazette No. 68, 04.03.2024, effective 01.04.2024) saved under Code on Wages s.69(2) (not contrary to the Code)? Fetch it and verify | Base rates the VDA adds to | M (advocate) + C (fetch) | open: DEC-045 says fetch it (Claude) then advocate check |
| L9 | Find and verify *Garment and Textile Workers Union (R) v. Chief Secretary, Govt. of Karnataka*, Karnataka HC, 3 June 2026 (cited in Malik's determination). Searches on 2026-11-06 found only related writ appeals 1684–1685/2026 pending | Persuasive authority for DEC-042 | C | open |
| L5 | Status of SC challenges to DPDP s.44(3) / RTI s.8(1)(j) (no stay as of 3 Nov 2026 per plan) | Sub-judice caveat | C | open |
| L6 | Official sources for escalation contacts (NALSA 15100, Nyaya Setu 7217711814, e-Jagriti, RCA) | DEC-018 contacts.yaml | C | open |

### L7 in detail: MP wage notifications after the repeal of the Minimum Wages Act (open)

**The question.** MP's VDA wage notifications issued *after* 21.11.2025 still say they are made "under the Minimum
Wages Act, 1948". That Act was repealed on that date. Are they valid under the Code on Wages, and on what power?
- Oct 2026: no. 1/11/अन्वे./पांच/2024/22288-337 dt 30.09.2026 (+ Book 22283-337), valid 01.10.2026–31.03.2027
- Apr 2026: no. 6445-6650 dt 31.03.2026, valid 01.04.2026–30.09.2026 (expired)

**What is decided (DEC-042, Malik, 2026-11-06).**
- The Code on Wages, 2019 governs.
- Pre-21.11.2025 notifications may continue under s.69(2) if not contrary to the Code (see L8).
- Post-21.11.2025 notifications do **not** automatically get s.69(2) protection. A continuity argument exists via
  the saved CPI-linked structure and s.7(1)–(2).

**What is verified (Claude, 2026-11-06)**, from the official India Code PDF (`IN.COW2019@en@1`):
- s.69(1)–(3) text (p.30): repeal; savings "to the extent they are not contrary to the provisions of this Code";
  General Clauses Act s.6.
- Commencement by S.O. 5322(E) dt 21.11.2025 (p.5 footnote).
- s.7(1)–(2) cost-of-living allowance (pp.9–10).
- The Oct 2026 notification's number, date, issuing office and validity, read from p.1 of the official scan.
- **Not verified:** the Karnataka HC judgment of 3 June 2026 (L9). The Gazette PDF of S.O. 5322(E) is found but not
  yet read.

**What is still open (needs Malik or an advocate):**
1. Is the Labour Commissioner validly appointed or notified as the authority for the cost-of-living allowance under
   Code s.7(2)? (Or is the old appointment saved by s.69(2)?)
2. Which statutory power supports a post-repeal VDA revision: a saved pre-repeal structure, or a fresh exercise
   under ss.6–8 of the Code (which needs the s.8 procedure)?
3. Has MP notified its own Code on Wages rules or a fresh minimum-wage notification under the Code? (Ties to L3.)

**How it is implemented.**
- Manifest (`data/corpus_manifest.json`):
  - `MP.MWVDAOCT2026` docs `@hi@1`, `@hi@2`: `mode: gated`, `gate: ["L7"]`. The Code's index gate keeps them out of
    the search index.
  - `MP.MWVDAAPR2026@hi@1`: `mode: archive`, expired (`valid_to` 2026-09-30), so `is_current()` is false.
  - `IN.MWA1948`: instrument only, `superseded_by: ["IN.COW2019"]`, no document, never shown as operative.
  - `IN.COW2019@en@1`: `mode: index`, with confirmed status / commencement / text checks.
- No new status flag: "transitional legal review" = `gated` on L7 (DEC-042 mapping, Claude's choice).
- Bot effect: wage-**amount** answers abstain until L7 is closed, or until a caveat wording is approved in W2.1.
  The bot may still explain the Code's minimum-wage provisions (ss.5–9) from the indexed Code text.

**What closes L7.** An advocate's (or Malik's) written answer to points 1–3, recorded as a verification record
(`what: interpretation`, `by: malik|advocate`) on the notification, plus OCR of the scan (W0.5). Then the document
moves `gated → index`, or stays archived if found invalid.

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
| T3 | Do Indian government sites block non-Indian IPs (GitHub runners)? | DEC-013 | C | partly answered 2026-11-07: revenue.mp.gov.in is also unreachable for Malik in India, so that site is down, not IP-filtering. India Code 504s were intermittent. Other sites untested from abroad |
| T4 | Lambda behaviour after returning a response (freeze) — confirms DEC-010 option C was unreliable | DEC-010 | C | open |
| T5 | LGD (Local Government Directory) district codes: official source + format for `applies_to.districts` | DEC-040 | C | open |

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
| G4 | MP Karyasthal Sashaktikaran (Shram Shakti) Sanhita 2026 passed 21 Jul 2026; assent/notification | MP Vidhan Sabha; e-gazette | **MVP (labour)** | resolved in part (DEC-043/044): MP Act 7/2026, assent 07.08.2026, Gazette No. 257 dt 10.08.2026 (official listing match; PDF 404 so PRS copy used), registered `enacted_not_commenced`. **Open: s.1(3) commencement notification(s)**; monitor (DEC-045) |
| G5 | Registration (MP Amendment) Act 2025, assent 13 Oct 2026; commencement date | MP e-gazette | Dec (land; moved by DEC-037) | open |
| G6 | Lok Seva Guarantee: Act 24 of 2010 + amendments; notified service list and time limits (e.g., caste 30 working days; income 3 / domicile 7 per a secondary guide) | lokseva.gov.in/MPL; PRS | **MVP** | open (DEC-045): Act + Rules + amendments + 2025 services list fetched; 2013 gazette time-limit list (rcms.mp.gov.in) = historical official source. **Open: later s.3 notifications for certificate time limits**; unverified deadlines must carry source date + uncertainty |
| G7 | 181 in MP = women's helpline **and** CM Helpline? Official numbers for 112, 1098, 1930, 14416, 14447, 14555, 14567, 15100 | Official portals → contacts.yaml | **MVP** | open |
| G8 | MPLRC 2022 Ordinance + 2023 Second Amendment contents; mutation timelines (s.110: 1 vs 2 months); demarcation rules 2019 vs 2020 | revenue.mp.gov.in; e-gazette | **MVP** (land slice, DEC-038) | open, **deadline 16 Nov 2026** (DEC-045): no official text yet (revenue.mp.gov.in down; India Code 504; bor.mp.gov.in lists the Code but links are dead). If unresolved by 16 Nov, land leaves the Nov demo → Dec |
| G9 | CM Kisan Kalyan amount (₹6,000 vs ₹4,000); Bhavantar Kharif 2026 dates; stubble-burning disqualification order | Agriculture dept orders | Dec | open |
| G10 | PM-KISAN instalment dates; RTE MP 2026-27 dates | pmkisan.gov.in; rteportal.mp.gov.in | Dec / Q1 | open |
| G11 | SC/ST PoA relief schedule (₹85,000–₹8.25 lakh) and task-force proposal status | PoA Rules Annexure I; MoSJE | Q2 2027 | open |

## H. Added by the Phase 0 review (DEC-037)
| ID | Question | Verify at | Phase | Status |
| --- | --- | --- | --- | --- |
| G12 | Exact name, date and content of MP's RTI fee rules for state public authorities (fees, payment mode, BPL exemption) | MP GAD; MP e-gazette | **MVP** | partly resolved: Rules 2005 found (`MP.RTIFAR2005`). **Open: amendment check (reported fee-hike proposal) + OCR fix**, then index (DEC-045); implement state-vs-central routing |
| G13 | MP SLSA rules / notification setting the income limit for free legal aid under LSA Act s.12(h) | MP SLSA site; e-gazette | **MVP** | partly resolved (DEC-045): rules gated; ₹2 lakh usable only as qualified official guidance with DLSA referral. **Open: the amending notification number/date (Malik to ask MPSLSA/DLSA)**; confirm r.20 'clause (b)' = today's s.12(h) |
| G14 | Is the MP Shops and Establishments Act still in force, or changed/replaced by the 2026 Sanhita (G4)? | MP Labour; e-gazette | **MVP** (decide include) | resolved for v1 (DEC-045): the S&E Act 1958 + 2025 amendments stay the applicable framework until the Sanhita commences (s.40(1)(b) repeal). Open: fetch those texts; check MP Acts 260/264 for changes |

L4 is resolved (current notification found, see group A). Wage-amount answers are now gated on **L7** (validity of
post-repeal notifications, DEC-042) and on OCR of the scan (W0.5).

## I. Added by the W0.4 review (DEC-045, 2026-11-07)
| ID | Question / task | Owner | Status |
| --- | --- | --- | --- |
| G15 | **MP Repeal (निरसन) Act 2026** (Gazette No. 260, 11.08.2026): which corpus instruments does it repeal, from when, with what savings? Priority before G16 | C | resolved 2026-11-07: MP Act 8 of 2026 (assent 07.08.2026, Gazette No. 260 dt 11.08.2026; PRS copy, official PDF 404) repeals 7 CP&Berar-era Acts in whole (debt relief 1933/1937/1939, Famine Relief Fund 1937, Vidya Mandir 1940, Regulation of Couching 1944, Land Survey 1947); s.3 savings. **No corpus instrument affected.** Instrument `MP.NIRSAN2026` recorded. TODO(verify): commencement rule (no commencement clause) |
| G16 | **MP Ease of Doing Business Act 2026** (Gazette No. 264, 20.08.2026): does it amend corpus laws (S&E Act 1958, Sanhita, others)? | C | resolved 2026-11-07: MP Act 9 of 2026 (assent 17.08.2026, Gazette No. 264 dt 20.08.2026; PRS copy). Not yet commenced (s.1(3)); extends only to notified industrial areas (s.1(2)). **No textual amendment of corpus laws.** After commencement: S&E registration via the State Nodal Agency (Sch. IV item 41), Lok Seva Act penalties for missed clearance limits (s.20), override by harmonious construction (s.21). Instrument `MP.EODB2026` recorded; **watch for its commencement + industrial-area notifications** (law-watch) |
| X1 | Effective-date ("as of") legal retrieval design | C (plan) → M | open: plan needed before code |
| X2 | Separate legal-authority vs source-quality metadata (official file / listing-matched copy / defective scan) | C (plan) → M | open: schema change, plan needed |
| X3 | Legal-impact analysis for every amendment and repeal (affected instruments, provisions, dates) | C (plan) → M | open |
| X4 | Re-run affected golden-set rows after every legal change (law-watch flow, DEC-013) | C (plan) → M | open |
| U1 | `section_uid` support for roman-numbered clauses alongside letters, validated against the hierarchy (DEC-045 item 7) | C | resolved 2026-11-07: new segments `clr_<roman>` (clause) and `scla_<letters>` (sub-clause); canonical roman 1–3999; spec `docs/specs/section_uid.md`; 23 new tests. First use: `MP.LSGR2010:r8:clr_vii` for the 2026 amendment. **TODO(verify):** the mapping of Hindi clause '(सात)' → (vii) is structural; confirm against the 2010 Rules text once fetched |

## F. Environment
| ID | Question | Owner | Status |
| --- | --- | --- | --- |
| E1 | Local Python is 3.12.0. Switch to latest 3.12.x? | M | resolved 2026-11-06: keep the local 3.12 install. The Lambda base image brings its own 3.12.x patch. |
| E2 | Terraform not installed — install via winget before W0.6 (needs OK) | M | open |
