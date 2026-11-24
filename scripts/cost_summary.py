"""Nightly cost summary for the public dashboard (W3.2, DEC-012, DEC-095). Standard library only.

    GOOGLE_ACCESS_TOKEN=... python scripts/cost_summary.py --pages <dir> [--date YYYY-MM-DD]

Reads one Indian calendar day of the answer service's Firestore records (``queries``, by
their ``at`` time) and that day's ``spend`` counter through the Firestore REST API, then
writes **aggregates only** (no question or reply text, no chat hashes, no update ids) to
``<dir>/data/summary-<date>.json`` and merges the day into ``<dir>/data/history.json``; it also
copies the dashboard page ``site/index.html``. Default date: yesterday in India (the job runs
at 02:00 IST).

Token: the GitHub Actions workflow logs in keylessly as the read-only ``mks-cost-reader``
account and passes a short-lived access token in ``GOOGLE_ACCESS_TOKEN``; locally
``gcloud auth print-access-token``. Firestore REST: ``documents:runQuery`` with a structured
query, ``GET documents/spend/<YYYYMMDD>`` (firebase.google.com/docs/firestore/reference/rest).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT = "mks-prod-515410"
BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
IST = timezone(timedelta(hours=5, minutes=30))
SITE = Path(__file__).resolve().parent.parent / "site" / "index.html"


def decode(value: dict[str, Any]) -> Any:
    """Firestore REST typed value -> plain Python."""
    if "mapValue" in value:
        return {k: decode(v) for k, v in (value["mapValue"].get("fields") or {}).items()}
    if "arrayValue" in value:
        return [decode(v) for v in (value["arrayValue"].get("values") or [])]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "booleanValue" in value:
        return bool(value["booleanValue"])
    if "nullValue" in value:
        return None
    for key in ("stringValue", "timestampValue", "referenceValue"):
        if key in value:
            return value[key]
    return None


def fields(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: decode(v) for k, v in (doc.get("fields") or {}).items()}


def day_bounds(day: date) -> tuple[str, str]:
    start = datetime(day.year, day.month, day.day, tzinfo=IST)
    to_utc = lambda t: t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    return to_utc(start), to_utc(start + timedelta(days=1))


def _request(url: str, token: str, body: dict[str, Any] | None = None) -> Any:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        method="POST" if body is not None else "GET",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise SystemExit(f"Firestore HTTP {e.code}") from None


def fetch_day(day: date, token: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    lo, hi = day_bounds(day)
    query = {
        "structuredQuery": {
            "from": [{"collectionId": "queries"}],
            "where": {
                "compositeFilter": {
                    "op": "AND",
                    "filters": [
                        {
                            "fieldFilter": {
                                "field": {"fieldPath": "at"},
                                "op": "GREATER_THAN_OR_EQUAL",
                                "value": {"timestampValue": lo},
                            }
                        },
                        {
                            "fieldFilter": {
                                "field": {"fieldPath": "at"},
                                "op": "LESS_THAN",
                                "value": {"timestampValue": hi},
                            }
                        },
                    ],
                }
            },
        }
    }
    rows = _request(f"{BASE}:runQuery", token, query) or []
    records = [fields(r["document"]) for r in rows if "document" in r]
    spend_doc = _request(f"{BASE}/spend/{day:%Y%m%d}", token)
    return records, (fields(spend_doc) if spend_doc else None)


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return round(s[min(len(s) - 1, int(q * (len(s) - 1) + 0.5))], 2)


def summarise(
    day: date, records: list[dict[str, Any]], spend: dict[str, Any] | None
) -> dict[str, Any]:
    """Aggregates only; nothing that identifies a person or repeats what they asked."""
    n = len(records)
    times = [
        r["timings_ms"]["total"] / 1000 for r in records if (r.get("timings_ms") or {}).get("total")
    ]
    by_step: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "inr": 0.0, "latency_ms": []}
    )
    by_provider: Counter[str] = Counter()
    inr_total = 0.0
    for r in records:
        for c in r.get("costs") or []:
            step = str(c.get("step", "?"))
            cost = float(c.get("cost_inr") or 0.0)
            by_step[step]["calls"] += 1
            by_step[step]["inr"] += cost
            if c.get("latency_ms") is not None:
                by_step[step]["latency_ms"].append(float(c["latency_ms"]))
            by_provider[str(c.get("provider", "?"))] += 1
            inr_total += cost
    steps = {
        k: {
            "calls": v["calls"],
            "inr": round(v["inr"], 4),
            "latency_ms_p50": _pct(v["latency_ms"], 0.5),
        }
        for k, v in sorted(by_step.items())
    }
    crisis = Counter(((r.get("crisis") or {}).get("tier") or "none") for r in records)
    return {
        "date": day.isoformat(),
        "questions": n,
        "outcomes": dict(Counter(str(r.get("outcome", "?")) for r in records)),
        "abstained": sum(1 for r in records if r.get("abstain_reason")),
        "topic_lists": sum(1 for r in records if r.get("help")),
        "crisis": {"full": crisis.get("full", 0), "note": crisis.get("note", 0)},
        "languages": dict(Counter(str(r.get("lang", "?")) for r in records)),
        "inr_total": round(inr_total, 4),
        "inr_per_question": round(inr_total / n, 4) if n else None,
        "steps": steps,
        "providers": dict(by_provider),
        "time_s": {
            "mean": round(statistics.mean(times), 2) if times else None,
            "p50": _pct(times, 0.5),
            "p95": _pct(times, 0.95),
        },
        "spend_counter": (
            {"inr": round(float(spend.get("inr", 0.0)), 4), "calls": int(spend.get("calls", 0))}
            if spend
            else None
        ),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def publish(summary: dict[str, Any], pages: Path) -> None:
    data = pages / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / f"summary-{summary['date']}.json").write_text(
        json.dumps(summary, indent=1) + "\n", encoding="utf-8"
    )
    hist_path = data / "history.json"
    history = json.loads(hist_path.read_text("utf-8")) if hist_path.exists() else []
    history = [h for h in history if h.get("date") != summary["date"]] + [summary]
    history.sort(key=lambda h: h["date"])
    hist_path.write_text(json.dumps(history, indent=1) + "\n", encoding="utf-8")
    shutil.copy2(SITE, pages / "index.html")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=Path, required=True, help="gh-pages working tree")
    ap.add_argument("--date", default="", help="IST date YYYY-MM-DD (default: yesterday in India)")
    a = ap.parse_args()
    token = os.environ.get("GOOGLE_ACCESS_TOKEN", "").strip()
    if not token:
        print("GOOGLE_ACCESS_TOKEN is not set")
        return 2
    day = date.fromisoformat(a.date) if a.date else (datetime.now(IST) - timedelta(days=1)).date()
    records, spend = fetch_day(day, token)
    summary = summarise(day, records, spend)
    publish(summary, a.pages)
    print(f"{day}: {summary['questions']} questions, ₹{summary['inr_total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
