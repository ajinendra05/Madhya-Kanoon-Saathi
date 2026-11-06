> **Status banner (added 2026-11-05, DEC-008):** this plan is the original design. Later decisions in
> [`docs/DECISIONS.md`](DECISIONS.md) **override** it wherever they conflict. Main overrides:
> - OCR is Bodhan IndicOCR, not Sarvam (DEC-001).
> - Hosting is always-free serverless AWS: Lambda + SQS + DynamoDB + EventBridge, with no Aurora, Fargate or API Gateway (DEC-002, DEC-010).
> - There is no vector DB; FAISS + BM25 index files are packed into the image (DEC-003).
> - Embeddings are BGE-M3, not Cohere (DEC-004).
> - Secrets live in SSM Parameter Store (DEC-009).
> - Scope is MP + central, Hindi + English, with no Marathi (DEC-016).
> - There is no VPC (DEC-029).
> - The project name is Madhya Kanoon Saathi (DEC-017).
>
> The body below is left unchanged as history.

# Kanoon/Niyam Saathi: A Build Plan for a Citation-Verified, Multilingual Legal-Information RAG (MP-first), as of 5 Nov 2026

**Bottom line:** Build Niyam Saathi as an **MP-first, Hindi-first legal-information assistant** over central laws plus Madhya Pradesh rules. Every answer should cite a clause that is checked automatically, and the assistant should abstain when the law is unsettled. Use Postgres + pgvector on AWS ap-south-1. Use Sarvam-105B as the default generator and Claude via Bedrock's India geo profile as fallback and judge. Ship a Telegram bot first and WhatsApp second. Give yourself ~3.5 weeks for an eval-backed, cost-tracked demo you can take to interviews by 30 Nov 2026. Your edge over Nyaya Setu, Indian Kanoon and the many hackathon clones is not "AI legal chat". It is **state-specific accuracy + verifiable citations + a published eval report + an NGO workflow**.

## TL;DR
- **What to build and where:** Start with Madhya Pradesh plus central laws (tenancy, consumer, RTI, labour codes, a few schemes), in Hindi + English, with Marathi as the +1 language in v2. Tenancy is a state subject. MP still runs on the MP Accommodation Control Act, 1961, and its MTA-style tenancy bill was shelved again before the July 2026 monsoon session. MP's labour-code rules were published only in draft (5 Jan 2026). This messiness is your product: state-aware, "law-as-of"-dated, citation-verified answers that say clearly when something is a model law, a draft or under challenge.
- **How to build it cheaply and defensibly:** Use clause-aware chunking, then hybrid BM25 + multilingual dense retrieval (Cohere Embed Multilingual v3 runs in-region in ap-south-1, listed at $0.10 per 1M tokens; check on-demand access because one tracker lists it as deprecating on 15 Feb 2027), then a cross-encoder reranker, then a generator that must emit JSON claims tied to chunk IDs, validated by code. A text query costs roughly ₹0.1–0.7 in model fees (Sarvam-105B at ₹15/₹60 per 1M tokens vs Claude Haiku 4.5 on the India geo profile at ~$1.10/$5.50). Voice and WhatsApp volume are the real cost drivers. Note that Bedrock rerank models are **not** offered in ap-south-1.
- **How to win interviews:** Present a 120-question golden set built from real WhatsApp/Telegram questions, per-language eval breakdowns (recall@k, citation precision, faithfulness, refusal correctness), CI regression gates, a per-query INR cost dashboard, and a clear compliance story (BCI Rule 36, DPDP Rules phases on 13 Nov 2026 and 13 May 2027). Together these make up a complete system-design narrative.

---

## Key Findings (current facts verified for this plan)

| Area | Current status (as of early Nov 2026) | Implication for the product |
|---|---|---|
| Labour Codes | All four codes in force from 21 Nov 2025. Central Rules notified 8 May 2026 (one tracker records the OSH Rules as 9 May). Labour is on the Concurrent List, so each state notifies its own rules, and most were still drafts as of May 2026. | Answers must say whether a rule is a Central Rule (covers establishments where the Centre is the appropriate government) or a state rule. |
| MP labour rules | MP Labour Dept published **draft** rules under all four codes on 5 Jan 2026, with a 45-day objection window. The draft wage rules would supersede the MP Minimum Wages Rules 1958 and the Payment of Wages Rules 1962. A Hindi report says an MP labour-related bill passed in the 20–22 Jul 2026 monsoon session. | Tag MP rules `status=draft` until a final gazette is found. Re-check the MP Labour DMS weekly. |
| MP minimum wages | Notification of 31 Mar 2026, effective 1 Apr–30 Sep 2026: unskilled ₹12,425/month (₹478/day), highly skilled ₹16,769/month. The next revision was due 1 Oct 2026. | A good "time-versioned fact" test case. Every wage answer needs a validity window. |
| Tenancy (national) | The Model Tenancy Act 2021 is advisory only. Tenancy falls under Entry 18 of the State List. Adoption lists conflict even between Rajya Sabha replies. On 25 Jul 2022 MoS Housing Kaushal Kishore said AP, TN, UP and Assam "have revised Tenancy Acts on the lines of MTA". A later RS reply, reported by DT Next, lists Assam, Arunachal, A&N, DNH&DD and Lakshadweep as adopters and says AP, TN, Uttarakhand and UP have only "issued draft notifications". | Never answer "MTA says X" as binding law. Label it as a model law. |
| Tenancy (MP) | MP still uses the **MP Accommodation Control Act, 1961** (Rent Controlling Authority, not below Deputy Collector). A draft "MP Tenancy Act 2024" (MTA-based) was reviewed against the 2010 MP Parisar Kirayedari Adhiniyam. Patrika reported the tenancy bill "put in cold storage" before the Jul 2026 monsoon session, which passed UCC and other bills instead. | MVP must cover the 1961 Act. The 2010 Act's enforcement status needs lawyer verification (see Caveats). |
| Consumer | CPA 2019. e-Daakhil, OCMS, CMS and Confonet were merged into **e-Jagriti** on 1 Jan 2025. Pecuniary jurisdiction depends on *consideration paid* (2021 Jurisdiction Rules). No filing fee if consideration ≤ ₹5 lakh. | Procedural answers should link to e-jagriti.gov.in, not e-Daakhil. |
| RTI | RTI Act 2005 + RTI Rules 2012. DPDP s.44(3) replaced s.8(1)(j) with a blanket "personal information" exemption, in force from 13 Nov 2025. SC petitions are pending: Venkatesh Nayak W.P.(C) 177/2026, NCPRI 212/2026, Reporters' Collective 211/2026, MKSS (notice 13 Apr 2026), DNPA (notice 27 Oct 2026). No stay as of 3 Nov 2026. | RTI answers about personal information must quote the *amended* s.8(1)(j), flag the pending challenge, and note that s.8(2)'s public-interest override survives. |
| DPDP Rules | Notified 13/14 Nov 2025. Rule 4 (Consent Managers) from **13 Nov 2026**. Rules 3, 5–16, 22, 23 (notice, consent, security, breach, children, rights) from **13 May 2027**. | Design for DPDP compliance now. Hard obligations land before any real scale. |
| Nyaya Setu | Govt WhatsApp legal-help service on 7217711814 (shows as "Tele-Law"), announced 1 Jan 2026. The AI chatbot and mascot "Dishika", built by the Digital India BHASHINI Division, were unveiled at the DoJ DISHA programme at Vigyan Bhawan (31 Mar 2026) by Vice-President C.P. Radhakrishnan and MoS Law Arjun Ram Meghwal. According to PIB, it offers "over 20 specialised NLP services across 36 text and 23 voice languages." The Live Nagpur (5 Jan 2026) reported that shortly after launch "several users reported technical issues while using the chatbot." | Free incumbent with distribution. Position as complementary: escalate to it, don't compete on breadth. |
| Bedrock in India | Claude Opus 5, Sonnet 5 and Haiku 4.5 are available through the **India geographic cross-Region inference** profile (routes only ap-south-1 ↔ ap-south-2), announced 29 Sep 2026. Rerank (Cohere 3.5, Amazon Rerank 1.0) is **only** in ap-northeast-1, ca-central-1, eu-central-1, us-east-1 and us-west-2. | Self-host the reranker (or accept that rerank data leaves India). |
| WhatsApp pricing | From 1 Oct 2026: 1,000 free service messages per business number per month, then ₹0.115 per message (Meta rate). Utility templates inside the 24-h window are now chargeable. BSPs mark up (e.g., AiSensy ₹0.145). | WhatsApp is cheap at portfolio scale but no longer free. Telegram is free. |

---

## 1. Problem, users, and validation → golden set

### Problem statement (use this sentence in interviews)
"First-generation workers, tenants and small shopkeepers in Hindi-speaking India can't get a **state-correct, clause-cited** answer to everyday legal questions. Laws are split across central acts, state acts, drafts and gazette notifications, mostly in English PDFs. Generic chatbots hallucinate sections and ignore state variation."

### Target users and their top jobs-to-be-done
| User | Typical question | What "good" looks like |
|---|---|---|
| Tenant (Jabalpur/Bhopal/Indore) | "Can my landlord keep my whole deposit / evict without notice?" | MP 1961 Act section + plain-Hindi steps + where to complain (Rent Controlling Authority / DLSA) |
| Small-business owner | "Do I need to give appointment letters / pay overtime at 2x under new codes?" | Code + Central/State rule + "MP rules still draft" caveat |
| First-gen job-seeker | "Employer hasn't paid wages for 2 months" / "What is min wage in MP?" | Code on Wages section, current MP notification with validity dates, complaint route |
| NGO volunteer | "How do I help someone file RTI / consumer complaint?" | Procedure + form fields + fees + appeal timelines, exportable as a checklist |

### WhatsApp/Telegram validation plan (Week 0, start today)
1. **Pick 3 groups** you can genuinely access: one Jabalpur/MP tenants or locality group, one job-seeker/skilling group, one NGO/legal-aid volunteer group (law-college legal-aid clinics are ideal). Ask the admin's permission first.
2. **Post (Hindi + English):** "मैं एक AI टूल बना रहा हूँ जो किरायेदारी, उपभोक्ता, RTI और श्रम कानूनों पर धारा-सहित जानकारी देता है। अपना सवाल भेजिए — मैं AI से जवाब बनाकर खुद कानून से मिलाकर भेजूँगा। यह कानूनी सलाह नहीं, सामान्य जानकारी है। अपना नाम/पता/फोन न लिखें।" Plus the English equivalent. The disclaimer and the "don't share personal details" line start your DPDP-minimisation habit from day 1.
3. **Respond within 24 h.** Draft with your prototype (or manual search on India Code), verify by hand against the official text, and reply with the section cite.
4. **Log every question** in a Google Sheet that mirrors the golden-set schema below. Strip names and phone numbers at entry.
5. **Success metrics:** ≥60 real questions in 10 days = strong signal. 20–60 = proceed and supplement. <20 = re-target (legal-aid clinics, r/LegalAdviceIndia-style forums, NGO FAQs). Also track repeat askers and "would you use this again?" replies.

### Turning questions into a 120-item golden set
**Target composition (adjust to what users actually ask, but keep the floors):**
| Slice | Target count | Floor rule |
|---|---|---|
| Tenancy (MP + MTA-as-model + TPA/Registration basics) | 35 | – |
| Labour codes (Central + MP draft + min wages) | 30 | – |
| Consumer (CPA 2019, e-Jagriti, jurisdiction) | 25 | – |
| RTI (Act, Rules 2012, amended 8(1)(j)) | 20 | – |
| Schemes / legal aid eligibility | 10 | – |
| **Should-abstain / out-of-scope / needs-a-lawyer** | ≥25 (overlaps the above) | ≥20% of set |
| Language mix | ≥45% Hindi or Hinglish, ≥35% English, ≥10% Marathi (added in v2) | Per-language reporting |
| Synthetic (paraphrases/NGO FAQs) | ≤30% | Must be flagged `source=synthetic` |

**Labeling schema (one row per question; store as JSONL in the repo):**
```
id, source (whatsapp|telegram|ngo|synthetic), received_at, raw_question_redacted,
language (hi|en|hinglish|mr), script (deva|latn), state (MP|central|other:<code>),
domain (tenancy|labour|consumer|rti|scheme|other), intent (definition|procedure|eligibility|
deadline|amount|rights_scenario|document_review), answerability (answerable|partial|unanswerable),
unanswerable_reason (out_of_corpus|needs_more_facts|individual_legal_advice|law_pending_or_draft|
sub_judice|other_state), expected_clauses [{act_id, section, subsection, proviso, version_as_of}],
key_facts [atomic claims], must_include [e.g., "Rent Controlling Authority"],
must_not_include [e.g., "MTA applies in MP"], expected_escalation (none|DLSA/NALSA|consumer_commission|
RTI_first_appeal|labour_inspector|Nyaya_Setu), reference_answer_en, reference_answer_hi,
difficulty (1-3), verified_by, verified_on, law_as_of_date, notes
```
**Labeling protocol:** You label all 120 rows. Get a second reviewer (law student or legal-aid volunteer, paid a small honorarium) to double-label at least 30 rows. Report inter-annotator agreement on `answerability` and `expected_clauses`. Freeze `v1.0` and version it. Never edit the frozen set silently; add `v1.1` rows when the law changes.

---

## 2. Corpus: what to ingest and from where

### MVP corpus (central + MP)
| # | Instrument | Status flag | Authoritative source |
|---|---|---|---|
| 1 | Right to Information Act, 2005 (EN + HI) | in_force (s.8(1)(j) amended) | India Code; rti.gov.in |
| 2 | RTI Rules, 2012 | in_force | egazette.gov.in / DoPT |
| 3 | DPDP Act, 2023: s.44(3) and definitions | in_force (phased) | India Code / MeitY |
| 4 | Consumer Protection Act, 2019 + Jurisdiction Rules 2021 + E-Commerce Rules 2020 + Commission procedure regs | in_force | India Code; consumeraffairs.nic.in; e-jagriti.gov.in help docs |
| 5 | Code on Wages 2019; IR Code 2020; SS Code 2020; OSH Code 2020 | in_force from 21 Nov 2025 | India Code; labour.gov.in |
| 6 | Four Central Rules 2026 (8–9 May 2026) + Model Standing Orders | in_force | labour.gov.in gazette PDFs |
| 7 | MP draft rules under all four codes (5 Jan 2026) | **draft** | labour.mponline.gov.in DMS (Acts & Rules) |
| 8 | MP minimum wage notifications (31 Mar 2026 and any Oct 2026 revision) | time-bound | MP Labour Commissioner, Indore |
| 9 | MP Accommodation Control Act, 1961 (EN + HI) | in_force | India Code (state section); MP gazette |
| 10 | MP Parisar Kirayedari Adhiniyam, 2010 | **verify status** | MP gazette / Vidhan Sabha |
| 11 | Model Tenancy Act, 2021 | **model_law (not binding in MP)** | MoHUA |
| 12 | Transfer of Property Act 1882 (ss.105–111, leases); Registration Act 1908 (s.17) | in_force | India Code |
| 13 | Legal Services Authorities Act 1987 (s.12 eligibility) | in_force | India Code; NALSA |
| 14 | 3–5 scheme guideline PDFs (e.g., e-Shram, PM-SVANidhi, an MP worker-welfare scheme) | time-bound | Ministry / MP portal |

**Bootstrap shortcut:** Vaquill's open-india-law dataset (CC BY 4.0) and its India API (64,179 acts / 745,970 sections built from India Code) can speed up section-level parsing. **Always re-anchor citations to the official India Code/gazette URL and keep a checksum.** Cite the primary source, never the aggregator.

### Hindi versions
India Code hosts many central acts bilingually. Ingest the official Hindi text as its own chunks, linked to the English chunk by a canonical `section_uid` (e.g., `RTI2005:s8:ss1:cl_j`). Never machine-translate statute text for citation. Translation is only for *explanations*.

### Versioning and amendment tracking
- Every document record stores: `source_url, fetched_at, sha256, gazette_ref, valid_from, valid_to, status (in_force|draft|model_law|repealed|sub_judice_flag), supersedes`.
- A weekly EventBridge job re-fetches watched URLs (egazette, labour.gov.in, MP Labour DMS, consumeraffairs, rti.gov.in). It diffs hashes and opens a GitHub issue/alert on change. Changed sections trigger re-embedding and a re-run of the affected golden-set rows.
- Every answer prints **"Law as of: <date>"** and the status flags for each cited instrument.

### MVP scope and +1 language: recommendation
- **State scope:** MP + central. Reasons: you live in Jabalpur (cheap validation, local NGOs, Hindi), MP is genuinely messy (1961 rent law, draft labour rules), and few competitors handle it.
- **+1 language: Marathi (v2, December).** It shares Devanagari script (same OCR/tokenisation path), and Maharashtra (Maharashtra Rent Control Act 1999) is the natural second state with a large migrant-tenant market. For the November demo, support Marathi *questions* on central laws only and report its eval slice separately. Don't add Maharashtra state law until December.

---

## 3. Legal, ethical and compliance guardrails

**Legal information vs legal advice.** Practising law (appearing, pleading, advising a specific client as their advocate) is reserved to enrolled advocates under the Advocates Act, 1961. Publishing general information about what the law says is not. Product rules:
1. Answer "what the law says + how the process works + where to go". Never "you will win / you should sue / draft my notice against X".
2. Detect individual-advice intents (litigation strategy, pending cases, criminal exposure, drafting against a named party). Abstain with a referral.
3. Show a persistent disclaimer in the user's language. Every answer carries citations, a "law as of" date and a "not legal advice" footer.

**BCI Rule 36 (B2B lawyer features).** Rule 36 bars advocates from soliciting or advertising "directly or indirectly". Several actions have extended this to online platforms and listings: the Madras HC judgment in PN Vignesh v. Chairman and Members of the Bar Council (3 Jul 2024), BCI Letter No. BCI:D:3417/2024 (6 Jul 2024) directing State Bar Councils to act, BCI cease-and-desist notices to Quikr, Sulekha, Just Dial and Grotal, and BCI's March 2025 directive. The Supreme Court has issued notice on the Sulekha/JustDial appeals. Therefore:
- **Do not build** a lawyer directory, lawyer ranking, "connect to a lawyer" marketplace, lead-gen or referral fees.
- **Do build** a SaaS *tool* that law/CA offices license for their own internal research and their *existing* clients' intake. Escalate citizens only to **statutory** free legal aid (DLSA/NALSA, Tele-Law, Nyaya Setu), never to named private lawyers.

**Escalation paths to hard-code:** NALSA helpline 15100 and the District Legal Services Authority (free legal aid for s.12 LSA Act categories), Tele-Law / Nyaya Setu WhatsApp 7217711814, e-Jagriti for consumer complaints, RTI first appeal/CIC/SIC, the labour inspector-cum-facilitator, and MP's Rent Controlling Authority.

**DPDP Act + Rules 2025 for a consumer app (design now, mandatory by 13 May 2027):**
| Obligation (Rule) | Your implementation |
|---|---|
| Itemised notice before consent (R.3) | Bilingual consent screen/first message; purpose = answering legal-info queries + improving quality |
| Consent Managers (R.4, from 13 Nov 2026) | Not required for you; just keep consent records exportable |
| Security safeguards (R.6) | KMS encryption, private subnets, least-privilege IAM, PII redaction before logging/tracing |
| Breach intimation (R.7) | Runbook: notify users + Data Protection Board (72-h detailed report) |
| Retention/erasure | Raw chats auto-deleted after 90 days; golden-set rows stored redacted only |
| Children (R.10) | Age gate ("18+ only"); no knowing processing of children's data |
| Grievance redressal | Named contact + in-bot "delete my data" command |

---

## 4. Competitive landscape and differentiation

| Player | What it is | Gap you exploit |
|---|---|---|
| **Nyaya Setu** (DoJ + BHASHINI) | Free, WhatsApp, voice-first, gateway to Tele-Law/Nyaya Bandhu. PIB says it covers "36 text and 23 voice languages". | Broad and generic. No public eval or citation guarantees. The Live Nagpur reported user "technical issues" right after launch. You *refer to* it. |
| **Indian Kanoon** | Huge free judgment/statute search | Search, not answers. English-centric. No state-aware plain-language guidance. |
| **Vaquill** | Legal-data API (India acts at section level, MCP server) + open dataset; US-focused workspace | Infrastructure, not a citizen product. A potential *data supplier*. |
| Hackathon clones (dozens on GitHub) | "Chat with IPC/Constitution PDFs" | No golden set, no state scope, no versioning, no compliance story |

**Differentiators (lead with these):** (1) MP-specific + status flags (draft/model/sub-judice); (2) code-verified citations with exact quote spans; (3) a public eval report broken down by language and domain; (4) an NGO workflow (case log, checklist export, volunteer seats); (5) per-query cost transparency.

---

## 5. Architecture and system design

```
[Telegram / WhatsApp Cloud API / Web]
        │ webhook
 API Gateway (HTTP API) ──► Lambda "ingress" (auth, rate-limit, PII redaction, LID) ──► SQS
                                                                                     │
                                                       ECS Fargate "answer" service (FastAPI)
   ┌───────────────────────────────────────────────────────────────────────────────┤
   │ 1 query understanding (lang, state, domain, intent, abstain-precheck)          │
   │ 2 query rewrite → EN + HI variants (cheap LLM call)                            │
   │ 3 hybrid retrieval: BM25 (bm25s in-memory) + pgvector HNSW (Cohere Embed v3)  │
   │   with metadata filters (state ∈ {MP, central}, status, valid_on=today)       │
   │ 4 RRF fusion → top-40 → cross-encoder rerank (bge-reranker-v2-m3) → top-6      │
   │ 5 generation (Sarvam-105B default | Claude via Bedrock India geo fallback)    │
   │ 6 citation validator (chunk_id ∈ retrieved, quote span exact match)           │
   │ 7 answer in user language (+ optional Bulbul TTS)                              │
   └──► Postgres (Aurora Serverless v2 / RDS) : chunks, embeddings, query_log, cost_log
 S3: raw PDFs, parsed JSON, eval artifacts │ EventBridge: weekly law-watch │ CloudWatch + OTel traces
```

### Ingestion
- **Prefer born-digital text** (India Code HTML/PDF text layer). OCR only scanned gazettes and Hindi PDFs.
- **Indic OCR:** Sarvam Document Digitization at ₹0.50/page (Document Extraction ₹1/page). About 3,000 scanned pages ≈ ₹1,500. Benchmark it against Tesseract `hin` (free) by character error rate on 20 hand-verified pages. Amazon Textract is not a fit for Devanagari.
- **Clause-aware chunking:** parse the hierarchy Act → Chapter → Section → Sub-section → Clause → Proviso/Explanation with regex + layout cues. The chunk unit is the sub-section (provisos and explanations stay attached). Store the parent section for "expand context" (parent-child retrieval). Target 150–450 tokens, which fits Cohere Embed v3's 512-token window.
- **Metadata per chunk:** `section_uid, act_id, act_title_en/hi, jurisdiction, state, doc_type, status, valid_from/to, language, heading, page, source_url, sha256, amended_by`.

### Retrieval
- **Hybrid:** BM25 on a normalised "simple" analyser (Postgres lacks a Hindi stemmer, and an in-memory `bm25s` index is fine for a ~10–30k-chunk corpus), plus dense vectors in pgvector, fused with Reciprocal Rank Fusion. Section-number queries ("धारा 8(1)(j)") need BM25/exact match, so hybrid is non-negotiable.
- **Embeddings, recommended:** **Cohere Embed Multilingual v3 on Bedrock, in-Region in ap-south-1.** Portkey and Maxim list it at $0.10 per 1M tokens with a 512-token maximum input, so the whole corpus embeds for well under $1. Check two things in the AWS console before committing. First, cloudprice.net lists the model as "Deprecating 2027-02-15". Second, eesel.ai says Bedrock offers it only through Provisioned Throughput at $7.12/hour. Keep self-hosted BGE-M3 as the ready fallback. Embed v4 is reachable from Mumbai only via the *global* profile (data may leave India), so skip it. **Benchmark BGE-M3 offline** (dense + sparse in one model, long context) and **multilingual-e5-large**. Report recall@10 per language and keep the winner. That comparison table is interview gold.
- **Cross-lingual:** store both EN and HI official text. Retrieve with the original query **and** an English rewrite produced by a cheap LLM call. For a ~150-character query, an LLM rewrite costs ~₹0.01 vs ~₹0.30 via the Translate API (₹2/1,000 chars). Use Sarvam Translate where quality matters (answer post-editing, Marathi).
- **Reranking:** Bedrock Rerank isn't available in ap-south-1. **Recommended:** self-host `bge-reranker-v2-m3` on the Fargate task (CPU; 40 pairs is fine for an MVP; measure p95). Run Cohere Rerank 3.5 (Tokyo, $2 per 1,000 queries) as an *eval-only* comparison on the golden set, and document the data-residency trade-off.

### Generation
- **Citation enforcement:** the model must return JSON: `{answer_blocks:[{text, citations:[{chunk_id, quote}]}], abstain:bool, abstain_reason, escalation}`. The validator rejects any `chunk_id` not in the context and any `quote` that isn't an exact substring after Unicode NFC normalisation. It retries once, then strips the unsupported claim. If no supported claims remain, it abstains.
- **Abstention triggers:** top rerank score below a calibrated threshold, state ∉ corpus, intent = individual advice, or a cited instrument with `status ∈ {draft, sub_judice, model_law}`. In that last case the bot *answers with a caveat* rather than refusing.
- **Answer language:** generate directly in the user's language (Hindi or Hinglish mirrored), with statute quotes in their official language. Avoid "generate in English → translate", which costs ₹2 per 1,000 chars and loses register.
- **Voice (December):** Saaras STT ₹0.49/min; Bulbul v4 Flash TTS ₹1.00/1,000 chars (half price until 12 Nov 2026) or Bulbul v3 at ₹3.00/1,000 chars.

### LLM choice: recommendation with trade-offs
| Model | Price (per 1M tokens) | Pros | Cons | Role |
|---|---|---|---|---|
| **Sarvam-105B** (`sarvam-105b`) | ₹15 in / ₹5 cached / ₹60 out (excl. GST) | Indic-native, INR billing, Indian provider, cheapest | 60 req/min on pay-as-you-go; JSON/citation discipline must be proven by eval | **Default generator** for hi/mr |
| **Claude Haiku 4.5** via Bedrock `in.` profile | ~$1.10 / $5.50 (global $1/$5 + 10% regional premium) | Strong instruction following, stays in India (ap-south-1↔ap-south-2) | ~7x Sarvam cost per query | Fallback when validator fails twice |
| **Claude Sonnet 5** via Bedrock `in.` profile | ~$2.20 / $11 (global $2/$10 + 10%) | Best reasoning; good judge | Highest cost | **LLM-as-judge** + hard queries |

Decide the default **by the golden-set numbers, not vibes**. Publish the A/B in the eval report.

---

## 6. Evaluation

| Layer | Metric | MVP gate (CI fails below) |
|---|---|---|
| Retrieval | Recall@10 of `expected_clauses` (section_uid match); MRR@10; nDCG@10 | Recall@10 ≥ 0.85; MRR ≥ 0.6 |
| Citations (deterministic) | Citation precision (cited ⊆ retrieved ∩ expected-or-supporting); citation recall vs expected; quote exact-match rate | Precision ≥ 0.90; quote match = 1.00 |
| Generation | Faithfulness (claim-level, judge); answer correctness vs `key_facts`; `must_not_include` violations | Faithfulness ≥ 0.90; zero `must_not_include` hits on critical rows |
| Safety | Refusal correctness: abstain precision/recall on `answerability=unanswerable` | Abstain F1 ≥ 0.85 |
| Language | Answer-language match (Sarvam LID ₹0.35/1k chars); human fluency 1–5 on a 30-row sample | Match ≥ 0.98; fluency ≥ 4 |
| Ops | p50/p95 latency; ₹/query | p95 < 8 s text; ≤ ₹1 text query |

**Tooling:** use **Ragas** for batch RAG metrics (faithfulness, context precision/recall) and **DeepEval** for pytest-style CI assertions. Write your own deterministic citation/retrieval scorers; they are the most important and need no LLM. Run everything per slice (language × domain × answerability).

**Judge calibration:** hand-grade 40 answers on faithfulness and correctness. Compute Cohen's κ between you and the Sonnet-5 judge. Target κ ≥ 0.6, iterate on the judge rubric if lower, and report κ in the eval report. Re-calibrate whenever the judge model changes.

**CI regression gates:** a GitHub Actions job runs on every PR. Use a fast 40-question "smoke" subset with a cached judge, plus nightly full 120. Fail on any gate drop > 2 points. Post a markdown diff table on the PR.

---

## 7. AWS deployment (ap-south-1)

| Concern | Choice | Why |
|---|---|---|
| Vector + metadata + logs | **Aurora PostgreSQL Serverless v2 + pgvector** (min 0 ACU in dev, 0.5 ACU on demo days) | Supports scale-to-zero (PG 13.15+/14.12+/15.7+/16.3+). One store for chunks, BM25 sidecar data and cost logs. Avoids the OpenSearch Serverless classic floor (2 OCU ≈ $350/mo; 4 OCU ≈ $701/mo). Some 2026 posts describe NextGen OpenSearch Serverless collections with no OCU floor; re-evaluate, but you don't need it at this scale. |
| Compute | Lambda for webhooks/ingress + ingestion jobs; **one ECS Fargate task** for the answer service + reranker | Reranker model + warm BM25 index don't suit Lambda cold starts |
| Storage | S3 (raw PDFs, parsed JSON, eval runs), versioning on | Audit trail for law versions |
| API/auth | API Gateway HTTP API; Cognito only for the NGO/B2B web console | Bots authenticate by platform user ID (hashed) |
| Secrets | Secrets Manager (Sarvam key, bot tokens) | — |
| Observability | OpenTelemetry → CloudWatch/X-Ray; structured JSON logs; Bedrock CloudWatch metrics; optional self-hosted Langfuse with PII redaction | End-to-end trace per query |
| IaC | **Terraform** (or CDK in Python) + GitHub Actions OIDC deploy | Shows production habits |
| Guardrails | AWS Budgets alerts at $20/$40; per-user daily quota; Sarvam `402` (credits exhausted) → fallback to Bedrock | Cost-spike protection |

**Channels:** **Telegram Bot API first** (free, no approval, ships in a day). **WhatsApp Cloud API second**: needs Meta business verification and a dedicated number. Service replies are free up to 1,000/month per number, then ₹0.115 each. Use Meta's Cloud API directly rather than a BSP to avoid markup.

---

## 8. Cost tracking and unit economics

**Assumption:** ₹88 = $1 (update monthly). Sarvam prices exclude GST.

### Per-query cost model (text, Hindi, ~4,000 input / 500 output tokens)
| Step | Sarvam-105B path | Claude Haiku 4.5 (in.) path |
|---|---|---|
| LID (150 chars) | ₹0.0005 | ₹0.0005 |
| Query rewrite (300 in / 100 out) | ~₹0.011 | ~₹0.08 |
| Query embedding (Cohere v3) | ~₹0.0005 | ~₹0.0005 |
| Rerank (self-hosted) | ~₹0 marginal | ~₹0 marginal |
| Generation | ₹0.06 + ₹0.03 = **₹0.09** | $0.0044 + $0.00275 ≈ **₹0.63** |
| **Model subtotal** | **≈ ₹0.10** | **≈ ₹0.71** |
| + WhatsApp (2 msgs beyond free tier) | +₹0.23 | +₹0.23 |
| + Voice (30 s STT + 800-char TTS v4 Flash) | +₹0.25 + ₹0.80 | same |

**Insight to state in interviews:** model inference is *not* the dominant cost on the Sarvam path. Messaging and voice dominate, and translation APIs (₹2/1,000 chars) can quietly cost more than generation. That is why answers are generated natively and queries are rewritten by LLM.

**Fixed floor (portfolio):** Aurora at 0–0.5 ACU (~$0–44/mo), one small Fargate task part-time, CloudWatch, Route 53, S3. Budget **≈ ₹3,000–6,000/month** while demoing. Scale Fargate to 0 when idle. One-time costs: OCR ≈ ₹1,500 and corpus embedding < ₹100. Sarvam's ₹100 signup credit covers early dev.

**Cost dashboard design:** a `cost_log` row per pipeline step `{query_id, step, provider, model, units, unit_type, unit_price_inr, cost_inr, latency_ms}`. A view aggregates ₹/query, ₹/active user, ₹ by step/provider/language, and p95 latency. Render it in a simple Streamlit or Grafana page (Postgres datasource). Add a daily CloudWatch alarm on spend anomalies.

### Freemium and B2B pricing hypotheses (to test, not facts)
| Tier | Limits | Price hypothesis |
|---|---|---|
| Free (citizen) | 15 text questions/month, citations, escalation links | ₹0 (≈ ₹2–5/user/month cost) |
| Saathi Plus | 100 questions, voice, rent-agreement/notice explainer upload | ₹49–99/month |
| NGO / legal-aid clinic | Volunteer seats, case log, checklist PDF export, analytics, Hindi/Marathi | ₹1,999–4,999/org/month; **free pilot for first 3 NGOs** |
| CA / law office | Labour-code + state-rules compliance assistant for their own staff/clients, change alerts | ₹2,999/seat/month |

---

## 9. Business model and go-to-market
- **Citizen freemium** is the acquisition channel and data engine (questions improve the golden set). It won't pay the bills alone because willingness to pay is low and Nyaya Setu is free.
- **B2B is the revenue path:** (a) **legal-aid NGOs and law-college clinics**, where Niyam Saathi is a volunteer co-pilot plus intake log plus impact reporting (funders love metrics); (b) **CA firms / HR consultants** advising MSMEs on labour-code transition, with a "what changed this week in Central/MP rules" alert feed. Rule 36 compliant: software licences only, with no lawyer listing, referral or lead routing.
- **GTM sequence:** Jabalpur NGOs and the law-college legal-aid cell (Dec) → MP CA networks (ICAI Jabalpur branch events) → Maharashtra + Marathi (Q1 2027). Publish the eval report and a monthly "MP law changes" Hindi digest as content marketing.

---

## 10. Week-by-week roadmap (8–10 h/day)

| Week | Dates | Build | Definition of done |
|---|---|---|---|
| W0 | 5–9 Nov | Validation posts in 3 groups; repo + Terraform skeleton; download corpus items 1–13; `section_uid` scheme | ≥15 real questions logged; corpus in S3 with checksums |
| W1 | 10–16 Nov | Parser + clause chunker (EN+HI); OCR benchmark (Sarvam vs Tesseract); pgvector + bm25s hybrid; deterministic retrieval eval | Recall@10 reported on first 50 golden rows; chunk viewer works |
| W2 | 17–23 Nov | Generation with JSON citations + validator + abstention; Sarvam vs Haiku A/B; Ragas/DeepEval harness; judge calibration; Telegram bot; golden set to **120 frozen v1.0** | All gates computed per slice; CI smoke job green; κ reported |
| W3 | 24–30 Nov | AWS deploy (Fargate, Aurora, API GW, Lambda, Secrets, OTel); cost_log + dashboard; law-watch job; README, architecture diagram, **eval report**, 3-min demo video; 2 mock system-design interviews | Public demo bot + dashboard URL; p95 and ₹/query published; **interview-ready** |
| W4–5 | Dec | WhatsApp Cloud API; voice (Saaras/Bulbul); Marathi slice; NGO pilot console (Cognito) | 1 NGO pilot live; Marathi eval slice ≥ gates |
| W6–9 | Jan | Maharashtra corpus; rent-agreement explainer; B2B change-alert feed | 2 paying/pilot B2B users |
| By May 2027 | — | DPDP full compliance (notice, retention, breach runbook, grievance) | Compliance checklist signed off before 13 May 2027 |

**Cut-line if behind:** drop voice, WhatsApp and Marathi from November. Never drop the eval report or citation validator.

---

## 11. Portfolio and interview angle

**Show:** (1) the architecture diagram above, polished; (2) an eval report with slice tables, the embedding/reranker/LLM A/B and the κ calibration; (3) a cost dashboard screenshot with ₹/query by step; (4) a demo video with one Hindi tenancy question, one RTI question showing the "sub-judice" caveat, and one correct refusal; (5) an ADR folder (why pgvector over OpenSearch, why self-hosted rerank, why native-language generation).

**Questions this prepares you for:**
- Design a multilingual RAG for 10M users: sharding, caching (semantic cache keyed by `section_uid` set), and model routing under rate limits (Sarvam 60 req/min).
- How do you prevent hallucinated citations? (Validator + exact-quote match + abstention.)
- Hybrid vs dense retrieval; RRF vs weighted fusion; when reranking pays for itself.
- How do you evaluate without ground truth, and how do you trust an LLM judge? (Calibration, κ.)
- How do you handle a law change? (Versioned corpus, valid_from/to filters, regression rows.)
- Data residency on AWS India (geo vs global inference profiles; rerank region gap).
- Cost modelling and guardrails; what dominates unit cost and why.
- Chunking legal text; parent-child retrieval; cross-lingual retrieval failure modes.

---

## 12. Risks and mitigations

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| Law changes (MP labour rules finalised, MP tenancy bill revived, SC ruling on s.44(3)) | High / High | Weekly law-watch diffing; status flags; "law as of" stamp; regression rows per change |
| Hallucinated or wrong citations | Medium / Critical | Exact-quote validator; abstain on failure; citation precision gate = release blocker |
| OCR errors in Hindi gazettes | Medium / High | Prefer born-digital; CER benchmark; human spot-check of every OCR'd section that gets cited |
| State variation confusion (MTA vs MP law) | High / High | State detection + filter; `must_not_include` tests; ask a clarifying "which state?" when unknown |
| Liability / unauthorised-practice perception | Medium / High | Information-only scope, advice-intent refusal, disclaimers, statutory-aid escalation, no lawyer marketplace (Rule 36) |
| DPDP non-compliance | Low now / High from 13 May 2027 | Minimise, redact, 90-day retention, consent records, breach runbook |
| Cost spikes (voice, WhatsApp, translation, abuse) | Medium / Medium | Per-user quotas, budgets, cached answers, native-language generation, Sarvam 402 fallback |
| Provider limits/outages (Sarvam rate limits, price changes) | Medium / Medium | Multi-provider router (Sarvam ↔ Bedrock), retries with backoff |
| Low validation response | Medium / Medium | Legal-aid clinics, NGO FAQ mining, capped synthetic rows (≤30%) clearly flagged |
| Nyaya Setu improves and absorbs the use case | Medium / Medium | Specialise (state depth, NGO workflow, eval transparency); position as complementary |

---

## Caveats
- **MP tenancy law status needs a lawyer's confirmation.** A 2012 report says the "Madhya Pradesh Tenants Act 2010" (Parisar Kirayedari Adhiniyam) received Presidential assent. Current guides and the Rent Controlling Authority framework still centre on the 1961 Accommodation Control Act. Ingest both and have a practising MP advocate confirm which provisions govern before you publish tenancy answers.
- **MTA adoption lists conflict** even between Rajya Sabha replies: the 25 Jul 2022 reply (AP, TN, UP, Assam) differs from the later reply reported by DT Next (Assam, Arunachal, A&N, DNH&DD, Lakshadweep). Cite the most recent MoHUA/Parliament answer and date it.
- **MP labour codes:** I confirmed the 5 Jan 2026 drafts. I could not confirm a final MP gazette notification of rules. A Hindi media report of an MP "labour code" bill passed in July 2026 is unverified as to content.
- **Bedrock India-profile Claude prices** are derived from Anthropic's published global prices plus its stated 10% regional premium. AWS's own table didn't render, and Mumbai may carry an uplift (other providers show ~18–20%). Confirm in the AWS Pricing Calculator.
- **Sarvam pricing moved repeatedly in 2026.** The official sarvam.ai/api-pricing page lists Sarvam 105B at ₹15/₹5/₹60 per 1M tokens (input/cached/output). UsagePricing.com dates that cut to 15 Oct 2026, down from ₹29.28/₹10.98/₹73.2; Mindcat.ai puts it at 10 Oct. Other third-party pages still quote older rates (e.g., ₹4/₹16). Trust docs.sarvam.ai and re-check monthly.
- Infrastructure floors in INR are estimates. Aurora rates cited are US list prices, and Mumbai rates differ slightly.
- Pricing tiers and B2B prices are hypotheses to validate with NGO/CA interviews, not market data.
