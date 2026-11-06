# Spec: corpus manifest (DEC-011, DEC-033, DEC-037, DEC-040)

File: `data/corpus_manifest.json` (committed). Code: `src/madhya_kanoon_saathi/ingestion/manifest.py`
(stdlib validator that reports **every** error at once). Tests: `tests/unit/test_manifest.py`.

```json
{"schema_version": 1, "instruments": [ ... ], "documents": [ ... ]}
```
Unknown fields are errors (typos can't slip through). Dates are `YYYY-MM-DD`; `fetched_at` is ISO-8601 with a
timezone offset.

## `instruments`: one row per law, rule set, notification or guide
| Field | Req. | Notes |
| --- | --- | --- |
| `instrument_id` | yes | `IN.RTI2005` style; prefix must equal `jurisdiction` |
| `type` | yes | `act · ordinance · rules · regulations · notification · order · scheme_guideline · official_guide · bill` (`ordinance` added by DEC-044) |
| `jurisdiction` | yes | `IN` or `MP` |
| `title_en` / `title_hi` | one of | official titles |
| `parent_instrument` | – | e.g. rules → their Act; must exist in the manifest |
| `made_under` | – | section_uids of the parent that give the rule-making power; needs `parent_instrument` |
| `enacted_on`, `commenced_on` | – | enacted ≠ commenced; `commenced_on ≥ enacted_on` |
| `commencement_overrides` | – | `[{uid, commenced_on}]` for provisions that started on a different date |
| `amendments` | – | `[{by: instrument_id, commenced_on, affects: [uids of this instrument]}]` |
| `supersedes` / `superseded_by` | – | instrument ids in the manifest |
| `amends` | – | instrument ids this instrument changes (DEC-044); each amending law is its own instrument; targets may be outside the corpus; not itself |
| `notes` | – | |

**Derived (never stored):** `authority_rank` (act / ordinance 1 · rules/regulations 2 · notification/order 3 ·
scheme_guideline 4 · official_guide 5 · bill 6) and `binding` (true for act, ordinance, rules, regulations, notification,
order). Rank is **not** a retrieval weight; notifications often hold the facts users ask for (amounts, fees). It
is used for the law-beats-guide conflict flag and the rule that rights claims cite binding law (answer wording:
W2.1 decision). Scheme guidelines are non-binding here but are the primary source for scheme eligibility.

## `documents`: one row per downloaded file
| Field | Req. | Notes |
| --- | --- | --- |
| `doc_id` | yes | `<instrument_id>@<lang>@<n>`; must start with `<instrument_id>@` |
| `instrument_id` | yes | must exist |
| `language` | yes | `hi · en · bi` (`bi` = one bilingual gazette file) |
| `status` | yes | `in_force · draft · model_law · repealed · sub_judice_flag · passed_awaiting_assent · proposal · enacted_not_commenced` (last added by DEC-044: assented + published, commencement not yet notified; never current; invalid once the instrument has `commenced_on`) |
| `mode` | yes | `index · gated · archive · guide` (DEC-037) |
| `gate` | if gated | OPEN_QUESTIONS IDs (`L4`, `G12`); only allowed with `mode=gated` |
| `valid_from`, `valid_to`, `expires_on` | – | `valid_to`/`expires_on` not before `valid_from` |
| `source_url` | yes | official http(s) source (never an aggregator) |
| `publisher` | yes | |
| `fetched_at` | yes | with timezone |
| `sha256` | yes | 64 lowercase hex; law-watch compares against it |
| `bytes` | yes | > 0 |
| `content_type` | yes | |
| `gazette_ref`, `notification_no` | – | |
| `text_layer` | yes | `born_digital · scanned · mixed`. "scanned" = no *usable* text: for `hi` pages ≥ 50% of letters must be Devanagari (`bi` ≥ 20%), else a bad embedded OCR layer counts as no text |
| `ocr_engine` | – | must be empty for `born_digital` |
| `local_path` | – | relative to `MKS_DATA_DIR` (e.g. `raw/x.pdf`) |
| `s3_path` | – | `s3://…` (prod, DEC-011) |
| `applies_to` | yes | `{level, states, districts, areas, note}`; see below |
| `applies_to_overrides` | – | `[{uid, applies_to}]` per provision (e.g. MP-only amendment) |
| `verifications` | – | list of verification records; see below |
| `last_checked_on` | – | written by law-watch (DEC-013); "re-checked", not "verified" |
| `supersedes` / `superseded_by` | – | doc ids in the manifest |
| `notes` | – | |

### Applicability
- `level`: `national · state · district · area`. `national` takes no lists; the others need `states`; `district`
  needs `districts` (LGD codes, TODO(verify)); `area` needs `areas`.
- An `MP` instrument can't be `national`, and its `states` must include `MP`.
- **Enforced now:** state level (jurisdiction guard). **Stored only:** districts/areas.
- Who a law covers (e.g. "establishments with N+ workers") is legal content and stays in the text.

### Verification records
`{what, by, on, method, evidence, result, note}`
- `what`: `status · commencement · validity · text_matches_source · consolidation_current · interpretation`
- `by`: `claude · malik · advocate`. `interpretation` must be `malik` or `advocate`.
- `result`: `confirmed · conflict · unclear`. `evidence` = official URL or file + page.

### Gates enforced by the validator
- **Index gate:** `mode=index` needs `confirmed` records for both `status` and `commencement`, and no `conflict`.
- `mode=guide` only for `official_guide` / `scheme_guideline`; official guides can't be `index`.

### Sources file and the downloader (DEC-041)
`data/corpus_sources.json` = `{"schema_version": 1, "sources": [...]}`; each row has `doc_id, instrument_id, url,
language, status, publisher, applies_to, target_mode, gate` plus optional `resolver` (`direct` default, or
`mp_labour_dms` for the MP Labour DMS two-hop download) and `gazette_ref, notification_no, valid_from,
valid_to, expires_on, notes`. `scripts/fetch_corpus.py` fills `fetched_at, sha256, bytes, content_type,
text_layer, local_path` and writes the row with **`mode=archive`** (note `[pending: target_mode=…]`). Promotion to
`index`/`gated`/`guide` is a manual edit made together with the verification records. Changed bytes on re-fetch are
saved as `*.new` and never applied automatically.

### Computed, never stored
`Document.is_current(on)`: `status == in_force` and `on` inside `valid_from` … `valid_to` and not after `expires_on`.
Retrieval filters on this at query time.
