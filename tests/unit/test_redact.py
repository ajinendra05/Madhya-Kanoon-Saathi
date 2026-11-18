"""Redaction before storage or logs (DEC-029, DEC-033 item 4, DEC-076)."""

import pytest

from madhya_kanoon_saathi.common.redact import redact


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("mera number 98765 43210 hai", "mera number [PHONE] hai"),
        ("call +91-9876543210 please", "call [PHONE] please"),
        ("आधार 2345 6789 0123 है", "आधार [AADHAAR] है"),
        ("card 4111 1111 1111 1111 se payment", "card [CARD] se payment"),
        ("mail me at ram.kumar@gmail.com", "mail me at [EMAIL]"),
        ("UPI id ramkumar@okaxis par bheja", "UPI id [UPI] par bheja"),
        ("PAN ABCDE1234F galat hai", "PAN [PAN] galat hai"),
        ("account no 123456789012345 band hai", "account no [ACCOUNT] band hai"),
        ("फ़ोन ९८७६५४३२१० पर", "फ़ोन [PHONE] पर"),  # Devanagari digits
    ],
)
def test_pii_placeholders(text: str, expected: str) -> None:
    assert redact(text).text == expected


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("मैं दलित हूँ, मेरी ज़मीन पर कब्ज़ा है", "CASTE"),
        ("hum OBC hain, certificate kaise banega", "CASTE"),
        ("मैं आदिवासी हूँ और वन अधिकार चाहिए", "CASTE"),
        ("I am a Muslim tenant and the landlord refuses", "RELIGION"),
        ("मैं विकलांग हूँ, पेंशन मिलेगी?", "DISABILITY"),
        ("my son is blind, school denied admission", "DISABILITY"),
        ("मुझे एचआईवी है, कंपनी ने निकाल दिया", "HEALTH"),
        ("I am pregnant and my employer fired me", "HEALTH"),
    ],
)
def test_sensitive_disclosures_are_replaced(text: str, label: str) -> None:
    r = redact(text)
    assert f"[{label}]" in r.text and r.sensitive
    assert r.found[label] >= 1


@pytest.mark.parametrize(
    "text",
    [
        "जाति प्रमाण पत्र कैसे बनवाएँ?",  # a service, not a disclosure
        "SC/ST Act ke tahat shikayat kahan karein",
        "Hindu Succession Act mein beti ka hissa",
        "विकलांगता प्रमाण पत्र के लिए आवेदन",
        "disability certificate kaise milega",
        "RTI fee kitni hai, 10 rupaye?",
        "मजदूरी 12575 रुपये प्रति माह",  # amounts are not account numbers
        "helpline 1930 aur 112",
    ],
)
def test_topics_and_amounts_are_kept(text: str) -> None:
    r = redact(text)
    assert r.text == text and not r.found


def test_counts_only_never_values() -> None:
    r = redact("98765 43210 aur 91234 56789, main dalit hoon")
    assert r.found == {"PHONE": 2, "CASTE": 1}
    assert "98765" not in r.text and "dalit" not in r.text
