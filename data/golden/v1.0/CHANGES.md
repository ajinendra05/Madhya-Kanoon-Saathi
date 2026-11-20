# Golden set v1.0 (frozen 2026-11-19)

- source: `data/golden/v0.1-seed/golden_set_v0.1_seed.jsonl` (seed, DEC-063); reviewed and verified by Malik on 2026-11-19
- rows: 130 · sha256 of `golden_set_v1.0.jsonl`: `386f40b8d2e95d06483bc78a51c43b63b4038fcab8ede21ef9b1953dbd63447a`
- protected: never edit; corrections go into a new version (eval rules)

## Corrections applied at freeze (only those required by decisions or verified findings)

- **GS-028**: DEC-050: current official wage rates may be stated with the qualification; the 67 scheduled employments are Schedule A Part B (sch_a_ba, DEC-073)
  - `expected_behavior`: `"gated"` → `"answer_with_caveat"`
  - `gates`: `["L7"]` → `[]`
  - `expected_clauses`: `[{"act_id": "MP.MWVDAOCT2026", "section_uid": null, "confidence": "medium", "version_as_of": "2026-11-12", "needs_verification": true}]` → `[{"act_id": "MP.MWVDAOCT2026", "section_uid": "MP.MWVDAOCT2026:sch_a_ba", "confidence": "high", "version_as_of": "2026-11-19", "needs_verification": false}]`
- **GS-058**: S31: charging above the price displayed on the goods is a ground of complaint in CPA s.2(6)(iv) (chunk IN.CPA2019:s2:ss6 text checked 2026-11-18), not s.2(47)
  - `expected_clauses`: `[{"act_id": "IN.CPA2019", "section_uid": "IN.CPA2019:s2:ss47", "confidence": "medium", "version_as_of": "2026-11-12", "needs_verification": true}]` → `[{"act_id": "IN.CPA2019", "section_uid": "IN.CPA2019:s2:ss6", "confidence": "high", "version_as_of": "2026-11-19", "needs_verification": false}]`
- **GS-121**: DEC-070: mutation moved to December, MPLRC s.109-110 and Mutation Rules gated (G8a)
  - `expected_behavior`: `"answer_with_caveat"` → `"abstain_refer"`
  - `answerability`: `"partial"` → `"none"`
  - `unanswerable_reason`: `null` → `"out_of_corpus"`
- **GS-122**: DEC-070: mutation moved to December, MPLRC s.109-110 and Mutation Rules gated (G8a)
  - `expected_behavior`: `"answer_with_caveat"` → `"abstain_refer"`
  - `answerability`: `"partial"` → `"none"`
  - `unanswerable_reason`: `null` → `"out_of_corpus"`
- **GS-123**: DEC-070: mutation moved to December, MPLRC s.109-110 and Mutation Rules gated (G8a)
  - `expected_behavior`: `"answer_with_caveat"` → `"abstain_refer"`
  - `answerability`: `"partial"` → `"none"`
  - `unanswerable_reason`: `null` → `"out_of_corpus"`
