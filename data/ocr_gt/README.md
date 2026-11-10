# OCR ground truth (W0.5 bake-off, DEC-014 / DEC-053)

Hand-corrected text of 20 scanned pages, used to score OCR engines (CER/WER). Public law text only.

- `pages.json`: the page set (`page_id`, `doc_id`, 1-based `page`, `kind`, `lang`, `why`) and `gt_status` per page
  (`draft` = pre-filled from Tesseract, not yet corrected; `corrected` = fully checked by Malik).
- `<page_id>.txt`: the ground truth for that page, UTF-8.

## How to correct a page (Malik)
Open the page image (`data/ocr/pages/<page_id>.png`) next to `<page_id>.txt` and fix the text until it matches the
page exactly. Then set that page's `gt_status` to `corrected` in `pages.json`.

**Conventions** (all engines are converted to the same plain-text form before scoring):
1. Type what is printed, in reading order: header line, body, footer, page number. Columns left to right.
2. Keep the original script and spelling, including printer errors. Do not translate or "fix" the law.
3. Digits as printed (Devanagari `१२` stays `१२`, ASCII `12` stays `12`).
4. Tables: one table row per line; cells separated by a single space; no `|` characters. Skip ruling lines.
5. Line breaks and extra spaces do not matter for scoring; text order does.
6. Handwriting, stamps, signatures and scanner marks (e.g. "Scanned with OKEN Scanner"): leave out.
   Printed but illegible text: type your best reading and mark the word `[?]`, e.g. `धारा[?]`.
7. Blank form fields (`........`): keep the dots as printed.

Uncorrected pre-fill leftovers can only favour Tesseract, the baseline (DEC-053 item 6).
