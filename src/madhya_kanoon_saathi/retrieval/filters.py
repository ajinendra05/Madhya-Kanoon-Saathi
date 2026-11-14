"""Retrieval filters applied after scoring (DEC-058 item 4; .claude/rules/retrieval.md).

Shared by every retriever (BM25 now, dense later) so the same chunks are eligible everywhere.

- **Jurisdiction guard:** national/central chunks always pass; state-level chunks pass only for
  states in scope (the bot covers MP, DEC-016).
- **Currency on the query date:** a chunk is dropped if the query date is before its
  ``valid_from``, after its ``valid_to`` or after its ``expires_on``, or if its status is
  ``repealed``. Chunks whose status is ``draft``, ``model_law``, ``enacted_not_commenced``,
  ``sub_judice_flag``, ``passed_awaiting_assent`` or ``proposal`` are **kept but flagged**:
  the answer layer must label them (e.g. "draft, not in force").
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

IN_SCOPE_STATES = frozenset({"MP"})
FLAGGED_STATUSES = frozenset(
    {
        "draft",
        "model_law",
        "enacted_not_commenced",
        "sub_judice_flag",
        "passed_awaiting_assent",
        "proposal",
    }
)

# Flagged statuses whose text is not operative law; ranked after in-force law (DEC-067).
# sub_judice_flag is in force (only under challenge), so it is not in this set.
NOT_IN_FORCE = FLAGGED_STATUSES - {"sub_judice_flag"}


def _day(value: Any) -> date | None:
    return date.fromisoformat(value) if value else None


def jurisdiction_ok(meta: Mapping[str, Any], states: frozenset[str] = IN_SCOPE_STATES) -> bool:
    applies = meta.get("applies_to") or {}
    if applies.get("level", "national") == "national":
        return True
    return bool(set(applies.get("states", ())) & states)


def current_ok(meta: Mapping[str, Any], on: date) -> bool:
    if meta.get("status") == "repealed":
        return False
    start, end, expires = (
        _day(meta.get("valid_from")),
        _day(meta.get("valid_to")),
        _day(meta.get("expires_on")),
    )
    if start and on < start:
        return False
    if end and on > end:
        return False
    return not (expires and on > expires)


def flags(meta: Mapping[str, Any]) -> list[str]:
    """Labels the answer layer must show for an eligible chunk."""
    status = meta.get("status", "in_force")
    return [status] if status in FLAGGED_STATUSES else []


def eligible(meta: Mapping[str, Any], on: date, states: frozenset[str] = IN_SCOPE_STATES) -> bool:
    return jurisdiction_ok(meta, states) and current_ok(meta, on)
