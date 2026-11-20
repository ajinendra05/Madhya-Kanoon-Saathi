""" "What can you help with?" detection and the topic list (DEC-082).

A message that asks which topics the bot covers ("aap mujhe kis kis topic me help kar sakte hai",
"आप किन विषयों पर जानकारी देते हैं", "what can you help me with") gets the topic list from
``data/help_topics.json`` instead of a retrieval + LLM answer (free, deterministic). The list is
appended to the "no reliable answer" abstention so users learn what they *can* ask.

Detection is rules only: an *asking-about-scope* cue (kis kis / kaun se / what can you ...) together
with a *help* cue (help / madad / jaankari / topics ...), and no named legal subject, so
"RTI ke liye kya kya documents chahiye" still goes to retrieval.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from madhya_kanoon_saathi.common.normalize import normalize

MAX_WORDS = 16

_SCOPE = re.compile(
    r"kis\s*kis|kis\s+(?:topic|vishay|cheez|chiz|baat|area|kshetra|mamle|maamle)|"
    r"kaun\s*kaun|kaun\s+se|kon\s*kon|kon\s+se|kin\s+(?:topic|vishay|cheez|chiz|baat|maamlon|mamlon)|"
    r"kya\s*kya|kya\s+kar\s+sakt|kya\s+help|kaise\s+(?:help|madad)|"
    r"\bwhich\s+(?:topics?|areas?|subjects?|things|questions|laws)|"
    r"\bwhat\s+(?:topics?|areas?|subjects?|kind|sort|type|things|questions|laws)|"
    r"\bwhat\s+(?:can|do)\s+you|\bhow\s+can\s+you\s+help|"
    r"किस\s*किस|किस\s+(?:विषय|टॉपिक|चीज़|चीज|बात|मामल|क्षेत्र)|किन|कौन\s*कौन|कौन\s+से|"
    r"क्या\s*क्या|क्या\s+कर\s+सकत|कैसे\s+(?:मदद|सहायता)",
    re.IGNORECASE,
)
_HELP = re.compile(
    r"\bhelp|madad|sahayata|sahayta|jaankari|jankari|jawab|bata\s+sakt|\btopics?\b|vishay|"
    r"\bcover|\banswer|\bknow\b|\byou\s+do\b|kar\s+sakt|"
    r"मदद|सहायता|जानकारी|जवाब|बता\s+सकत|विषय|टॉपिक|कर\s+सकत",
    re.IGNORECASE,
)
# a named legal subject means a real question, not a scope question
_SUBJECT = re.compile(
    r"\brti\b|soochna|suchna|consumer|upbhokta|wage|vetan|mazdoori|majdoori|salary|kiraya|"
    r"kirayedar|\brent|tenan|landlord|zameen|jameen|\bland\b|seemankan|simankan|demarcation|"
    r"legal\s+aid|lok\s+adalat|svanidhi|swanidhi|e-?shram|\bshram\b|bonus|section|dhara|"
    r"\bact\b|adhiniyam|niyam|\brules?\b|"
    r"सूचना|उपभोक्ता|मज़दूरी|मजदूरी|वेतन|किराय|ज़मीन|जमीन|सीमांकन|लोक\s+अदालत|स्वनिधि|श्रम|"
    r"धारा|अधिनियम|नियम",
    re.IGNORECASE,
)


def is_help_request(question: str) -> bool:
    """True when the message asks which topics the bot can help with (see module docstring)."""
    text = normalize(question, fold_nukta=False).strip()
    if not text or len(text.split()) > MAX_WORDS:
        return False
    return bool(_SCOPE.search(text) and _HELP.search(text) and not _SUBJECT.search(text))


def topic_lines(topics: Mapping[str, Any], lang: str) -> list[str]:
    return [f"• {t[lang]}" for t in topics["topics"]]


def render(topics: Mapping[str, Any], lang: str, *, abstain: bool = False) -> str:
    """The topic list in ``lang``; ``abstain`` uses the shorter intro and no outro."""
    if topics.get("status") != "approved":
        raise PermissionError("user-facing wording is not approved yet (help_topics.json)")
    intro = topics["abstain_intro" if abstain else "intro"][lang]
    lines = [intro, *topic_lines(topics, lang)]
    if not abstain:
        lines += ["", topics["outro"][lang]]
    return "\n".join(lines)
