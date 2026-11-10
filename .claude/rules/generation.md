---
paths:
  - "src/madhya_kanoon_saathi/generation/**"
  - "src/madhya_kanoon_saathi/bot/**"
  - "data/contacts.yaml"
---

# Generation and bot rules

- Anything that changes what the bot tells users about the law — prompts, disclaimers, refusal/abstention rules,
  escalation text — is a major decision. Propose, don't just edit.
- Output contract: `{answer_blocks:[{text, citations:[{chunk_id, quote}]}], abstain, abstain_reason, escalation}`.
- Validator: `chunk_id` must be in the retrieved context; `quote` must be an exact substring after `normalize()` (NFC + nukta folding) of both sides (DEC-054).
  Retry once → strip unsupported claims → abstain if none remain. Never weaken this to make tests pass.
- Draft / model_law / sub_judice instruments: answer with an explicit caveat, not a refusal.
- Every reply: citations, "Law as of <date>", status caveats, "not legal advice" footer, in the user's language.
- Escalate only to statutory free legal aid from `contacts.yaml` (DEC-018). Never name or recommend private lawyers.
- Model IDs are config, not literals; Bedrock IDs stay `TODO(verify)` until checked (DEC-006).
- Tests never hit paid APIs unless marked `@pytest.mark.paid`; use recorded fixtures.
- Log no PII: redact before any log, trace or DynamoDB write.
- Crisis router runs before retrieval on every message; crisis-trigger recall must stay 100% (DEC-033).
- Never ask for caste, disability, health or religion. If a user volunteers it, use it only within the session and never store it (DEC-033).
- An instrument past its `expires_on` date means abstain, not answer.
