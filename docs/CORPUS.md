# Corpus roadmap — Madhya Kanoon Saathi

Which laws, rules and schemes we ingest, in which phase, and from where. Decided in **DEC-032**.
Scope: Madhya Pradesh + central law, Hindi + English (DEC-016).

**Sources of the facts below:**
- **[P]** `docs/plan.md` §2 (5 Nov 2026)
- **[R]** the domain-expansion research report Malik shared on 6 Nov 2026

Neither is a primary source. **Every status, date, amount or time limit here is a claim to verify** against the
official text (India Code, e-gazette, the department portal) before ingestion (CLAUDE.md accuracy rule 1).
The status column uses our status flags. New flags proposed by [R] are marked *(new flag, pending DEC-033)*.

---

## Phase 0 — November 2026 MVP (reviewed 6 Nov 2026, DEC-037)

**Ingestion modes:**
- `index`: ingest and make searchable.
- `gated`: ingest only after the named check; until then the status decides the caveat or abstention.
- `archive`: download + checksum, but keep out of the search index.
- `guide`: an official procedure page (doc_type `official_guide`), not law.

| # | Instrument | Domain | Status (claimed) | Mode | Source portal | OCR? |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | RTI Act 2005 (EN + HI) | RTI | in_force; s.8(1)(j) amended by DPDP s.44(3), under SC challenge [P] | index | India Code; rti.gov.in | no |
| 2 | RTI Rules 2012 (central public authorities) | RTI | in_force [P] | index | egazette / DoPT | maybe |
| 2a | **MP RTI (Fees and Appeal) Rules 2005** (F 11-37-05-एक-9 dt 10.10.2005; state public authorities) | RTI | in_force; amendment check pending (G12) | gated: G12 → index after OCR fix + amendment check (DEC-045); state-vs-central routing | code.mp.gov.in (`MP.RTIFAR2005`) | yes (corrupt text layer) |
| 3 | DPDP Act 2023: **only** s.44(3) + the definitions it needs | RTI/privacy | in_force, phased [P] | index | India Code / MeitY | no |
| 4 | Consumer Protection Act 2019 + Jurisdiction Rules 2021 + E-Commerce Rules 2020 | Consumer | in_force [P] | index | India Code; consumeraffairs.nic.in | no |
| 4b | e-Jagriti filing steps (help docs only) | Consumer | — | guide | e-jagriti.gov.in | no |
| 5 | Code on Wages; IR Code; SS Code; OSH Code (**full text**) | Labour | in_force from 21 Nov 2025 [P] | index | India Code; labour.gov.in | no |
| 6 | Central Rules 2026 under the four codes | Labour | in_force [P] | index | labour.gov.in | maybe |
| 7 | MP draft rules under the four codes (5 Jan 2026); **Code on Wages rules re-published as a revised draft on 30 Apr 2026** (No. 83/2026/A-16; `MP.WCR2026`) | Labour | draft [P]; no final rules found (2026-11-07) | index as `draft` per DEC-037 (Wage rules: newer draft held gated: L3 until we confirm it replaces the Jan draft) | labour.mponline.gov.in; code.mp.gov.in | yes (Wage rules draft) |
| 7a | MP Karyasthal Sashaktikaran (Shram Shakti) Sanhita 2026 (MP Act 7/2026, Gazette No. 257 dt 10.08.2026) | Labour | **enacted_not_commenced** (DEC-044); s.1(3) commencement not notified; repeals #18 on commencement | gated: G4; interim PRS copy (DEC-043); monitor commencement | govtpress listing; PRS copy (`MP.SSS2026`) | yes |
| 8 | MP minimum-wage notification 22288-337 dt 30.09.2026 (valid 01.10.2026–31.03.2027) + Book; Apr 2026 one archived; Mar 2024 base-rate notification to fetch (L8) | Labour | time-bound; post-repeal legal authority unverified (DEC-042) | gated: **L7**; no current wage amounts until advocate review (DEC-045) | MP Labour DMS (`MP.MWVDAOCT2026`) | yes |
| 9 | MP Accommodation Control Act 1961 (EN + HI) | Tenancy | in_force [P] | index | India Code; MP gazette | maybe |
| 10 | MP Parisar Kirayedari Adhiniyam 2010 | Tenancy | unknown (L1, lawyer) [P] | **archive** until L1 resolved | MP gazette | likely |
| 11 | Model Tenancy Act 2021 | Tenancy | model_law, not binding in MP [P] | index | MoHUA | no |
| 12 | Transfer of Property Act **ss.105–111 only**; Registration Act 1908 **s.17 only** | Tenancy | in_force [P] | index | India Code | no |
| 13 | Legal Services Authorities Act 1987 (s.12) | Legal aid | in_force [P] | index | India Code; NALSA | no |
| 13a | **MP State Legal Services Authority Rules 1996** r.20 (₹12,000 "or higher as notified"); MPSLSA legal-aid page states ₹2,00,000; amending notification not found | Legal aid | rules in_force (text unamended); limit unresolved (G13) | rules gated: G13; page = guide → ₹2 lakh only as qualified official guidance + DLSA referral + other s.12 categories (DEC-045) | madhyapradesh.nalsa.gov.in (`MP.SLSAR1996`, `MP.SLSALAGUIDE2025`) | yes |
| 14 | Scheme guidelines: **e-Shram + PM-SVANidhi only** | Schemes | time-bound, `expires_on` where stated [P] | index | ministry portals | maybe |
| 15 | MP Lok Sewaon ke Pradan ki Guarantee Adhiniyam 2010 (Act 24/2010) + 2010 Rules + amendments (incl. Rules amendment 09.07.2026) + notified service list (19.08.2025) | Public services | in_force | gated: G6 | mpedistrict.gov.in/MPL (`MP.LSG2010`, `MP.LSGR2010`, `MP.LSGRA2026`, `MP.LSGSERVICES2026`) | yes (CCITT) |
| 16 | Income / domicile / caste certificate *procedure* (services 6.1–6.3, 6.7 under #15) | Public services | in_force; statutory time limits = s.3 notifications | gated: G6; 2013 gazette list (RCMS) = historical official source; unverified deadlines carry source date + uncertainty; the 2025 services list is **not** the time-limit notification (DEC-045) | mpedistrict.gov.in; rcms.mp.gov.in | yes |
| 17 | Grievance routes: CM Helpline 181 (MP), CPGRAMS | Public services | — | guide + `contacts.yaml` (DEC-018) | cmhelpline.mp.gov.in; pgportal.gov.in | no |
| 18 | MP Shops and Establishments Act 1958 (No. 25 of 1958) + 2025 amendment + Second Amendment Act 2025 | Labour | in_force **until #7a commences** (repealed by Sanhita s.40(1)(b)) | index as the applicable framework with a "to be replaced by the Sanhita" caveat (DEC-045); fetch pending | MP Code / India Code; MP Labour DMS (Sid=18) | maybe |
| 19 | **Land procedure slice (DEC-038):** MP Land Revenue Code 1959, **ss.109–110** (mutation) and **s.129** (demarcation), plus the sections they cross-refer to for authorities and appeals | Land | MPLRC (pre-2018 consolidation) + **MPLRC (Amendment) Act 2018 (No. 23/2018) substituting ss.109, 110, 129**, commenced **25.09.2018** (Nirdharan Rules r.1(2); notification No. 24-2018-VII-Sec-6 dt 16.08.2018 reported by Malik, gazette retrieval open); later amendments 2/2022, 20/2022, 1/2023 verified (G8). Bot must keep **s.129(5)** (SDO application within 45 days) distinct from **s.129(8)** (no appeal/revision) (DEC-046) | gated: G8 | **code.mp.gov.in** (`MP.LRC1959`, `MP.LRCA2018`); revenue.mp.gov.in down | no (born-digital EN) |
| 20 | MP Bhu-Rajasv Sanhita (Bhu-Abhilekhon Mein Namantaran) Niyam 2018 (F 2-14/2018/VII/Se.6; under s.258(2)(xxiii) r/w ss.109–110) | Land | in_force from gazette publication (date not printed; MP Code lists 31-12-2018) | gated: G8 | **code.mp.gov.in** (`MP.LRCMR2018`) | no (born-digital EN) |
| 21 | MP Bhu-Rajasava Sanhita (Seemankan) Niyam 2018: notification F-2-13-2018-7-Se.7, recorded date 28.01.2019 (reported in force 01.02.2019; discrepancy G8g). Rules 3–11, Forms I–III, agencies, team, fees (r.4: Collector-fixed with Commissioner approval, district-specific), boundary marks | Land | **qualified** (DEC-046): full reproduced text located by Malik, not source-verified; original gazette unavailable | **gated** (`MP.LRCDR2018`, instrument only); s.129 statute answers not blocked; no universal fee amounts | revenue.mp.gov.in (down); not on MP Code; reproduced copy (Malik) | ? |
| 19a | Later amendments to the MPLRC: Act 2/2022 (s.110(8), Cyber Tahsil s.13-A), Act 20/2022 (s.9), Act 1/2023 ("or Patwari" in s.129) | Land | in_force (assented + published) | 2/2022 and 1/2023 gated: G8; 20/2022 archive | **mpvidhansabha.nic.in** (`MP.LRCAJAN2022`, `MP.LRCASEP2022`, `MP.LRCA2023`) | yes |
| 22 | Getting a khasra / B-1 / Bhulekh copy online; Cyber Tehsil steps | Land | — | guide | MP Bhulekh / revenue portal | no |
| 23 | **MP Repeal (निरसन) Act 2026** (MP Act 8/2026, Gazette No. 260 dt 11.08.2026) | All | checked 2026-11-07: repeals 7 CP&Berar-era Acts (1933–1947) in whole; **no corpus instrument affected** (G15) | instrument record only (`MP.NIRSAN2026`); not indexed | PRS copy (govtpress PDF 404) | yes |
| 24 | **MP Ease of Doing Business Act 2026** (MP Act 9/2026, Gazette No. 264 dt 20.08.2026) | Labour / business | checked 2026-11-07: enacted, **not commenced** (s.1(3)); only notified industrial areas (s.1(2)); no textual amendment of corpus laws; once commenced, S&E registration (#18) runs via the State Nodal Agency (Sch. IV item 41) and missed clearance limits are penalised under the Lok Seva Act (#15, s.20) (G16) | instrument record only (`MP.EODB2026`); watch commencement | PRS copy (govtpress PDF 404) | yes |

**Land deadline (DEC-045):** retry official sources for the complete MPLRC, amendments and rules (revenue.mp.gov.in is
down; try India Code and MP Code). If no official text by **16 Nov 2026**, land-law advice leaves the November demo and
items 19–22 move to December. Secondary sources never replace verified legislation.

**Land slice limits (DEC-038):** procedure only (how to apply, time limits, which authority, appeals). No ownership,
title, inheritance, encroachment or tribal-land (s.165(6)) merits answers: the dispute detector routes these to DLSA.
The jurisdiction guard is mandatory: never cite the Chhattisgarh or Maharashtra Land Revenue Codes.

Items 15–17 are the "Sarkari Seva aur Praman-patra" module. Caste certificates are **procedure only**: the bot never
decides anyone's caste status (DEC-033 sensitive-data rule).

**Removed from Phase 0 (DEC-037):**
- Registration (MP Amendment) Act 2025 → Phase 1 (it's about land and mortgages, not tenancy).
- Model Standing Orders → later (employer/CA phase).
- Consumer commission procedure regulations → later.
- MP worker scheme → Phase 1 with the schemes.

**Excluded:** DPDP Rules 2025. They govern our own compliance, not users' questions.

**Golden-set effect (DEC-037):** the schemes slice drops from 10 to ~5 rows. The other ~5 move to public-services and
state-RTI rows. Total stays 120.

## Phase 1 — December 2026: rest of land + farmers

The mutation and demarcation procedure slice moved to Phase 0 (DEC-038). Phase 1 adds the rest of land: the remaining
MPLRC sections and rules, diversion, partition, s.165(6), s.250, stamp and registration, SVAMITVA, acquisition.
It also adds all farmer schemes.

| Instrument / scheme | Status (claimed) [R] | Source portal | OCR? |
| --- | --- | --- | --- |
| MP Land Revenue Code 1959 (2018, 2021 amendments; 2022 Ordinance + 2023 Second Amendment contents unverified) | in_force | India Code; revenue.mp.gov.in; PRS | some |
| Rules: Mutation 2018, Demarcation (2019 vs "2020" conflict), Assessment 2018, Survey & Land Records 2020, Restoration of Dispossessed Bhumiswami 2018 | in_force | revenue.mp.gov.in | some |
| Indian Stamp Act with MP amendments (incl. rent-agreement duty); Sampada 2.0 procedure | in_force; 2025 stamp bill to verify | sampada.mpigr.gov.in | no |
| Registration (MP Amendment) Act 2025: reconveyance deeds, s.80-C fees (moved from Phase 0, DEC-037) | assent 13 Oct 2026; commencement to verify (G5) | MP e-gazette | maybe |
| One MP worker/farmer scheme (moved from Phase 0, DEC-037) | time-bound | MP portals | likely |
| SVAMITVA property cards; RFCTLARR Act 2013 | in_force | India Code; ministry | no |
| MP Nagar Tatha Gram Nivesh (Amendment) 2025: land pooling | to verify | MP e-gazette | maybe |
| PM-KISAN; PMFBY (helpline 14447); KCC; PM-AASHA | time-bound / seasonal | pmkisan.gov.in; pmfby.gov.in; RBI | no |
| MP: CM Kisan Kalyan Yojana (amount conflict: ₹6,000 vs ₹4,000); Bhavantar (Kharif 2026); MSP via e-Uparjan; stubble-burning disqualification | time-bound; verify orders | mpeuparjan.nic.in; agriculture dept | likely |
| Central farm laws 2020 | **repealed** (2021) | — | — |

**Guard:** never cite the Maharashtra or Chhattisgarh Land Revenue Codes (both amended 2025–26, per [R]).

## Phase 2 — Q1 2027

| Area | Instruments [R] | Notes |
| --- | --- | --- |
| Students | RTE Act 2009 s.12(1)(c) + MP RTE Rules 2011; NSP + MP scholarship portal; UGC anti-ragging regs 2009; MP Niji Vidyalaya fee Act 2017; Apprentices Act 1961 + NAPS; education-loan subsidy | Must be live **before March 2027** (RTE cycle). Reservation answers must show the OBC court position + challenge banner |
| Cyber / FIR basics | BNSS 2023 (s.173 Zero/e-FIR, s.35(3), s.144); BNS; IT Act 2000; cybercrime.gov.in + 1930 | Information only. Arrest and bail questions are escalated |
| Banking / insurance | RBI Integrated Ombudsman Scheme 2021; RBI Digital Lending Directions 2025; Insurance Ombudsman Rules 2017; MSME Samadhaan | Low risk |
| Women's safety | PWDVA 2005; Dowry Prohibition Act 1961; BNS cruelty provisions; BNSS s.144; POSH Act 2013 (SHe-Box); One Stop Centres | Safety-first flow is mandatory |
| Senior citizens | MWPSC Act 2007 + MP Rules; Elder Line 14567 | — |

## Phase 3 — Q2 2027

| Area | Instruments [R] | Notes |
| --- | --- | --- |
| Panchayat / rural jobs | MP Panchayat Raj Avam Gram Swaraj Adhiniyam 1993; PESA Act 1996; MP PESA Rules 2022; **VB-G RAM G Act 2025** | [R]: MGNREGA repealed, VB-G RAM G in force from 1 Jul 2026, 125 days. OCR-heavy district circulars |
| SC/ST + forest rights | SC/ST (PoA) Act 1989 + Rules 1995; PCR Act 1955; Forest Rights Act 2006 + Rules; MPLRC s.165(6) | Strict mode. Relief increase is a **proposal only** [R] |
| Disability | RPwD Act 2016; UDID | Never ask for a diagnosis or disability percentage |

## Phase 4 — H2 2027 or later

Family / marriage (MP UCC 2026: **passed, awaiting Presidential assent, not in force** [R]); RERA; motor-accident
claims; electricity consumer forums; NFSA / ration; Ayushman Bharat / PM-JAY; birth/death registration.
Ration and Ayushman may move earlier if NGO demand shows up.

---

## Status traps (verify first; the bot must never get these wrong)

| Trap | Claim [R] | Bot behaviour |
| --- | --- | --- |
| MGNREGA | Repealed; replaced by VB-G RAM G Act 2025 from 1 Jul 2026 (125 days) | Never answer "100 days under MGNREGA" as current |
| MP 27% OBC quota | Struck down by MP HC on 9 Oct 2026; 14% restored; State SLP at defects stage | 14% position + "under challenge" banner; never predict the outcome |
| MP UCC 2026 | Passed 21 Jul 2026; awaiting Presidential assent | "Not in force" |
| SC/ST relief amounts | 2016 schedule in force; increase is a task-force proposal | Quote the current schedule only |
| Central farm laws 2020 | Repealed 2021 | Never cite as current |
| MP labour Sanhita 2026 | Passed Jul 2026; assent/notification unverified | Caveat on labour answers |
| MP land code news | "Automatic mutation" reports are about **Chhattisgarh**, not MP | Jurisdiction guard |

## Escalation and helpline numbers mentioned in [R]

112, 181 (MP: both a women's helpline and the CM Helpline — must be disambiguated), 1098, 1930, 14416, 14447,
14555, 14567, 15100, 1800-180-5522. **None may be used** until each has an official source page in `contacts.yaml`
(DEC-018).
