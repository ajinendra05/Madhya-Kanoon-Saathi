"""Query-side jurisdiction guard (DEC-016, DEC-033 item 5, DEC-038).

Retrieval already admits only national and MP chunks (``retrieval/filters.py``). This module catches
the other half: a question about **another state's** law ("Rajasthan mein kiraya kanoon", "UP mein
dakhil kharij") must not be answered silently from MP law. The answer layer then says the bot covers
Madhya Pradesh and central law only and refers the user to free legal aid (abstention rule).

A question that names MP as well ("UP se MP aaya hoon") stays in scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from madhya_kanoon_saathi.generation.crisis import prepare

MP = "MP"
# state/UT -> names (English, Hinglish, Hindi); short forms only where unambiguous in context
_STATES: dict[str, tuple[str, ...]] = {
    MP: (
        r"madhya ?pradesh", r"\bm\.? ?p\.?\b", r"मध्य ?प्रदेश", r"म\.? ?प्र\.?", r"\bmp\b",
        # district headquarters: a user in Jabalpur is in scope (golden GS-054)
        r"\b(bhopal|indore|jabalpur|gwalior|ujjain|sagar|rewa|satna|ratlam|dewas|katni|"
        r"chhindwara|khandwa|khargone|burhanpur|vidisha|sehore|hoshangabad|narmadapuram|"
        r"betul|shivpuri|guna|morena|bhind|datia|damoh|chhatarpur|tikamgarh|panna|sidhi|"
        r"singrauli|shahdol|mandla|balaghat|seoni|dhar|jhabua|alirajpur|barwani|mandsaur|"
        r"neemuch|shajapur|rajgarh|raisen|harda|dindori|anuppur|umaria|niwari|maihar)\b",
        r"(भोपाल|इंदौर|इन्दौर|जबलपुर|ग्वालियर|उज्जैन|सागर|रीवा|सतना|रतलाम|देवास|कटनी|छिंदवाड़ा|"
        r"खंडवा|खरगोन|बुरहानपुर|विदिशा|सीहोर|होशंगाबाद|नर्मदापुरम|बैतूल|शिवपुरी|गुना|मुरैना|भिंड|"
        r"दतिया|दमोह|छतरपुर|टीकमगढ़|पन्ना|सीधी|सिंगरौली|शहडोल|मंडला|बालाघाट|सिवनी|धार|झाबुआ|"
        r"बड़वानी|मंदसौर|नीमच|शाजापुर|राजगढ़|रायसेन|हरदा|डिंडौरी|अनूपपुर|उमरिया|निवाड़ी|मैहर)",
    ),
    "AP": (r"andhra ?pradesh", r"आंध्र ?प्रदेश"),
    "AR": (r"arunachal", r"अरुणाचल"),
    "AS": (r"\bassam\b", r"असम"),
    "BR": (r"\bbihar\b", r"बिहार"),
    "CG": (r"chh?att?isgarh", r"छत्तीसगढ"),
    "GA": (r"\bgoa\b", r"गोवा"),
    "GJ": (r"gujarat", r"गुजरात"),
    "HR": (r"haryana", r"हरियाणा"),
    "HP": (r"himachal", r"हिमाचल"),
    "JH": (r"jharkhand", r"झारखंड"),
    "KA": (r"karnataka", r"कर्नाटक"),
    "KL": (r"kerala", r"केरल"),
    "MH": (r"maharashtra", r"महाराष्ट्र", r"\bmumbai\b", r"मुंबई", r"\bpune\b"),
    "MN": (r"manipur", r"मणिपुर"),
    "ML": (r"meghalaya", r"मेघालय"),
    "MZ": (r"mizoram", r"मिजोरम"),
    "NL": (r"nagaland", r"नागालैंड"),
    "OD": (r"odisha|orissa", r"ओडिशा|उड़ीसा|उडीसा"),
    "PB": (r"punjab", r"पंजाब"),
    "RJ": (r"rajasthan", r"राजस्थान", r"\bjaipur\b", r"जयपुर"),
    "SK": (r"sikkim", r"सिक्किम"),
    "TN": (r"tamil ?nadu", r"तमिलनाडु", r"\bchennai\b"),
    "TS": (r"telangana", r"तेलंगाना", r"\bhyderabad\b"),
    "TR": (r"tripura", r"त्रिपुरा"),
    "UP": (r"uttar ?pradesh", r"उत्तर ?प्रदेश", r"\bu\.?p\.?\b", r"यूपी", r"\blucknow\b", r"लखनऊ"),
    "UK": (r"uttarakhand", r"उत्तराखंड"),
    "WB": (r"west ?bengal", r"पश्चिम ?बंगाल", r"\bkolkata\b", r"कोलकाता"),
    "DL": (r"\bdelhi\b", r"दिल्ली"),
    "JK": (r"jammu|kashmir", r"जम्मू|कश्मीर"),
    "LA": (r"\bladakh\b", r"लद्दाख"),
    "PY": (r"puducherry|pondicherry", r"पुडुचेरी"),
    "CH": (r"chandigarh", r"चंडीगढ"),
}  # fmt: skip
_COMPILED = {s: tuple(re.compile(prepare(p)) for p in pats) for s, pats in _STATES.items()}
# "delhi" in "New Delhi, the 17th May" (central gazette headers) is not the user's state
_CENTRAL_CONTEXT = re.compile(r"(new delhi|नई दिल्ली)")


@dataclass(frozen=True)
class JurisdictionCheck:
    states: tuple[str, ...]  # states/UTs named in the question

    @property
    def other_state_only(self) -> bool:
        """True if the question names another state and not MP: answer abstains for state law."""
        return bool(self.states) and MP not in self.states


def check(text: str) -> JurisdictionCheck:
    t = _CENTRAL_CONTEXT.sub(" ", prepare(text))
    return JurisdictionCheck(
        tuple(s for s, pats in _COMPILED.items() if any(p.search(t) for p in pats))
    )
