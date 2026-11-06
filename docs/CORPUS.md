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

## Phase 0 — November 2026 MVP (existing scope)

| # | Instrument | Domain | Status (claimed) | Source portal | OCR? |
| --- | --- | --- | --- | --- | --- |
| 1 | RTI Act 2005 (EN + HI) | RTI | in_force; s.8(1)(j) amended by DPDP s.44(3), under SC challenge [P] | India Code; rti.gov.in | no |
| 2 | RTI Rules 2012 | RTI | in_force [P] | egazette / DoPT | maybe |
| 3 | DPDP Act 2023: s.44(3) + definitions | RTI/privacy | in_force, phased [P] | India Code / MeitY | no |
| 4 | Consumer Protection Act 2019 + Jurisdiction Rules 2021 + E-Commerce Rules 2020 + commission regs | Consumer | in_force [P] | India Code; consumeraffairs.nic.in; e-jagriti.gov.in | no |
| 5 | Code on Wages; IR Code; SS Code; OSH Code | Labour | in_force from 21 Nov 2025 [P] | India Code; labour.gov.in | no |
| 6 | Central Rules 2026 + Model Standing Orders | Labour | in_force [P] | labour.gov.in | maybe |
| 7 | MP draft rules under the four codes (5 Jan 2026) | Labour | draft [P] | labour.mponline.gov.in | maybe |
| 7a | **MP Karyasthal Sashaktikaran (Shram Shakti) Sanhita Bill 2026**, passed 21 Jul 2026 | Labour | passed; assent/notification to verify [R] | MP Vidhan Sabha / e-gazette | maybe |
| 8 | MP minimum-wage notifications (31 Mar 2026 + any Oct 2026 revision) | Labour | time-bound [P] | MP Labour Commissioner | likely |
| 9 | MP Accommodation Control Act 1961 (EN + HI) | Tenancy | in_force [P] | India Code; MP gazette | maybe |
| 10 | MP Parisar Kirayedari Adhiniyam 2010 | Tenancy | status unknown, lawyer to confirm (OPEN_QUESTIONS L1) [P] | MP gazette | likely |
| 11 | Model Tenancy Act 2021 | Tenancy | model_law, not binding in MP [P] | MoHUA | no |
| 12 | Transfer of Property Act ss.105–111; Registration Act 1908 s.17 | Tenancy | in_force [P] | India Code | no |
| 12a | **Registration (MP Amendment) Act 2025**: reconveyance deeds; s.80-C fees | Tenancy/land | assent 13 Oct 2026; commencement to verify [R] | MP e-gazette | maybe |
| 13 | Legal Services Authorities Act 1987 (s.12) | Legal aid | in_force [P] | India Code; NALSA | no |
| 14 | 3–5 scheme guidelines (e.g., e-Shram, PM-SVANidhi, one MP worker scheme) | Schemes | time-bound [P] | ministry / MP portals | maybe |
| 15 | **MP Lok Sewaon ke Pradan ki Guarantee Adhiniyam 2010** + rules + notified service list | Public services | in_force; service list changes by notification [R] | lokseva.gov.in/MPL; PRS copy | some |
| 16 | **Income / domicile / caste certificate *procedure*** (services under #15; e-District) | Public services | in_force; time limits to verify against the live list [R] | lokseva.gov.in; mpedistrict.gov.in | some |
| 17 | **Grievance routes:** CM Helpline 181 (MP), CPGRAMS | Public services | — | cmhelpline.mp.gov.in; pgportal.gov.in | no |

Items 15–17 are the "Sarkari Seva aur Praman-patra" module. Caste certificates are **procedure only**: the bot never
decides anyone's caste status. Items 7a and 12a change existing domains.

## Phase 1 — December 2026: land + farmers

| Instrument / scheme | Status (claimed) [R] | Source portal | OCR? |
| --- | --- | --- | --- |
| MP Land Revenue Code 1959 (2018, 2021 amendments; 2022 Ordinance + 2023 Second Amendment contents unverified) | in_force | India Code; revenue.mp.gov.in; PRS | some |
| Rules: Mutation 2018, Demarcation (2019 vs "2020" conflict), Assessment 2018, Survey & Land Records 2020, Restoration of Dispossessed Bhumiswami 2018 | in_force | revenue.mp.gov.in | some |
| Indian Stamp Act with MP amendments; Sampada 2.0 procedure | in_force; 2025 stamp bill to verify | sampada.mpigr.gov.in | no |
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
