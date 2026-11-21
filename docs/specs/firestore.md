# Firestore layout (DEC-087, DEC-088)

One database `(default)`, Native mode, **asia-south1** (location and mode are permanent).
Code: `src/madhya_kanoon_saathi/common/store.py` (`MemoryStore` for tests/local, `FirestoreStore` for cloud).

| Collection / doc id | Fields | Kept | Written by |
| --- | --- | --- | --- |
| `seen_updates/{update_id}` | `received_at`, `expire_at`, `token` (random, detects our own retried write) | 2 days | ingress, create-if-absent |
| `queries/u{update_id}` | `chat` (hash), `at`, `outcome`, `lang`, `question`*, `reply`*, crisis tier/categories, `help`, `dispute`, `states`, `retrieved`, `cited`, `attempts`, `abstain_reason`, `timings_ms`, `costs[]` `{step, provider, model, units, unit_type, cost_inr, latency_ms}`, `expire_at` | 90 days | answer service |
| `quotas/{chat_hash}_{YYYYMMDD}` | `count`, `expire_at` (day = Indian calendar day, IST) | 2 days | answer service, in a transaction |
| `spend/{YYYYMMDD}` | `inr` (₹ incl. GST), `calls`, `expire_at` | 2 days | answer service: reserve worst case before a model call (refused above ₹20/day), settle to actual after (DEC-088) |

\* passed through `common/redact.py` inside `query_doc()`; callers cannot skip it.

Rules enforced in code:
- `chat` and quota keys must be `chat_hash(chat_id, MKS_CHAT_HASH_KEY)`: HMAC-SHA256, 32 hex chars; key ≥ 32 chars.
- Keys `chat_id`, `user_id`, `username`, `first_name`, `last_name`, `phone` are refused in query records.
- All timestamps timezone-aware. Deletion via TTL policies on `expire_at` (OPEN_QUESTIONS P16 for timing).
- Cost history beyond 90 days lives only in the nightly summary (DEC-012).
