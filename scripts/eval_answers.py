# ruff: noqa: E501
"""Answer-level evaluation on golden rows, end to end (W2.3; deterministic scorers, DEC-023).

Usage:
    uv run python scripts/eval_answers.py --sample smoke   # 20 stratified rows (~Rs1, DEC-078 cap)
    uv run python scripts/eval_answers.py --ids GS-074,GS-129

Every LLM answer is cached in data/eval/llm_cache.jsonl, keyed by the sha256 of the request, so
re-scoring is free and repeatable; only cache misses are paid calls (each through the spend cap).
Draft wording is used (--allow-draft semantics) because evaluation precedes Malik's approval.

Scores per row (no LLM judge):
- behaviour: answer/answer_with_caveat → answered; abstain_refer → abstained, or the dispute
  referral was given; crisis_route → full crisis tier; gated → abstained (row skipped otherwise);
- cited_expected: a cited provision covers or is covered by an expected clause (lenient match);
- must_include / must_not_include: the golden regexes on the reply text (case-insensitive).
Writes reports/answers/<golden>_<date>_<sample>.md and .json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

from madhya_kanoon_saathi.common.contacts import load as load_contacts
from madhya_kanoon_saathi.common.section_uid import covers
from madhya_kanoon_saathi.generation.llm import complete, request_body
from madhya_kanoon_saathi.generation.local import LocalRuntime
from madhya_kanoon_saathi.generation.pipeline import answer
from madhya_kanoon_saathi.generation.prompt import PROMPT_VERSION

GOLDEN = Path("data/golden/v0.1-seed/golden_set_v0.1_seed.jsonl")
CACHE = Path("data/eval/llm_cache.jsonl")
OUT = Path("reports/answers")
SMOKE = {  # stratified 20 rows: answerable (indexed), refer/abstain, crisis, gated
    "answer": 10,
    "abstain_refer": 4,
    "crisis_route": 3,
    "gated": 3,
}


def load_cache() -> dict[str, str]:
    if not CACHE.is_file():
        return {}
    rows = (json.loads(x) for x in CACHE.read_text("utf-8").splitlines() if x.strip())
    return {r["request_sha256"]: r["content"] for r in rows}


def cached_generator(cache: dict[str, str], stats: dict[str, int]):  # type: ignore[no-untyped-def]
    def generate(messages: list[dict[str, str]]) -> str:
        body = request_body(messages, "json_object", reasoning_effort="low", max_tokens=1200)
        key = hashlib.sha256(
            json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        if key in cache:
            stats["cache_hits"] += 1
            return cache[key]
        comp = complete(body, purpose="eval_answers")
        stats["paid_calls"] += 1
        cache[key] = comp.content
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("a", encoding="utf-8", newline="\n") as f:
            f.write(
                json.dumps(
                    {
                        "request_sha256": key,
                        "prompt_version": PROMPT_VERSION,
                        "content": comp.content,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        return comp.content

    return generate


def pick(
    rows: list[dict[str, Any]], present: set[str], sample: str, ids: list[str]
) -> list[dict[str, Any]]:
    if ids:
        return [r for r in rows if r["id"] in ids]

    def answerable(r: dict[str, Any]) -> bool:
        return bool(r["expected_clauses"]) and all(
            any(
                covers(p, c["section_uid"] or c["act_id"])
                or covers(c["section_uid"] or c["act_id"], p)
                for p in present
            )
            for c in r["expected_clauses"]
        )

    if sample == "indexed":  # every answerable-now row + every refer/crisis row (cheap or free)
        return [
            r
            for r in rows
            if (r["expected_behavior"] in ("answer", "answer_with_caveat") and answerable(r))
            or r["expected_behavior"] in ("abstain_refer", "crisis_route")
        ]
    out: list[dict[str, Any]] = []
    for behaviour, n in SMOKE.items():
        cands = [
            r
            for r in rows
            if r["expected_behavior"] == behaviour
            or (behaviour == "answer" and r["expected_behavior"] == "answer_with_caveat")
        ]
        if behaviour == "answer":  # answerable now: every expected clause has a chunk
            cands = [
                r
                for r in cands
                if r["expected_clauses"]
                and all(
                    any(
                        covers(p, c["section_uid"] or c["act_id"])
                        or covers(c["section_uid"] or c["act_id"], p)
                        for p in present
                    )
                    for c in r["expected_clauses"]
                )
            ]
        out += cands[:: max(1, len(cands) // n)][:n]
    return out


def score(row: dict[str, Any], reply: Any, top_rerank: float | None) -> dict[str, Any]:
    exp = row["expected_behavior"]
    cited = [c.split("@")[0] for c in reply.log.get("cited", [])]
    if exp in ("answer", "answer_with_caveat"):
        behaviour = not reply.abstained
    elif exp == "abstain_refer":
        behaviour = reply.abstained or bool(reply.log.get("dispute", {}).get("flag"))
    elif exp == "crisis_route":
        behaviour = reply.log.get("crisis", {}).get("tier") == "full"
    else:  # gated: the law is not in the index, so the bot must not answer from elsewhere
        behaviour = reply.abstained
    expected = [c["section_uid"] or c["act_id"] for c in row.get("expected_clauses", [])]
    cited_expected = None
    if expected and not reply.abstained:
        cited_expected = any(covers(c, e) or covers(e, c) for c in cited for e in expected)
    text = reply.text
    inc = [p for p in row.get("must_include", []) if not re.search(p, text, re.I)]
    exc = [p for p in row.get("must_not_include", []) if re.search(p, text, re.I)]
    return {
        "id": row["id"], "lang": row["language"], "domain": row["domain"], "expected": exp,
        "abstained": reply.abstained, "top_rerank": top_rerank,
        "reason": reply.reason, "behaviour_ok": behaviour, "cited": cited,
        "cited_expected": cited_expected, "missing_must_include": inc, "found_must_not_include": exc,
        "merits_dropped": reply.log.get("merits_blocks_dropped", 0), "attempts": reply.log.get("attempts"),
    }  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="smoke")
    ap.add_argument("--ids", default="")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    rows = [json.loads(x) for x in GOLDEN.read_text("utf-8").splitlines()]
    rt = LocalRuntime.load()
    present = {c["section_uid"] for c in rt.chunks.values()}
    chosen = pick(rows, present, a.sample, [x for x in a.ids.split(",") if x])
    texts = json.loads(Path("data/answer_texts.json").read_text("utf-8"))
    replies = json.loads(Path("data/safety/crisis_replies.json").read_text("utf-8"))
    numbers = {c.id: c.number for c in load_contacts(Path("data/contacts.yaml"))}
    cache, stats = load_cache(), {"paid_calls": 0, "cache_hits": 0}
    gen = cached_generator(cache, stats)
    results, samples = [], []
    for r in chosen:
        q = r["raw_question_redacted"]
        t0 = time.perf_counter()
        vec = rt.vector(q)
        chunks = rt.retrieve(q, vec, date.today())
        reply = answer(q, retrieve=lambda _q, c=chunks: c, generate=gen, texts=texts, crisis_replies=replies,
                       numbers=numbers, today=date.today(), query_vec=vec, crisis_examples=rt.crisis_index,
                       dispute_examples=rt.dispute_index, versions=rt.versions, allow_draft=True)  # fmt: skip
        scores = [float(c.extra["rerank"]) for c in chunks if c.extra.get("rerank")]
        s = score(r, reply, max(scores) if scores else None)
        s["seconds"] = round(time.perf_counter() - t0, 1)
        results.append(s)
        samples.append({"id": r["id"], "question": q, "reply": reply.text})
        print(
            f"{r['id']} {s['expected']:18s} ok={s['behaviour_ok']} cited_exp={s['cited_expected']} {s['seconds']}s"
        )

    def rate(key: str, subset: list[dict[str, Any]]) -> str:
        vals = [x[key] for x in subset if x[key] is not None]
        return f"{sum(vals)}/{len(vals)}" if vals else "-"

    L = [f"# Answer eval ({a.sample}): {GOLDEN.parent.name}, {date.today().isoformat()}", "",
         f"**Seed golden set (unverified); wording approved (DEC-079), prompt {PROMPT_VERSION}.** Deterministic scores, no judge.", "",
         f"- rows: {len(results)} · paid calls: {stats['paid_calls']} · cache hits: {stats['cache_hits']}", "",
         "| expected | rows | behaviour ok | cited an expected provision | must_include all | must_not_include none |",
         "| --- | --- | --- | --- | --- | --- |"]  # fmt: skip
    for exp in dict.fromkeys(x["expected"] for x in results):
        sub = [x for x in results if x["expected"] == exp]
        inc = sum(not x["missing_must_include"] for x in sub)
        exc = sum(not x["found_must_not_include"] for x in sub)
        L.append(
            f"| {exp} | {len(sub)} | {rate('behaviour_ok', sub)} | {rate('cited_expected', sub)} | {inc}/{len(sub)} | {exc}/{len(sub)} |"
        )
    for key in ("lang", "domain"):
        L += [
            "",
            f"### By {key} (answer + answer_with_caveat rows)",
            "",
            f"| {key} | rows | behaviour ok | cited expected |",
            "| --- | --- | --- | --- |",
        ]
        ans_rows = [x for x in results if x["expected"] in ("answer", "answer_with_caveat")]
        for v in sorted({x[key] for x in ans_rows}):
            sub = [x for x in ans_rows if x[key] == v]
            L.append(
                f"| {v} | {len(sub)} | {rate('behaviour_ok', sub)} | {rate('cited_expected', sub)} |"
            )
    # abstention-threshold candidates (analysis only; the threshold is Malik's decision)
    good = sorted(
        x["top_rerank"]
        for x in results
        if x["expected"] in ("answer", "answer_with_caveat")
        and x["behaviour_ok"]
        and x["top_rerank"] is not None
    )
    refer = sorted(
        x["top_rerank"]
        for x in results
        if x["expected"] == "abstain_refer" and x["top_rerank"] is not None
    )
    if good and refer:
        L += [
            "",
            "## Abstention threshold candidates (top reranker logit; analysis only)",
            "",
            "| threshold | correct answers kept | refer rows blocked |",
            "| --- | --- | --- |",
        ]
        for t in sorted({round(v, 2) for v in good + refer}):
            kept = sum(v >= t for v in good)
            blocked = sum(v < t for v in refer)
            L.append(f"| {t} | {kept}/{len(good)} | {blocked}/{len(refer)} |")
    L += [
        "",
        "## Per row",
        "",
        "| id | lang | expected | abstained (reason) | ok | cited expected | top rerank | missing must_include | cited |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for x in results:
        L.append(
            f"| {x['id']} | {x['lang']} | {x['expected']} | {x['abstained']} ({x['reason']}) | {x['behaviour_ok']} | {x['cited_expected']} | {x['top_rerank']} | {', '.join(x['missing_must_include'])} | {', '.join(x['cited'])} |"
        )
    L += ["", "## Replies", ""]
    for smp in samples:
        L += [f"### {smp['id']}: {smp['question']}", "", "```", smp["reply"], "```", ""]
    OUT.mkdir(parents=True, exist_ok=True)
    tag = a.tag or (a.sample if not a.ids else "ids")
    stem = OUT / f"{GOLDEN.parent.name}_{date.today().isoformat()}_{tag}_{PROMPT_VERSION}"
    (stem.parent / (stem.name + ".md")).write_text(
        "\n".join(L) + "\n", encoding="utf-8", newline="\n"
    )
    (stem.parent / (stem.name + ".json")).write_text(
        json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print("\n".join(L[4 : 8 + len({x["expected"] for x in results})]))
    print("->", stem.parent / (stem.name + ".md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
