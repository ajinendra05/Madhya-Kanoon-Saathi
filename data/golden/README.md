# Golden set

The evaluation questions for Madhya Kanoon Saathi (plan §7, DEC-063). Rules: `.claude/rules/eval.md`.
Frozen versions (`v1.0` and later) are never edited; a change makes a new version.

## v0.1-seed (synthetic, unverified)

130 questions written to bootstrap evaluation **before** real user questions arrive: Malik's 120-row seed
(2026-11-12) with the DEC-063 fixes, plus 10 land-procedure rows (DEC-038). Every row is `source: synthetic` and
`review_status: draft_unverified`. **Nothing here is a verified legal fact.**

### Files
- `v0.1-seed/golden_set_v0.1_seed.jsonl`: the set, one JSON object per line.
- `v0.1-seed/golden_set_v0.1_seed_review.csv`: flat copy for review in a spreadsheet.
- `v0.1-seed/coverage.md`: what the current corpus can answer (from `scripts/check_golden.py --write`).
- Generator: `scripts/build_golden_seed.py`. **Edit rows there, never in the outputs**, then run
  `uv run python scripts/build_golden_seed.py` and `uv run python scripts/check_golden.py --write`.

### Composition
| Domain | Rows | | Behaviour | Rows |
|---|---|---|---|---|
| Tenancy | 24 | | answer | 59 |
| Labour | 24 | | answer_with_caveat | 46 |
| Consumer | 20 | | abstain_refer | 16 |
| RTI | 18 | | crisis_route | 5 |
| Public services | 12 | | gated | 2 |
| Land procedure | 10 | | ask_clarifying | 2 |
| Legal aid | 8 | | | |
| Schemes | 6 | | | |
| Crisis / status | 8 | | | |

Languages: Hindi 56, English 55, Hinglish 19 (DEC-016: no Marathi). Channel: Telegram (DEC-007).
Should-abstain share (abstain + crisis + gated + clarify) = 25 / 130 = 19%. Push it past 20% when real questions
are added.

### Fields beyond the plan's schema
- `expected_behavior`: what the bot must do.
  - `answer`: answer with citations.
  - `answer_with_caveat`: answer, but state a status or uncertainty (draft, not commenced, under challenge,
    unverified figure, legal qualification as in DEC-050).
  - `abstain_refer`: decline the substance and point to the escalation route (statutory free legal aid, never
    private lawyers).
  - `ask_clarifying`: ask one question first (e.g. central vs MP office).
  - `crisis_route`: helplines first (from `contacts.yaml`), no legal text.
  - `gated`: behaviour follows the current decision on the gate in `gates` (e.g. L7 wages, now DEC-050).
- `gates`: open items the row depends on (L7, G6, G8, G12, G13, G14; see `docs/OPEN_QUESTIONS.md`).
- `incident_date`: set when the event happened before a law changed (temporal tests).
- `expected_clauses[]`: `act_id`, `section_uid` (`null` = act is right, section still to find), `confidence`,
  `needs_verification`. Eval matches with `covers()` (DEC-040), never string prefixes.
- `must_include` / `must_not_include`: case-insensitive regexes; `a|b` accepts either form (Hindi vs digits).

### Review workflow (to freeze v1.0)
1. For each row, open the cited provision in the **ingested official text** and correct `expected_clauses`
   (fill `section_uid`, set `needs_verification: false`).
2. Fix `key_facts` to match the text; delete any fact you can't find.
3. Write `reference_answer_hi` / `reference_answer_en` (left empty on purpose so no draft answer is treated as truth).
4. Set `verified_by`, `verified_on`, `review_status: verified`.
5. Have a law student double-label at least 30 rows; report agreement on `answerability` and `expected_clauses`.
6. As real Telegram questions come in, add them redacted (DEC-036) as `source: telegram` and retire synthetic rows
   so synthetic ≤ 30% of v1.0.

### Rows to re-check before the demo
Status traps that can change any day (from Malik's seed notes, not verified):
- UCC assent: GS-116
- OBC 27% SLP: GS-103
- Shram Shakti Sanhita commencement: GS-033, GS-039
- wage gate L7: GS-028, GS-047
- MGNREGA → VB-G RAM G: GS-109
- land rows (GS-121 to GS-130): G8, deadline 16 Nov 2026 (DEC-045)
