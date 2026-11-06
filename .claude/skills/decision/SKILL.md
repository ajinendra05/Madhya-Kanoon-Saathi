---
name: decision
description: Draft a major decision for Malik in the project's decision format (context, options A/B/C with trade-offs, cost and time, recommendation), wait for the choice, then record it as the next DEC entry in docs/DECISIONS.md. Use whenever a decision is "major" under CLAUDE.md's decision protocol.
argument-hint: "[topic of the decision]"
---

# Decision

Format: https://code.claude.com/docs/en/skills, checked 2026-11-06.

Topic: $ARGUMENTS

## 1. Prepare (no edits yet)
- Read the relevant parts of `docs/DECISIONS.md` (check that no existing DEC already covers this, and find the next number) and `docs/plan.md` / `docs/CORPUS.md` if they touch the topic.
- Verify facts the options depend on (prices, limits, API behaviour) against official docs. Anything unverified is labelled **(not verified)**. Never present a remembered price as fact.

## 2. Present it to Malik in exactly this shape
**Decision needed:** one line.

**Context:** 2–3 lines, plain English: why this needs deciding now and what it blocks.

| Option | What it means | Efficiency | Accuracy | Application | Cost (₹) | Time |
| --- | --- | --- | --- | --- | --- | --- |
| A | … | … | … | … | … | … |
| B | … | … | … | … | … | … |
| C | … | … | … | … | … | … |

**Recommendation:** the option + a 2–3 line plain-English "why" (it doubles as an interview answer).

Then **stop and wait** for Malik's choice. Don't implement anything that depends on it.

## 3. After Malik decides
Append to `docs/DECISIONS.md`, above "Pending decisions" (Malik approves this edit by prompt):

```
## DEC-NNN — <title>
- Date: YYYY-MM-DD | Status: accepted | Approved by: Malik
- Context: …
- Options: A) … · B) … · C) …
- Decision: …
- Why: …
- Effects: efficiency · accuracy · application · cost
- Follow-ups: verification items, related DECs (Supersedes DEC-xxx if it replaces one)
```

- If it replaces an older decision, add a new entry that says `Supersedes DEC-xxx`. Don't rewrite the old one.
- Update the "Pending decisions" table (remove it if resolved, or add it if deferred).
- Update the affected docs: `PROGRESS.md` (new or changed items), `OPEN_QUESTIONS.md` (new verifications), `CONCEPTS.md` / `TOOLS.md` / `CORPUS.md` (new concepts, tools, corpus scope; CORPUS edits also need Malik's approval).
- Confirm to Malik in one or two lines: the DEC number and which files changed.
