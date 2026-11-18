# ruff: noqa: E501  (pattern table: one rule per entry reads better than wrapped strings)
"""Dispute ("who is right") detector (DEC-033 item 6, DEC-038, DEC-076).

A *merits* question asks the bot to judge a dispute or predict an outcome: "ज़मीन किसकी है?",
"क्या मैं केस जीत जाऊँगा?", "will he go to jail?", "who gets custody?". The bot gives legal
**information**, not advice: for such questions the answer layer explains the procedure only and
refers the user to the District Legal Services Authority (free legal aid, LSA Act s.12; NALSA
15100 from ``data/contacts.yaml``). Procedural questions on the same topics ("सीमांकन कैसे
करवाएँ?") are not disputes.

Same two layers as the crisis router (DEC-074/075): phrase rules, plus a margin between the nearest
merits example and the nearest procedural question (``data/safety/dispute_examples.json``); either
layer flags the question. The domain (land, family, criminal, sc_st, other) is tagged by keywords so
the answer layer can pick the right procedure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from madhya_kanoon_saathi.generation.crisis import ExampleIndex, prepare

MERITS = "merits"
REFERRAL_CONTACT = "nalsa_15100"

_RULES: tuple[str, ...] = (
    # who owns / whose right
    r"किसकी (जमीन|संपत्ति|प्रॉपर्टी|मकान|दुकान|खेत|हिस्सा)", r"(जमीन|मकान|संपत्ति|खेत) (किसकी|किसका) (है|होगी|होगा)",
    r"(हक|अधिकार|दावा) किसका", r"किसका (हक|अधिकार|दावा)", r"कौन सही (है|हैं)", r"कौन गलत",
    r"मेरा (हक|दावा|पक्ष) (बनता|सही|मजबूत) है", r"(जमीन|मकान|खेत) मेरी है (ना|न|क्या)",
    r"(पडोसी|भाई|चाचा|मालिक|किरायेदार|पति|पत्नी|ससुराल).{0,25}(गलत|सही) (है|हैं|किया)( ना| न)?\s*[?।]",
    # outcome prediction
    r"(केस|मुकदमा|मामला|दावा) (जीत|हार)", r"जीत (जाऊंगा|जाऊंगी|पाऊंगा|पाऊंगी|सकता|सकती)",
    r"(जीतूंगा|जीतूंगी|हारूंगा|हारूंगी)", r"फैसला (मेरे|हमारे) (पक्ष|हक) में",
    r"(सजा|जेल) (होगी|हो सकती|होगा|मिलेगी)", r"(जमानत|बेल) (मिलेगी|मिल जाएगी|मिल सकती)",
    r"(बच्चे|बच्चों|कस्टडी).{0,20}किसे (मिलेंगे|मिलेगी|मिलेगा)", r"किसे मिलेगी (कस्टडी|जमीन|संपत्ति)",
    r"kiski (zameen|jameen|property|sampatti|dukaan|makaan)", r"kaun sahi hai", r"kaun galat",
    r"\bkiska (haq|hak|adhikar|dawa)\b", r"\b(haq|hak) kiska\b", r"mera (haq|hak|dawa) (banta|sahi)",
    r"\b(case|mukadma|mukadama) (jeet|haar)", r"\bjeet (jaunga|jaungi|paunga|sakta|sakti)\b",
    r"\b(saza|sazaa|sajaa|jail) (hogi|hoga|ho sakti|milegi)\b", r"\b(bail|jamanat) (milegi|mil jayegi)\b",
    r"\bfaisla mere (paksh|haq|hak) mein\b", r"\bcustody kise\b",
    r"\bwho (owns|is right|is wrong|will win|gets (the )?(custody|land|property|house))\b",
    r"\b(can|will|would) i win\b", r"\bwin (the|my) case\b", r"\bin my favou?r\b",
    r"\bis (he|she|my \w+) (wrong|right|guilty)\b", r"\b(will|would) (he|she|they|i) (go to jail|be jailed|get bail)\b",
    r"\b(legally|rightfully) mine\b", r"\bwhose (land|property|house|plot) is\b",
    # advice on whether to litigate
    r"\bshould i (file|sue|go to court|take (him|her|them) to court)\b",
    r"(केस|मुकदमा|शिकायत) (करना|करूं) चाहिए", r"\b(case|mukadma) (karna|karun|karoon) chahiye\b",
    r"\b(which|who) of (my|the) .{0,30}(has the right|is entitled|gets)\b",
)  # fmt: skip
_COMPILED = tuple(re.compile(prepare(p)) for p in _RULES)

_DOMAINS: dict[str, tuple[str, ...]] = {
    "land": (r"(जमीन|खेत|मेड|सीमा|सीमांकन|कब्जा|नामांतरण|खसरा|पट्टा|प्लॉट)",
             r"\b(zameen|jameen|khet|med|seema|kabza|kabja|khasra|patta|plot|land|boundary|"
             r"demarcation|mutation)\b"),
    "family": (r"(तलाक|पत्नी|पति|कस्टडी|गुजारा|भरण|बंटवारा|वसीयत|विरासत|उत्तराधिकार|दहेज)",
               r"\b(talaq|divorce|custody|maintenance|gujara|batwara|will|inheritance|wife|husband|"
               r"dowry|succession)\b"),
    "criminal": (r"(एफआईआर|जमानत|जेल|सजा|पुलिस|चोरी|मारपीट|गिरफ्तार)",
                 r"\b(fir|bail|jamanat|jail|saza|sazaa|police|arrest\w*|theft|chori|guilty|crime)\b"),
    "sc_st": (r"(अत्याचार|अनुसूचित जाति|अनुसूचित जनजाति|sc/st)", r"\b(atrocit\w*|sc/st act)\b"),
}  # fmt: skip
_DOMAIN_RE = {d: tuple(re.compile(prepare(p)) for p in pats) for d, pats in _DOMAINS.items()}


@dataclass(frozen=True)
class DisputeResult:
    by_rule: bool
    by_embedding: bool
    margin: float | None
    domains: tuple[str, ...]

    @property
    def is_dispute(self) -> bool:
        return self.by_rule or self.by_embedding

    @property
    def referral_contact(self) -> str | None:
        return REFERRAL_CONTACT if self.is_dispute else None


def domains(text: str) -> tuple[str, ...]:
    t = prepare(text)
    found = tuple(d for d, pats in _DOMAIN_RE.items() if any(p.search(t) for p in pats))
    return found or ("other",)


def rule_hit(text: str) -> bool:
    t = prepare(text)
    return any(p.search(t) for p in _COMPILED)


def route(
    text: str, query_vec: np.ndarray | None = None, examples: ExampleIndex | None = None
) -> DisputeResult:
    """Flag merits questions; without a vector or examples, rules only."""
    margin = None
    by_emb = False
    if query_vec is not None and examples is not None:
        margin = examples.similarities(query_vec)[MERITS]
        by_emb = margin >= examples.threshold
    return DisputeResult(rule_hit(text), by_emb, margin, domains(text))


# Answer-side screen (review 2026-11-18): the prompt asks for procedure only, but only code can
# guarantee it. A generated block that judges merits or predicts an outcome is dropped.
_OUTCOME: tuple[str, ...] = (
    r"\byou (will|would|are likely to|can|should) (win|lose)\b", r"\byou are (right|wrong)\b",
    r"\b(is|are) (guilty|innocent)\b", r"\bwill be (convicted|acquitted|jailed|punished)\b",
    r"\b(belongs|belong) to you\b", r"\bthe (land|property|house|plot) is (yours|his|hers|theirs)\b",
    r"\byour (claim|case) is (strong|weak|valid)\b",
    r"आप (केस |मुकदमा )?(जीत|हार) (जाएंगे|जाएंगी|सकते|सकती)", r"आप सही (हैं|है)", r"आप गलत (हैं|है)",
    r"(जमीन|संपत्ति|मकान|खेत) (आपकी|उनकी|उसकी) है", r"(दोषी|निर्दोष) (है|हैं)", r"सजा (होगी|हो जाएगी)",
    r"आपका (हक|दावा) (बनता|मजबूत|सही) है",
    r"\baap (case )?(jeet|haar) (jaoge|jaenge|jayenge|sakte|sakti)\b", r"\baap sahi (ho|hain|hai)\b",
    r"\b(zameen|jameen|property|makaan) aapki hai\b", r"\b(saza|sazaa) (hogi|ho jayegi)\b",
)  # fmt: skip
_OUTCOME_RE = tuple(re.compile(prepare(p)) for p in _OUTCOME)


def judges_merits(answer_text: str) -> bool:
    """True if generated answer text says who is right / who owns / how a case will end."""
    t = prepare(answer_text)
    return any(p.search(t) for p in _OUTCOME_RE)  # question rules (rule_hit) would flag "who owns"
