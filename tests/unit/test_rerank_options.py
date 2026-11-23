"""Reranker speed/quality options (docs/RERANKER.md, DEC-090): A1, A4, A7 config, B1, B7, D1, E1."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from madhya_kanoon_saathi.generation import rewrite
from madhya_kanoon_saathi.generation.local import RetrievalConfig, keep_candidates
from madhya_kanoon_saathi.handlers.answer import typing_indicator
from madhya_kanoon_saathi.retrieval.hybrid import FusedHit
from madhya_kanoon_saathi.retrieval.reranker import session_options

# --- E1 query rewriting ---


def test_rewrite_returns_english_then_hindi() -> None:
    raw = json.dumps({"en": "defective goods sold by trader refund", "hi": "दोषपूर्ण माल वापसी"})
    calls: list[Any] = []

    def call(messages: list[dict[str, str]]) -> str:
        calls.append(messages)
        return raw

    out = rewrite.rewrite("dukaan vaale ne kharab saman diya", call)
    assert out == ["defective goods sold by trader refund", "दोषपूर्ण माल वापसी"]
    assert calls[0][0]["role"] == "system" and calls[0][1]["content"].startswith("dukaan")


@pytest.mark.parametrize(
    "raw",
    ["not json", "[]", json.dumps({"en": 5}), json.dumps({"en": "x" * 400}), json.dumps({})],
)
def test_rewrite_bad_output_falls_back_to_nothing(raw: str) -> None:
    assert rewrite.parse(raw, "q").queries == []


def test_rewrite_failure_never_raises() -> None:
    def boom(messages: list[dict[str, str]]) -> str:
        raise RuntimeError("budget cap")

    assert rewrite.rewrite("RTI kaise du", boom) == []


def test_rewrite_drops_copies_of_the_question() -> None:
    raw = json.dumps({"en": "RTI kaise du", "hi": "RTI kaise du"})
    assert rewrite.parse(raw, "rti KAISE du").queries == []


def test_rewrite_prompt_forbids_new_facts_and_answers() -> None:
    assert "Add no facts" in rewrite.SYSTEM and "Do not answer" in rewrite.SYSTEM
    assert '"acts"' in rewrite.SYSTEM and rewrite.REWRITE_VERSION == "r2"


MANIFEST = json.loads(Path("data/corpus_manifest.json").read_text(encoding="utf-8"))
ALIASES = json.loads(Path("data/instrument_aliases.json").read_text(encoding="utf-8"))
CATALOG = rewrite.act_catalog(MANIFEST, ALIASES)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Legal Services Authorities Act, 1987", "IN.LSA1987"),
        ("consumer protection act 2019", "IN.CPA2019"),
        ("RTI Act", "IN.RTI2005"),
        ("Consumer Protection (E-Commerce) Rules, 2020", "IN.CPECR2020"),
        ("Indian Penal Code", None),  # not in our corpus
        ("Consumer Protection Rules", None),  # ambiguous between three Rules
        ("Payment of Gratuity Act", None),
    ],
)
def test_act_names_match_only_our_corpus(name: str, expected: str | None) -> None:
    act = rewrite.match_act(name, CATALOG)
    assert (act.instrument_id if act else None) == expected


def test_matched_acts_add_official_titles_and_unknown_are_dropped() -> None:
    raw = json.dumps(
        {
            "en": "free legal services eligibility",
            "hi": "निःशुल्क विधिक सेवा पात्रता",
            "acts": ["Legal Services Authorities Act, 1987", "Indian Penal Code"],
        }
    )
    rw = rewrite.parse(raw, "free legal aid kaise milega", CATALOG)
    assert [a.instrument_id for a in rw.acts] == ["IN.LSA1987"]
    assert rw.dropped_acts == ["Indian Penal Code"]
    assert (
        rw.queries[0] == "free legal services eligibility The Legal Services Authorities Act, 1987"
    )
    assert rw.queries[1] == "निःशुल्क विधिक सेवा पात्रता"  # no official Hindi title recorded
    assert "Penal" not in " ".join(rw.queries)


def test_hindi_title_is_used_for_the_hindi_query_when_recorded() -> None:
    raw = json.dumps({"en": "information request fee", "hi": "सूचना शुल्क", "acts": ["RTI Act"]})
    rw = rewrite.parse(raw, "RTI fees?", CATALOG)
    assert rw.queries[1].endswith("सूचना का अधिकार अधिनियम, 2005")


# --- A4 candidate filter ---


def hit(cid: str) -> FusedHit:
    return FusedHit(cid, 0.0)


def test_keep_candidates_drops_filler_and_duplicate_texts_in_order() -> None:
    passages = {
        "a": "The landlord shall give notice.",
        "b": "I/we … …… … ∙∙∙∙ …… … ……",
        "c": "The landlord shall give notice.",
        "d": "धारा 8 के अधीन सूचना",
    }
    kept = keep_candidates([hit("a"), hit("b"), hit("c"), hit("d")], passages, drop_filler=True)
    assert [h.chunk_id for h in kept] == ["a", "d"]
    kept_all = keep_candidates([hit("b")], passages, drop_filler=False)
    assert [h.chunk_id for h in kept_all] == ["b"]


# --- config (A5, A7, B1, B3, B7) ---


def test_config_defaults_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    d = RetrievalConfig()
    assert (d.pool, d.final, d.rerank_window, d.threads) == (40, 6, 256, None)
    monkeypatch.setenv("MKS_ORT_THREADS", "2")
    monkeypatch.setenv("MKS_RERANK_WINDOW", "512")
    monkeypatch.setenv("MKS_RERANK_BATCH", "4")
    monkeypatch.setenv("MKS_RERANK_VARIANT", "int8-opt")
    monkeypatch.setenv("MKS_RETRIEVAL_CACHE", "0")
    c = RetrievalConfig.from_env()
    assert (c.threads, c.rerank_window, c.rerank_batch, c.rerank_variant, c.cache_size) == (
        2,
        512,
        4,
        "int8-opt",
        0,
    )


def test_session_options_pin_threads_only_when_asked() -> None:
    import onnxruntime as ort

    o = session_options(2)
    assert o.intra_op_num_threads == 2 and o.inter_op_num_threads == 1
    assert o.execution_mode == ort.ExecutionMode.ORT_SEQUENTIAL
    assert session_options(None).intra_op_num_threads == 0  # 0 = ONNX Runtime decides


# --- D1 typing indicator ---


def test_typing_indicator_repeats_until_the_block_ends() -> None:
    seen: list[int] = []
    done = threading.Event()

    def action(chat: int) -> None:
        seen.append(chat)
        if len(seen) >= 2:
            done.set()

    with typing_indicator(action, 7, every=0.01):
        assert done.wait(2)
    n = len(seen)
    threading.Event().wait(0.05)
    assert seen and set(seen) == {7} and len(seen) == n  # stopped after the block


def test_typing_indicator_ignores_errors() -> None:
    def bad(chat: int) -> None:
        raise OSError("telegram down")

    with typing_indicator(bad, 1, every=0.01):
        pass


def test_answer_service_shows_typing_while_answering() -> None:
    from datetime import UTC, datetime

    from madhya_kanoon_saathi.common.store import MemoryStore
    from madhya_kanoon_saathi.generation.pipeline import Reply
    from madhya_kanoon_saathi.handlers.answer import AnswerService

    events: list[str] = []

    @contextmanager
    def typing(chat: int) -> Any:
        events.append("typing-on")
        yield
        events.append("typing-off")

    def respond(q: str) -> tuple[Reply, list[dict[str, Any]]]:
        events.append("respond")
        return Reply("ok", False, None, {}), []

    texts = {"start": "hi", "error": "sorry", "limit": {"hi": "x", "hinglish": "x", "en": "x"}}
    svc = AnswerService(
        MemoryStore(),
        lambda c, t: events.append("send"),
        respond,
        texts,
        "k" * 40,
        clock=lambda: datetime(2026, 11, 23, tzinfo=UTC),
        typing=typing,
    )
    svc.handle({"chat_id": 5, "text": "RTI kaise du", "update_id": 1})
    assert events == ["typing-on", "respond", "typing-off", "send"]


# --- B7: batch size is honoured ---


class _Enc:
    def __init__(self, ids: list[int]) -> None:
        self.ids = ids


class _Tok:
    """Word -> id tokenizer with <s>=0, <pad>=1, </s>=2 (enough for pair building)."""

    def token_to_id(self, t: str) -> int | None:
        return 1 if t == "<pad>" else None

    def encode(self, text: str) -> _Enc:
        return _Enc([0, *(10 + len(w) for w in text.split()), 2])

    def encode_batch(self, texts: list[str]) -> list[_Enc]:
        return [self.encode(t) for t in texts]


class _Session:
    def __init__(self) -> None:
        self.batches: list[int] = []

    def run(self, outputs: list[str], feeds: dict[str, Any]) -> list[Any]:
        ids = feeds["input_ids"]
        self.batches.append(len(ids))
        return [np.zeros((len(ids), 1), dtype=np.float32)]


def test_reranker_uses_its_batch_size() -> None:
    from madhya_kanoon_saathi.retrieval.reranker import Reranker

    s = _Session()
    r = Reranker(s, _Tok(), "fake", 64)  # type: ignore[arg-type]
    r.batch_size = 2
    r.score("q", ["a b", "a b c", "a"])
    assert s.batches == [2, 1]


# --- A3 one version per provision ---


def test_provision_key_keeps_parts_apart_and_joins_languages() -> None:
    from madhya_kanoon_saathi.generation.local import provision_key

    assert provision_key("IN.RTIR2012:r8@hi@2012-07-31") == provision_key(
        "IN.RTIR2012:r8@en@2012-07-31"
    )
    assert provision_key("MP.LRCDR2018:form_i@en@2019-02-01~2") != provision_key(
        "MP.LRCDR2018:form_i@en@2019-02-01"
    )


def test_one_version_per_provision_prefers_the_question_language() -> None:
    from madhya_kanoon_saathi.generation.local import one_version_per_provision

    hits = [
        hit("IN.RTIR2012:r8@hi@2012-07-31"),
        hit("IN.RTI2005:s6:ss1@en@2005-06-15"),
        hit("IN.RTIR2012:r8@en@2012-07-31"),
        hit("IN.RTIR2012:r3@hi@2012-07-31"),
    ]
    en = [h.chunk_id for h in one_version_per_provision(hits, "en")]
    assert en == [
        "IN.RTIR2012:r8@en@2012-07-31",
        "IN.RTI2005:s6:ss1@en@2005-06-15",
        "IN.RTIR2012:r3@hi@2012-07-31",
    ]
    hi = [h.chunk_id for h in one_version_per_provision(hits, "hi")]
    assert hi[0] == "IN.RTIR2012:r8@hi@2012-07-31" and len(hi) == 3
