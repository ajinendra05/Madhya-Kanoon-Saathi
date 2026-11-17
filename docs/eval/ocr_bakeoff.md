# W0.5 OCR bake-off results

Pages scored: 20 (corrected ground truth only).
Mean per-page error rates in %, lower is better. raw = whitespace-collapsed NFC;
norm = shared normaliser (nukta folded, invisible characters removed).
Produced by `scripts/ocr_score.py score`.

| Slice | Engine | Pages | CER raw | CER norm | WER raw | WER norm |
| --- | --- | --- | --- | --- | --- | --- |
| all | tesseract | 20 | 17.7 | 17.7 | 33.0 | 32.8 |
| all | bodhan | 20 | 13.7 | 13.6 | 21.3 | 21.2 |
| kind=degraded_scan | tesseract | 2 | 34.9 | 34.9 | 57.0 | 56.9 |
| kind=degraded_scan | bodhan | 2 | 3.3 | 3.3 | 7.0 | 7.0 |
| kind=english_scan | tesseract | 2 | 3.7 | 3.7 | 6.6 | 6.6 |
| kind=english_scan | bodhan | 2 | 7.2 | 7.2 | 7.3 | 7.3 |
| kind=gazette_notice | tesseract | 3 | 10.0 | 10.0 | 27.7 | 27.5 |
| kind=gazette_notice | bodhan | 3 | 6.2 | 6.2 | 22.8 | 22.8 |
| kind=hindi_act | tesseract | 7 | 6.2 | 6.1 | 15.8 | 15.5 |
| kind=hindi_act | bodhan | 7 | 2.5 | 2.5 | 6.2 | 6.2 |
| kind=hindi_form | tesseract | 1 | 12.9 | 12.9 | 16.7 | 16.7 |
| kind=hindi_form | bodhan | 1 | 3.5 | 3.5 | 11.2 | 11.2 |
| kind=wage_table | tesseract | 5 | 38.2 | 38.1 | 64.6 | 64.2 |
| kind=wage_table | bodhan | 5 | 42.5 | 42.4 | 55.0 | 54.5 |
| lang=en | tesseract | 3 | 5.8 | 5.8 | 13.1 | 13.1 |
| lang=en | bodhan | 3 | 5.2 | 5.2 | 5.5 | 5.5 |
| lang=hi | tesseract | 17 | 19.8 | 19.8 | 36.6 | 36.3 |
| lang=hi | bodhan | 17 | 15.2 | 15.1 | 24.1 | 24.0 |

## Per page (CER norm %)

| Page | Kind | Lang | tesseract | bodhan | sarvam |
| --- | --- | --- | --- | --- | --- |
| p01 | hindi_act | hi | 4.6 | 3.6 | - |
| p02 | hindi_act | hi | 8.5 | 6.7 | - |
| p03 | hindi_act | hi | 7.5 | 0.2 | - |
| p04 | hindi_act | hi | 8.2 | 0.7 | - |
| p05 | hindi_act | hi | 5.8 | 1.0 | - |
| p06 | hindi_form | hi | 12.9 | 3.5 | - |
| p07 | hindi_act | hi | 4.4 | 3.3 | - |
| p08 | hindi_act | hi | 3.7 | 2.1 | - |
| p09 | wage_table | hi | 13.2 | 13.3 | - |
| p10 | wage_table | hi | 24.0 | 15.3 | - |
| p11 | wage_table | hi | 20.5 | 12.6 | - |
| p12 | wage_table | hi | 66.7 | 130.7 | - |
| p13 | wage_table | hi | 66.2 | 40.3 | - |
| p14 | degraded_scan | hi | 59.7 | 5.5 | - |
| p15 | gazette_notice | hi | 9.2 | 5.7 | - |
| p16 | gazette_notice | hi | 8.3 | 5.5 | - |
| p17 | gazette_notice | hi | 12.4 | 7.4 | - |
| p18 | english_scan | en | 1.0 | 0.0 | - |
| p19 | degraded_scan | en | 10.2 | 1.0 | - |
| p20 | english_scan | en | 6.4 | 14.5 | - |
