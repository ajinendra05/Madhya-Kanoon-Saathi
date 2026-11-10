# Spec: chunks, extraction QA and the build record (DEC-055)

Code: `src/madhya_kanoon_saathi/ingestion/{pdf_text,structure,chunker}.py`, `scripts/build_chunks.py`
Output: `data/parsed/chunks.jsonl` (git-ignored) · committed record: `data/parsed_manifest/{build_manifest.json,qa_report.md}`

## What a chunk is
One citable unit of one language version of one provision:
- the **sub-section**, with its provisos and explanations attached;
- a section **without** sub-sections is one chunk;
- chunks never span two sections;
- a unit longer than 450 estimated tokens is split at clause boundaries; each piece gets its own deeper
  `section_uid` (e.g. `…:ss1:cl_j`). Only a single clause that is still too long is cut into pieces that share its
  uid and get a `~n` suffix on `chunk_id` (DEC-055 item 3);
- the section heading line (e.g. "8. Exemption from disclosure of information.—") belongs to the first chunk of
  the section; every chunk also carries it in `heading`.

Guides and scheme guidelines use the same shape with their own numbering (`para<n>`), and HTML guides chunk by
question or heading.

## Fields (one JSON object per line)
| Field | Type | Notes |
| --- | --- | --- |
| `chunk_id` | str | `<section_uid>@<lang>@<version>[~n]` (`docs/specs/section_uid.md`); unique in a build |
| `section_uid` | str | language-independent provision identity (DEC-055 7b); valid per `section_uid.parse` |
| `parent_uid` | str or null | `section_uid.parent()`, written at build time |
| `instrument_id`, `doc_id` | str | from the manifest |
| `jurisdiction` | `IN` or `MP` | from the instrument (DEC-055 7c) |
| `lang` | `en` or `hi` | language of this chunk's text (a `bi` document yields chunks in both) |
| `version` | str | the version part of `chunk_id`: ISO date or `nd-<sha8>` |
| `version_source` | str | `valid_from`, `commencement_override`, `commenced_on`, `enacted_on` or `doc_sha256` (DEC-055 7d) |
| `text` | str | **canonical** text: `normalize(fold_nukta=False)` (DEC-054), footnote numerals removed, square brackets kept, line-wraps joined, paragraph breaks kept as `\n` |
| `raw_text` | str | the extractor's text for the same span, unchanged except page headers/footers removed (DEC-055 7a) |
| `heading` | str | the section heading (marginal note), canonical form |
| `path` | list[str] | e.g. `["CHAPTER II — RIGHT TO INFORMATION AND OBLIGATIONS OF PUBLIC AUTHORITIES", "8. Exemption from disclosure of information"]` |
| `footnotes` | list[{`n`, `text`}] | amendment footnotes whose markers fall inside this chunk, canonical form |
| `locator` | object | `{"kind": "pdf_page", "pages": [first, last]}` (1-based PDF page numbers) or `{"kind": "html", "url", "selector", "heading_path"}` |
| `source_url`, `doc_sha256` | str | from the manifest document |
| `extraction` | str | `pdfium-<version>` for born-digital PDFs, `html` for HTML, `ocr:<engine>@<revision>` for OCR |
| `status`, `doc_type` | str | document status; instrument type |
| `valid_from`, `valid_to`, `expires_on` | str or null | from the manifest document |
| `applies_to` | object | manifest `applies_to` (with per-provision override when one matches) |
| `token_estimate` | int | **estimate** until W1.4: `ceil(1.35 × words)` for `en`, `ceil(2.0 × words)` for `hi`; recalibrated with the BGE-M3 tokenizer |

Not stored (computed, DEC-040): `binding`, `authority_rank`, `is_current`.

**Raw ↔ canonical check:** `canonicalise(raw_text) == text` must hold for every chunk, using the same function
the build used. This is how an auditor maps a quote back to the extractor output.

## Version part of `chunk_id` (DEC-055 7d)
`valid_from` of the document → the provision's `commencement_overrides` entry → instrument `commenced_on` →
instrument `enacted_on` → `nd-` + first 8 hex of the document sha256. Never the fetch date.
`version_source` records which one was used.

## Extraction QA (DEC-055 7e)
**Hard failures (the build stops, nothing is written):**
- invalid `section_uid`, or a uid that does not belong to the document's instrument;
- a chunk outside the document's `index_scope` (DEC-051);
- missing locator (no page numbers / no HTML selector);
- `canonicalise(raw_text) != text`;
- duplicate `chunk_id`.

**Warnings (reported in `qa_report.md`, build continues):**
- `token_estimate` outside 150–450;
- suspected split words (e.g. `\b\w{1,3} \w+ion\b`, "sub -section", "( 1)");
- gaps in section numbering (e.g. 7 → 9) not explained by an omission footnote;
- pages with little text (fewer than 200 characters on a non-blank page);
- text on a page that was not assigned to any chunk (front matter and contents pages are expected and listed).

## Build record (committed, DEC-055 7e)
`data/parsed_manifest/build_manifest.json`:
`{built_at, git_commit, git_dirty, python, libraries {pypdfium2, ...}, normaliser_version, chunker_version,
inputs [{doc_id, sha256, local_path}], output {path, sha256, chunks, by_doc}, qa {errors, warnings}}`.
`data/parsed_manifest/qa_report.md`: per document counts, warnings and unassigned text.

## Extraction notes (India Code PDFs, observed 2026-11-10)
- pypdfium2 gives clean words where pypdf splits them (DEC-055 item 1).
- Body text is ~11 pt, footnotes ~9 pt: lines are classed by font size, not by pattern.
- The first line of each page is the page number (removed as header).
- Pages before the enactment line (`[15th June, 2005.]`) are title and contents: not chunked, listed in the QA report.
