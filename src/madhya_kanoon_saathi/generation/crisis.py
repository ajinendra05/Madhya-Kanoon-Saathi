"""Crisis router: runs on every message before retrieval (DEC-033 item 1, DEC-074).

Two layers, any hit counts (recall first; a few false alarms are acceptable):

1. **Rules** — phrase patterns per category in Hindi, Hinglish and English. A pattern needs a danger
   word near its subject ("पति ... मारते"), so "मालिक ने वेतन मार लिया" (wages withheld) is not a
   crisis. Message and patterns go through the same normaliser (NFC, nukta folding, ँ → ं,
   lower case) so spelling variants match.
2. **Embeddings** — cosine similarity of the query's BGE-M3 vector (already computed for retrieval)
   to example crisis messages (``data/safety/crisis_examples.json``); a category fires at or above
   the threshold tuned on the dev split of the crisis test set (``scripts/eval_crisis.py``).

The router only decides *which* categories apply and which contacts (``data/contacts.yaml`` ids) to
show. Reply wording lives in ``data/safety/crisis_replies.json`` and is used only once Malik has
approved it (generation rules: escalation text is a major decision).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from madhya_kanoon_saathi.common.normalize import normalize

# category -> contact ids shown, in order (DEC-074 item 3)
CONTACTS: dict[str, tuple[str, ...]] = {
    "self_harm": ("telemanas_14416", "erss_112"),
    "violence_now": ("erss_112",),
    "domestic_violence": ("erss_112", "women_181"),
    "child_at_risk": ("child_1098", "erss_112"),
    "cyber_fraud": ("cyber_1930",),
    "eviction_now": ("erss_112", "nalsa_15100"),
}
# self-harm replies carry no legal content (DEC-074 item 2)
NO_LEGAL_ANSWER = frozenset({"self_harm"})
ORDER = tuple(CONTACTS)  # self_harm first: it decides the reply mode
MAX_EMBEDDING_CATEGORIES = 2  # embedding layer: top categories kept (crisis_2026-11-17 eval)

_RULES: dict[str, tuple[str, ...]] = {
    "self_harm": (
        r"आत्महत्या", r"खुदकुशी", r"फांसी", r"(मर जाना|मरना) (चाहता|चाहती|है)",
        r"जीने का (मन|मतलब|कोई मतलब) नहीं", r"जीना नहीं चाहत",
        r"(जिंदगी|जान) खत्म कर", r"सब खत्म कर (दूं|दूंगा|दूंगी|देना|दें)",
        r"जान दे (दूंगा|दूंगी|दूं)", r"नस काट", r"जहर खा",
        r"khud ?kushi", r"aa?tma? ?hatya", r"\bsuicid", r"\b(mar jaana|marna) (chahta|chahti|hai)",
        r"jeene ka (koi )?(mann?|matlab) nahi", r"jeena nahi chaht",
        r"\b(zindagi|jindagi) khatam", r"sab khatam kar (dena|dunga|dungi|du)\b",
        r"jaan de (dunga|dungi)", r"\b(fansi|phansi|phaansi)\b", r"\b(zeher|jahar) kha",
        r"\bkill(ing)? myself", r"\bend (my life|it all)", r"\bwant to die\b",
        r"\bdon'?t want to live", r"\bno reason to live", r"\btake my (own )?life",
        r"\bhurt(ing)? myself", r"\bself[- ]?harm",
    ),
    "domestic_violence": (
        r"घरेलू हिंसा", r"दहेज.{0,30}(मार|पीट|प्रताड|तंग|जला)",
        r"(पति|ससुराल|सास|ससुर|देवर).{0,30}(मारत|मारते|पीटत|पीटते|पिटाई|मारपीट|मार-पीट|हाथ उठा|मारने)",
        r"gharelu hinsa", r"\bdahej.{0,30}(maar|\bmar\b|peet|pitai|pareshan|tang|tortur)",
        r"\b(pati|sasural|saas|devar)\b.{0,30}\b(maar|marta|marte|peet|pita|pitai|haath utha)",
        r"domestic violence",
        r"\b(husband|in-?laws?|mother-in-law|father-in-law)\b.{0,40}"
        r"\b(beat|beats|beating|hit|hits|hitting|tortur|abus|slap)",
        r"\bdowry\b.{0,30}(harass|tortur|beat|hit|abus)",
    ),
    "child_at_risk": (
        r"बाल विवाह", r"बाल (श्रम|मजदूर)", r"नाबालिग.{0,25}(शादी|विवाह)",
        r"\d{1,2} साल की (लडकी|बच्ची).{0,25}(शादी|विवाह)",
        r"(बच्च|बच्ची|भतीज|भांज).{0,40}(पीट|मारत|मारते|मारता|पिटाई|शोषण|यौन)",
        r"\b(bal|baal) vivah", r"\b(nabalig|naabalig|minor)\b.{0,25}\b(shaadi|shadi|vivah)",
        r"\b(bachch|bacch|bachi)\w*\b.{0,40}\b(pit|peet|maar|pitai|shoshan)",
        r"child marriage", r"child labou?r",
        r"\b(minor|underage|\d{1,2}[- ]year[- ]old)\b.{0,30}\b(married|marriage|wedding)",
        r"\b(child|children|kid|kids|minor)\b.{0,40}"
        r"\b(beaten|beat|beating|abused|abuse|hit|molest|traffick|tortur)",
    ),
    "cyber_fraud": (
        r"साइबर (ठगी|फ्रॉड|धोखा|अपराध)", r"ऑनलाइन (ठगी|धोखाधडी|धोखा|फ्रॉड)",
        r"(यूपीआई|upi).{0,20}(ठगी|फ्रॉड|धोखा)", r"ओटीपी.{0,40}(पैसे|रुपये|निकाल|कट)",
        r"खाते से.{0,30}(निकाल|कट|गायब|चले गए)", r"ठगी (हो|हुई)", r"खाता खाली",
        r"\b(online|cyber|saibar|upi)\b.{0,15}\b(fraud|thagi|dhokha|scam)",
        r"\botp\b.{0,40}\b(paise|paisa|nikal|kat)", r"\b(account|khate) se paise (kat|nikal)",
        r"\bthagi\b",
        r"\b(upi|online|cyber|bank|job|loan|investment)\b.{0,20}\b(fraud|scam)",
        r"\bscam(med|mer)?\b", r"\b(shared|gave|told)\b.{0,15}\botp\b", r"\bhacked\b",
        r"\b(debited|deducted|withdrawn)\b.{0,30}\bwithout\b", r"\bphishing\b", r"\bfraudster",
    ),
    "violence_now": (
        r"जान से मार", r"मार (डाल|देंगे|दूंगा)", r"हमला", r"मारपीट (कर|हो)",
        r"चाकू", r"बंदूक", r"तलवार", r"कट्टा", r"अपहरण", r"बलात्कार", r"छेडछाड", r"पीछा कर",
        r"लाठी",
        r"jaan se maar", r"\bmaar (dal|daal|denge|dunga)", r"\bhaml(a|e)\b", r"maar ?peet",
        r"\b(chaku|chhuri|bandook|goli)\b", r"\b(apaharan|kidnap)", r"\bbalatkar",
        r"chhed ?chhad", r"\bpeecha kar", r"\bkhoon beh",
        r"\bthreat\w*\b.{0,30}\b(kill|hurt|attack|beat)", r"\bkill me\b",
        r"\battack(ed|ing)?\b", r"\bassault", r"\b(knife|gun|weapon)\b", r"\brap(e|ed)\b",
        r"\bmolest", r"\bstalk(ing|ed|s)?\b", r"\b(beat|beating|hit|hitting) me\b",
        r"\b(i am|i'm) hurt\b", r"\bbleeding\b",
    ),
    "eviction_now": (
        r"सामान.{0,15}बाहर (फेंक|फेक|निकाल)", r"ताला (लगा|डाल) (दिया|दिए)",
        r"घर से (निकाल|बाहर कर) (दिया|दिए)", r"(रात|आज).{0,25}(कहां) (जाऊं|जाएं|रहूं)",
        r"रहने की जगह नहीं", r"सडक पर (हूं|हैं|आ गए)",
        r"\b(ghar|kamre|kamra) se (nikal|nikaal|bahar kar) (diya|diye)",
        r"\b(saman|samaan)\b.{0,15}\b(bahar|baahar) (fenk|phenk|fek)",
        r"\b(taala|tala|lock) laga (diya|diye)", r"\braat (mein|me|ko) kahan (jaun|jayen|rahun)",
        r"rehne ki jagah nahi",
        r"\block(ed)? (me|us) out", r"\b(threw|thrown|throw|kicked)\b.{0,30}"
        r"\b(out|belongings|things|stuff|street)\b",
        r"\bevicted\b.{0,30}\b(tonight|today|now|without (any )?notice)",
        r"\bnowhere to (go|sleep|stay)",
    ),
}  # fmt: skip


def prepare(text: str) -> str:
    """Matching form shared by messages and patterns."""
    t = normalize(text, fold_nukta=True).replace("ँ", "ं").lower()
    return re.sub(r"\s+", " ", t).strip()


_COMPILED = {
    cat: tuple(re.compile(prepare(p)) for p in patterns) for cat, patterns in _RULES.items()
}


@dataclass
class CrisisResult:
    """Router output. ``tier`` (DEC-075): "full" when a rule fired (crisis reply first), "note"
    when only the embedding layer fired (normal answer + one safety line), None otherwise."""

    categories: list[str] = field(default_factory=list)  # in ORDER
    by_rule: list[str] = field(default_factory=list)
    by_embedding: list[str] = field(default_factory=list)
    similarity: dict[str, float] = field(default_factory=dict)  # margin per category

    @property
    def is_crisis(self) -> bool:
        return bool(self.categories)

    @property
    def tier(self) -> str | None:
        if self.by_rule:
            return "full"
        return "note" if self.by_embedding else None

    @property
    def legal_answer_allowed(self) -> bool:
        # only a rule-detected self-harm message switches off legal content (DEC-075 item 2)
        return not any(c in NO_LEGAL_ANSWER for c in self.by_rule)

    @property
    def contact_ids(self) -> list[str]:
        out: list[str] = []
        for c in self.categories:
            out += [x for x in CONTACTS[c] if x not in out]
        return out


def rule_categories(text: str) -> list[str]:
    t = prepare(text)
    return [c for c in ORDER if any(p.search(t) for p in _COMPILED[c])]


@dataclass
class ExampleIndex:
    """Normalised BGE-M3 vectors of example crisis messages per category, and of ordinary legal
    questions. A category's score is the **margin** (DEC-075): similarity to its nearest example
    minus similarity to the nearest ordinary question; it fires at or above ``threshold``."""

    vectors: dict[str, np.ndarray]  # category -> (n, d), rows L2-normalised
    threshold: float
    ordinary: np.ndarray | None = None  # (m, d), rows L2-normalised

    def similarities(self, query_vec: np.ndarray) -> dict[str, float]:
        q = query_vec / (np.linalg.norm(query_vec) or 1.0)
        base = float(np.max(self.ordinary @ q)) if self.ordinary is not None else 0.0
        return {c: float(np.max(v @ q)) - base for c, v in self.vectors.items()}


def route(
    text: str, query_vec: np.ndarray | None = None, examples: ExampleIndex | None = None
) -> CrisisResult:
    """Crisis categories for one message. Without a vector or examples, rules only."""
    res = CrisisResult(by_rule=rule_categories(text))
    if query_vec is not None and examples is not None:
        res.similarity = examples.similarities(query_vec)
        # at most the MAX_EMBEDDING_CATEGORIES best: a safety line with six numbers is noise
        ranked = sorted(res.similarity, key=lambda c: -res.similarity[c])
        top = {
            c for c in ranked[:MAX_EMBEDDING_CATEGORIES] if res.similarity[c] >= examples.threshold
        }
        # self-harm is kept whenever it clears the threshold, whatever its rank: missing it costs
        # most (added after holdout HO-005 "neend ki goliyan kha li hain" ranked it third)
        if res.similarity.get("self_harm", -1.0) >= examples.threshold:
            top.add("self_harm")
        res.by_embedding = [c for c in ORDER if c in top]
    hits = set(res.by_rule) | set(res.by_embedding)
    res.categories = [c for c in ORDER if c in hits]
    return res


def build_examples(
    examples: dict[str, Sequence[str]],
    encode: Callable[[list[str]], np.ndarray],
    threshold: float,
    ordinary: Sequence[str] = (),
    categories: Iterable[str] | None = None,
) -> ExampleIndex:
    """Embed example messages with ``encode`` (the retrieval embedder's ``encode``)."""

    def unit(texts: Sequence[str]) -> np.ndarray:
        m = np.asarray(encode(list(texts)), dtype=np.float32)
        out: np.ndarray = m / np.linalg.norm(m, axis=1, keepdims=True)
        return out

    unknown = set(examples) - set(CONTACTS if categories is None else categories)
    if unknown:
        raise ValueError(f"unknown crisis categories {sorted(unknown)}")
    return ExampleIndex(
        vectors={cat: unit(texts) for cat, texts in examples.items()},
        threshold=threshold,
        ordinary=unit(ordinary) if ordinary else None,
    )


LANGS = ("hi", "hinglish", "en")
_PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")


@dataclass(frozen=True)
class CrisisReply:
    """Text around the normal answer: ``prefix`` first (full tier), ``suffix`` last (note tier)."""

    prefix: str | None
    suffix: str | None
    legal_answer_allowed: bool


def render(
    result: CrisisResult,
    lang: str,
    replies: dict[str, Any],
    numbers: dict[str, str],
) -> CrisisReply:
    """Crisis text for one message (DEC-074/075).

    ``replies`` is ``data/safety/crisis_replies.json`` and must be approved by Malik; ``numbers``
    maps contact ids to numbers from ``data/contacts.yaml``. Raises PermissionError on unapproved
    wording and KeyError if a placeholder has no sourced contact.
    """
    if replies.get("status") != "approved":
        raise PermissionError("crisis reply wording is not approved yet (crisis_replies.json)")
    lang = lang if lang in LANGS else "en"

    def fill(template: str) -> str:
        return _PLACEHOLDER.sub(lambda m: numbers[m.group(1)], template)

    prefix = suffix = None
    if result.tier == "full":
        prefix = "\n".join(fill(replies["full"][c][lang]) for c in result.by_rule)
    elif result.tier == "note":
        ids: list[str] = []
        for c in result.by_embedding:
            ids += [x for x in CONTACTS[c] if x not in ids]
        suffix = replies["note"][lang].replace("{numbers}", ", ".join(numbers[x] for x in ids))
    return CrisisReply(prefix, suffix, result.legal_answer_allowed)
