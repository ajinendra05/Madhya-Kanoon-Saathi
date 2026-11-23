# Retrieval before/after DEC-090 optimisations: golden v1.0, 2026-11-23

Strict matching (DEC-065), laptop i5-1155G7. `time` = rewrite + search + rerank per question.

| config | slice | n | R@6 | R@10 | MRR@10 | time mean s | time p95 s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 50 | 0.583 | 0.603 | 0.490 | 12.73 | 20.52 |
| baseline | hi | 21 | 0.460 | 0.484 | 0.488 | 13.14 | 22.07 |
| baseline | hinglish | 9 | 0.444 | 0.444 | 0.315 | 13.42 | 18.98 |
| baseline | en | 20 | 0.775 | 0.800 | 0.571 | 11.98 | 17.06 |
| optimised_no_rw | all | 50 | 0.603 | 0.623 | 0.470 | 10.24 | 17.73 |
| optimised_no_rw | hi | 21 | 0.508 | 0.532 | 0.472 | 10.96 | 20.35 |
| optimised_no_rw | hinglish | 9 | 0.444 | 0.444 | 0.315 | 10.36 | 11.26 |
| optimised_no_rw | en | 20 | 0.775 | 0.800 | 0.537 | 9.44 | 11.11 |
| optimised | all | 50 | 0.713 | 0.740 | 0.503 | 15.31 | 27.74 |
| optimised | hi | 21 | 0.627 | 0.643 | 0.415 | 17.49 | 35.91 |
| optimised | hinglish | 9 | 0.722 | 0.722 | 0.574 | 16.51 | 21.91 |
| optimised | en | 20 | 0.800 | 0.850 | 0.563 | 12.49 | 14.83 |
