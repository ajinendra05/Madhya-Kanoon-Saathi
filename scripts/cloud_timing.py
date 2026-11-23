"""Time the deployed answer service on golden questions (OPTIMIZATION.md, 2 vs 4 vCPU).

    uv run python scripts/cloud_timing.py --label cpu2 [--n 10]

Publishes golden v1.0 questions one at a time straight to the Pub/Sub topic ``mks-questions`` (the
same message the ingress would publish) with a made-up negative chat id per question, then waits
for the answer service's Firestore record ``queries/u<update_id>`` and reads its timings. Telegram
cannot deliver to a made-up chat, so records end as ``answered_unsent``; the processing time is what
is measured. One question per fake chat keeps the 20-per-day quota out of the way.

Each question is a real Sarvam answer call (~₹0.02 to 0.03, inside the ₹20/day cloud cap, DEC-088)
plus a free Groq rewrite. Uses Malik's gcloud login (``gcloud pubsub topics publish``; Firestore
read through application-default credentials). Results are appended to
``reports/cloud/timing_<label>.jsonl`` as they arrive; the first question warms the container and
is reported separately.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from compare_optimisations import pick
from eval_retrieval import GOLDEN, load_rows

PROJECT = "mks-prod-515410"
TOPIC = "mks-questions"
OUT = Path("reports/cloud")


def gcloud() -> str:
    g = (shutil.which("gcloud.cmd") if sys.platform == "win32" else None) or shutil.which("gcloud")
    if not g:
        raise SystemExit("gcloud not found")
    return g


def publish(update_id: int, chat_id: int, text: str) -> None:
    msg = json.dumps(
        {"update_id": update_id, "chat_id": chat_id, "text": text, "date": int(time.time())},
        ensure_ascii=False,
    )
    subprocess.run(
        [gcloud(), "pubsub", "topics", "publish", TOPIC, "--project", PROJECT, "--message", msg],
        check=True,
        capture_output=True,
    )


def wait_record(db: Any, update_id: int, timeout_s: float = 300) -> dict[str, Any] | None:
    ref = db.collection("queries").document(f"u{update_id}")
    end = time.time() + timeout_s
    while time.time() < end:
        snap = ref.get()
        if snap.exists:
            return dict(snap.to_dict() or {})
        time.sleep(2)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()
    from google.cloud import firestore

    db = firestore.Client(project=PROJECT)
    chunks = [
        json.loads(x) for x in Path("data/parsed/chunks.jsonl").read_text("utf-8").splitlines()
    ]
    rows = pick(load_rows(GOLDEN, {c["section_uid"] for c in chunks}, None), a.n + 1)
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f"timing_{a.label}.jsonl"
    base = int(time.time()) * 100  # unique update ids per run
    results = []
    with out_path.open("a", encoding="utf-8", newline="\n") as out:
        for i, r in enumerate(rows):
            uid, chat = base + i, -(base + i)
            t0 = time.time()
            publish(uid, chat, r["raw_question_redacted"])
            rec = wait_record(db, uid)
            wall = round(time.time() - t0, 1)
            costs = (rec or {}).get("costs", [])
            row = {
                "label": a.label,
                "id": r["id"],
                "language": r.get("language"),
                "warmup": i == 0,
                "wall_s": wall,
                "total_ms": ((rec or {}).get("timings_ms") or {}).get("total"),
                "outcome": (rec or {}).get("outcome"),
                "steps_ms": {c.get("step"): c.get("latency_ms") for c in costs},
                "rewrite_limits": next(
                    (c.get("limits") for c in costs if c.get("step") == "rewrite"), None
                ),
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            results.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    warm = sorted(x["total_ms"] / 1000 for x in results if not x["warmup"] and x["total_ms"])
    if warm:
        print(
            f"{a.label}: warm n={len(warm)} mean {sum(warm) / len(warm):.1f}s "
            f"p50 {warm[len(warm) // 2]:.1f}s max {warm[-1]:.1f}s; "
            f"first (warm-up) {results[0]['total_ms']} ms"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
