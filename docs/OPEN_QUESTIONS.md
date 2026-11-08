# Open questions — Madhya Kanoon Saathi

Everything not yet verified or decided. When resolved, set Status to `resolved`, add the answer + source URL + date,
and move a decision (if any) into DECISIONS.md. Owner: **M** = Malik, **C** = Claude.

## A. Legal content (from plan.md "Caveats") — needs an MP advocate or official source
| ID | Question | Why it matters | Owner | Status |
| --- | --- | --- | --- | --- |
| L1 | Which MP tenancy law governs: Accommodation Control Act 1961 vs Parisar Kirayedari Adhiniyam 2010? | Tenancy answers are wrong if the wrong Act is cited | M (advocate) | open |
| L2 | Most recent official list of states adopting the Model Tenancy Act (RS replies conflict) | "Model law" caveat wording | C | open |
| L3 | Is there a final MP gazette notification of rules under the four Labour Codes (drafts 5 Jan 2026)? Content of the reported Jul 2026 labour bill? | `status=draft` vs `in_force` | C | open (updated 2026-11-07): MP published a **revised draft** 'MP Code on Wages Rules, 2026' (No. 83/2026/A-16, MP Rajpatra 30.04.2026; `MP.WCR2026`, read from code.mp.gov.in); first draft 05.01.2026. **No final notification found.** Labour bill content (Jul 2026) superseded by the Sanhita findings (G4) |
| L4 | MP minimum-wage notification after 1 Oct 2026 | Time-versioned wage answers | C | resolved 2026-11-06: notification 1/11/अन्वे./पांच/2024/22288-337 dt 30.09.2026, valid 01.10.2026–31.03.2027, from the MP Labour DMS (`MP.MWVDAOCT2026` in the manifest; read from p.1 of the official scan). Scanned, so needs OCR (W0.5) |
| L7 | Post-commencement MP VDA notifications (Apr 2026 6445-6650, Oct 2026 22288-337) cite the repealed MW Act 1948. Are they valid under the Code on Wages (competent authority's continuing appointment, statutory power, procedure)? Malik's determination (DEC-042): Code governs; these stay in transitional legal review | Wage-amount answers | M (advocate) | open for a human advocate; **no longer blocks wage answers** (DEC-050, 2026-11-08: official schedule-specific rates with a legal qualification). Oct 2026 notification indexed |
| L8 | Is the MP base-rate notification F.4(B)1/2014/A-16 (MP Extraordinary Gazette No. 68, 04.03.2024, effective 01.04.2024) saved under Code on Wages s.69(2) (not contrary to the Code)? Fetch it and verify | Base rates the VDA adds to | M (advocate) + C (fetch) | partly resolved 2026-11-07: fetched from MP Labour DMS (`MP.MWBASE2024`): Rajpatra No. 68 dt 04.03.2024, rates from 01.04.2024. **Litigated**: stayed (21.05.2024; 2016 base applied), HC Indore disposed of WP 10772/2024 etc. on 10.02.2025; circular 6891 (28.02.2025) reinstated the 2024 rates for all employments **except textiles/made-ups, apparel, footwear** (pre-revision rates + VDA pending fresh revision). **Open for advocate:** saved status under Code s.69(2) (pre-commencement notification), and whether the fresh revision for the 3 employments was ever completed **2026-11-08:** Pithampur (20.03.2025) dismissal of the connected petitions found (Indian Kanoon); AI note's view: strongly likely saved (not an advocate opinion) |
| L9 | Find and verify *Garment and Textile Workers Union (R) v. Chief Secretary, Govt. of Karnataka*, Karnataka HC, 3 June 2026 (cited in Malik's determination). Searches on 2026-11-06 found only related writ appeals 1684–1685/2026 pending | Persuasive authority for DEC-042 | C | open |
| L5 | Status of SC challenges to DPDP s.44(3) / RTI s.8(1)(j) (no stay as of 3 Nov 2026 per plan) | Sub-judice caveat | C | open |
| L6 | Official sources for escalation contacts (NALSA 15100, Nyaya Setu 7217711814, e-Jagriti, RCA) | DEC-018 contacts.yaml | C | open |

### G8 in detail: Demarcation Rules 2018 and the deep-research check (2026-11-07, kept GATED)

**Decision (Malik, 2026-11-07):** record these findings here for now; the Demarcation Rules stay **gated** (DEC-046).
The research's "Level 2: qualified indexing" proposal is **not adopted** (it would be a second aggregator exception after DEC-043).

**Reproduced text checked by Claude:** Indian Kanoon, https://indiankanoon.org/doc/12233550/
- Copy saved at `data/raw/MP.LRCDR2018/MP.LRCDR2018_en_indiankanoon.html` (git-ignored), sha256 `820eee66c9c7199724cd382c90e5fa941c0ad0d8f29ff89a0818b4924cd82601`.
- The page itself says: *"The original publication document is not available and this content could not be verified."*

**Matches between the deep research and the reproduction:**
- Notification F-2-13-2018-7-Se.7, Bhopal, **28.01.2019**.
- Made under s.258(2)(xxx) + s.129; supersedes notification 187-6477-VII-N-(Rules) dt 06.01.1960.
- r.1(2): in force from **publication in the MP Gazette**.
- r.3 Form I (application); r.5 Form II (Tahsildar report, s.129(2)); r.6 Form III (SDO report, s.129(7)).
- **r.4 fees:**
  - (1) fixed by the Collector with the Commissioner Land Records' approval
  - (2) may differ by district (agency charges)
  - (3) **an applicant who builds the marks pays only the demarcation fee** (missing from the research)
  - (4) **until the Collector fixes a fee, the fee in force before these rules applies** (missing from the research)
- r.7 agencies:
  - (1) authorised by the Collector under the Commissioner's control
  - (2) engaged by the Tahsildar (s.129(3))
  - (3) engaged by the SDO (s.129(6))
- r.8 SDO team (s.129(6)):
  - Team Leader: Superintendent / Assistant Superintendent of Land Records, a Revenue Inspector or a Nagar Sarvekshak
  - Member: another Revenue Inspector or Nagar Sarvekshak
  - optional experts
- r.9 + Schedule I: property pins (Types 1–3, sizes) and pin caps.
- r.10: technical instructions by the Commissioner Land Records (s.129(9)).
- r.11: damage to marks is penalised under s.130.

**Corrections to the research:**
1. **The 45-day limit is exact, not "normally":** it runs from the date of the Tahsildar's confirmation **or the date of knowledge, whichever is later** (official Act 23/2018 text).
2. The s.129 text is **already verified layer by layer**: the 2018 substitution (official MP Code) plus the 2023 "or Patwari" amendment (official Assembly copy). No official consolidation exists.
3. Rules 3–11 have **no headings** in the source; the research's rule titles are descriptive labels, not quotations.

**Bot rules carried forward (DEC-046):**
- Keep **s.129(5)** separate from **s.129(8)**:
  - s.129(5): an SDO application on the stated grounds (no notice / no hearing / other sufficient ground)
  - s.129(8): no appeal or revision
- **No universal fee.**
- The procedure under the rules may be described only as "per the Demarcation Rules 2018 (official gazette copy not yet verified)", always alongside s.129.

**Not verifiable today:** the India Code record of commencement notification **No. 24-2018-VII-Sec-6 dt 16.08.2018** (appointing 25.09.2018). India Code returned HTTP 504 on every try. Keep the distinction: **16.08.2018 = notification date; 25.09.2018 = commencement date.**

**G8g hypothesis (unverified):** 28.01.2019 = notification date; **01.02.2019 = gazette publication date**. Because r.1(2) makes publication the commencement event, 01.02.2019 would then be the commencement date. Needs the gazette issue.

**Not adopted from the research's proposals:**
- Manifest fields `act_id` / `parent_act` / `legal_status` / `retrieval_mode`: equivalents already exist (`instrument_id`, `parent_instrument`, `status`, `mode`).
- `source_quality`: = X2, needs a plan + decision.
- ID `MP.LRCSEEM2018`: we keep `MP.LRCDR2018`.
- "Index mutation now": blocked until W1.1 can overlay the 2018 substituted sections on the 2014 consolidation, and until the Mutation Rules' gazette publication date is known (G8h).

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
   - 2026-11-07: only **draft** rules exist (revised draft 30.04.2026, `MP.WCR2026`). Draft r.5 sets the April/October cost-of-living
     revision cycle on CPI-IW under s.7(2), consistent with the VDA notifications, but neither the draft nor anything found
     appoints the s.7(2) computing authority. A draft is not law, so it can't by itself validate the Oct 2026 notification.

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

**Update 2026-11-07 (DEC-047):**
- **MP draft rules:**
  - The **30.04.2026 revised draft** (No. 83/2026/A-16; `MP.WCR2026@en@1`) is the latest draft; the **05.01.2026 draft** is archived as history.
  - Both are drafts (not in force). Objection / action-taken reports dated 24–25.06.2026 show no final rules as of then.
- **Proposed r.5** (both drafts): cost-of-living allowance computed once before 1 April and 1 October on CPI-IW. This **supports** the existing twice-yearly VDA cycle, but a draft is not law.
- **Proposed r.4**: an **advisory Technical Committee** chaired by the Labour Commissioner. It is **not** the s.7(2) computation authority.
- **S.O. 2451(E), 12.05.2026** (verified, `IN.SO2451E2026`):
  - appoints the **DG, Labour Bureau** under s.7(2), whole of India, only for establishments where the **Central Government** is the appropriate Government
  - supersedes S.O. 186(E)–192(E) of 19.01.2017
  - does **not** resolve the MP state-sphere authority question
- **L7 stays gated until verified:**
  - (a) the **MP s.7(2) appointment notification**
  - (b) the **2024 base-rate notification** (L8)
  - (c) the **legal basis of the September 2026 VDA revision**

**Update 2026-11-08: AI research note received** (`docs/briefs/research_note_L7_L8_2026-11-07.md`)
- **Not an advocate opinion** (the note says so), so the gate is unchanged.
- **New leads:**
  - (a) **Pithampur Audyogik Sangthan v. State of MP, 20.03.2025, 2025:MPHC-IND:7084**: WP 9401/11921/12606 of 2024 dismissed (verified via Indian Kanoon; official copy to fetch).
  - (b) a reported **1982 delegation** (No. 3761-613-16-A-82 dt 25.05.1982) of MW Act s.4(2) competent-authority powers to the Labour Commissioner, which would bear on point 1 (s.7(2) authority via s.69(2)). **Unverified.** Our official Oct 2026 notification pp.1–4 do **not** cite it, contrary to the note.
- **Correction:** the Oct 2026 notification has a separate schedule for the 3 new employments (unskilled ₹10,950), verified on official p.4. So SGCMS's ₹10,950 was right for that schedule.

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
| G8 | MPLRC 2022 Ordinance + 2023 Second Amendment contents; mutation timelines (s.110: 1 vs 2 months); demarcation rules 2019 vs 2020 | revenue.mp.gov.in; e-gazette | **MVP** (land slice, DEC-038) | statute + mutation + demarcation rules now backed by **official gazette copies** (2026-11-07, session 3); demarcation module still NOT production-ready (DEC-046; deadline 16 Nov). **Resolved:** **G8b** Demarcation Rules official gazette (MP Rajpatra Part 4(ग) 01.02.2019, notification एफ 2-13-2018-सात-शा.7 dt 28.01.2019) from the Revenue Dept's own PDF via an Internet Archive snapshot; **G8g** in force **01.02.2019** (publication; notification signed 28.01.2019); **G8h** Mutation Rules in force **04.01.2019** (MP Rajpatra No. 1, 04.01.2019). Also found: the department's consolidated MPLRC 'as amended up to 12.02.2020' (`MP.LRC1959@hi@2`). **Still open:** **G8a** the commencement notification No. 24-2018-VII-Sec-6 itself (date 25.09.2018 already confirmed by recital; retried 2026-11-07: India Code 504, Internet Archive offline, MP Code none); ~~G8c~~ Forms I–III **located** in `MP.LRCDR2018@bi@1` (Hindi PDF pp.8–16, English pp.23–28; Form I fields + enclosures recorded; its caste column is sensitive per DEC-033.4); **G8d** district Collector fee orders; **G8e** agency authorisation orders; **G8f** r.10 technical instructions. (2026-11-07: archived Revenue Dept circulars, `circular-loop.php` snapshot 20220706, contain no fee, agency or technical orders; these are **district-level** (r.4, r.7: Collector) or Commissioner Land Records issuances, likely on ~55 district sites. **Parked post-MVP (Malik, 2026-11-07)**; the bot says 'fee fixed by the Collector, varies by district; ask your Tahsil' (DEC-049); not demo-blocking.) **Decided (DEC-049, 2026-11-07):** Internet Archive copies of official files count; Demarcation Rules **indexed**, fee amounts still gated (G8d). Note: the PDF Malik found for G8a (No. 24/2018-Central Tax (Rate), Ministry of Finance, GST) is unrelated, not recorded |
| G9 | CM Kisan Kalyan amount (₹6,000 vs ₹4,000); Bhavantar Kharif 2026 dates; stubble-burning disqualification order | Agriculture dept orders | Dec | open |
| G10 | PM-KISAN instalment dates; RTE MP 2026-27 dates | pmkisan.gov.in; rteportal.mp.gov.in | Dec / Q1 | open |
| G11 | SC/ST PoA relief schedule (₹85,000–₹8.25 lakh) and task-force proposal status | PoA Rules Annexure I; MoSJE | Q2 2027 | open |

## H. Added by the Phase 0 review (DEC-037)
| ID | Question | Verify at | Phase | Status |
| --- | --- | --- | --- | --- |
| G12 | Exact name, date and content of MP's RTI fee rules for state public authorities (fees, payment mode, BPL exemption) | MP GAD; MP e-gazette | **MVP** | partly resolved: Rules 2005 found (`MP.RTIFAR2005`). **Open: amendment check (reported fee-hike proposal) + OCR fix**, then index (DEC-045); implement state-vs-central routing |
| G13 | MP SLSA rules / notification setting the income limit for free legal aid under LSA Act s.12(h) | MP SLSA site; e-gazette | **MVP** | partly resolved (DEC-045): rules gated; ₹2 lakh usable only as qualified official guidance with DLSA referral. **Open: the amending notification number/date (Malik to ask MPSLSA/DLSA)**; confirm r.20 'clause (b)' = today's s.12(h) |
| G14 | Is the MP Shops and Establishments Act still in force, or changed/replaced by the 2026 Sanhita (G4)? | MP Labour; e-gazette | **MVP** (decide include) | resolved for v1 (DEC-045) + texts fetched 2026-11-07: MP Code (1958 Act Hindi, pre-2014 consolidation, corrupt text; 2014 Amendment Act No. 21; Rules 1959) and MP Labour DMS (Amendment Act No. 20 of 2025: overtime cap 144 h/quarter, ss.11/16/21; Second Amendment Act No. 25 of 2025, in force 15.12.2025: portal registration within 30 days, auto certificate, fee max Rs 2,500, ss.2/6/7/8/41). All gated G14 until base-text overlay (W1.1). Open: Act 20/2025 commencement (s.1 blank in scan); 2014 Act gazette date. Sanhita repeals all on commencement (G4) |

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
| LW1 | **Law-watch: final MP Code on Wages Rules.** Check periodically (MP Rajpatra, MP Labour DMS Sid=14/24, code.mp.gov.in) for a final notification; on finding it, add it as a new document that `supersedes` the 30.04.2026 draft, keeping the version chain (DEC-047). Also watch the Sanhita (G4) and EoDB (G16) commencement notifications | C (law-watch, W3.3; manual until then) | open; **check log 2026-11-07:** (a) final MP Code on Wages Rules: none (DMS Sid=14/24 newest = drafts + objection reports 24–25.06.2026; MP Code: none); (b) Sanhita commencement: none (DMS Sid=24 has the Act text, posted 21.07.2026; Sid=14 has the 06.04.2026 draft; news says 'in force' without a notification); (c) EoDB commencement: none found (MPIDC secretariat reported as 'coming up'). **Spotted:** MP Shops and Establishments (Fire and Hazard Prevention) Rules, 2026 (DMS Sid=14, 03.06.2026; relates to G14/s.33); an MP Act assented 25.03.2026 (Sid=14, 26.03.2026; unidentified); draft MP Social Security Code Rules 2026 (Sid=24, 26.06.2026). Next manual check: before 16 Nov |
| N1 | Hindi normaliser (W1.3, DEC-026) must strip zero-width joiner/non-joiner (U+200D/U+200C) before matching: mpvidhansabha.nic.in embeds them inside words ('राजस्‍व'), which breaks exact search | C | open |
| N2 | 4th corrupt-text pattern: MP Code's Hindi Shops Act 1958 PDF mixes Devanagari with Sundanese/Balinese-block code points (e.g. 'ᮧ', '᭭'); passes the Devanagari-share check. Add to the W1.1 text-quality gate tests | C | open |
| S1 | **Partial-scope instruments need a manifest field** (decision needed, Malik). DEC-037 indexes only TPA ss.105–111, Registration Act s.17, LSA Act s.12 and DPDP s.44(3) + definitions, but the manifest has no way to say "index only these provisions". Until decided, `IN.TPA1882@en@1`, `IN.RA1908@en@1`, `IN.LSA1987@en@1`, `IN.DPDP2023@en@1` stay `archive` (fetched, verified, not indexed). Note: the DPDP s.44(3) change is already served by RTI s.8(1)(j) in `IN.RTI2005@en@1` | M (schema decision) | resolved 2026-11-08 by **DEC-051** (`index_scope`): TPA ss.105–111, RA s.17, LSA s.12 indexed; DPDP stays archive |
| S2 | Hindi RTI Act: the only India Code Hindi copy found (`IN.RTI2005@hi@1`, archive snapshot 21.11.2023) pre-dates the 13.11.2025 s.8(1)(j) change and has the N1 glyph corruption ('अधिधनयम'). Find a current Hindi copy (India Code when it is back) | C | open |
| S3 | `IN.CPA2019@en@1` is India Code 'Last Updated 17-9-2021'. Check whether CPA 2019 was amended after that (e.g. by a Jan Vishwas Act) before relying on later-amended provisions. TODO(verify) | C | open |
| S4 | W0.4 step 3, still to fetch: **CPA Jurisdiction Rules** (Consumer Protection (Jurisdiction of the District Commission, the State Commission and the National Commission) Rules, 2021; not found in the archive yet); **e-Shram** and **PM-SVANidhi** guidelines (archive has only press releases / state street-vending schemes so far). indiacode.nic.in gave 504/timeouts on 2026-11-08, so the Acts came from Internet Archive copies (DEC-049) | C | open; **done 2026-11-08:** RTI Rules 2012 (gated S5), E-Commerce Rules 2020 + 2021 amendment (indexed) + corrigendum (archive); Model Tenancy Act 2021 EN/HI found (MoHUA, 02.06.2021) but not registered (S6) |
| S5 | **RTI Rules 2012 status.** DoPT circular No. 1/5/2016 dt 05.04.2017 invited comments on draft RTI Rules 2017 'in supersession of RTI Rules, 2012'. Confirm the 2017 draft was never notified (or find what replaced 2012), and confirm the G.S.R. number (803(E) per memory; the OCR layer reads '603(E)'). Both copies also need OCR (W0.5) | C | open |
| S6 | **Model Tenancy Act 2021 has no fitting manifest type** (decision needed, Malik). It is a model law adopted by the Union Cabinet on 02.06.2021 for states to adapt; not binding in MP. `INSTRUMENT_TYPES` has no `model_law` type (`act` would make it binding; `bill` is wrong), and the index gate requires a commencement check that a model law cannot have (same gap DEC-048 fixed for drafts). Files: mohua.gov.in Model-Tenancy-Act-English-02_06_2021.pdf (snapshot 20210605092047) and the Hindi copy (20220706003017, N1 glyph corruption) | M (schema decision) | open |

## F. Environment
| ID | Question | Owner | Status |
| --- | --- | --- | --- |
| E1 | Local Python is 3.12.0. Switch to latest 3.12.x? | M | resolved 2026-11-06: keep the local 3.12 install. The Lambda base image brings its own 3.12.x patch. |
| E2 | Terraform not installed — install via winget before W0.6 (needs OK) | M | open |
