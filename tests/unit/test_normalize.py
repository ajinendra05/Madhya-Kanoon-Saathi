import unicodedata

from madhya_kanoon_saathi.common.normalize import NUKTA, normalize


def test_nfc_makes_composed_and_decomposed_equal() -> None:
    # Latin é composed vs e + combining acute
    assert normalize("é") == normalize("é") == "é"


def test_nukta_folded_in_both_spellings() -> None:
    precomposed = "\u095bरूरी"  # ज\u093cरूरी with U+095B
    decomposed = "ज\u093cरूरी"  # ज + nukta
    plain = "जरूरी"  # जरूरी
    assert normalize(precomposed) == normalize(decomposed) == plain


def test_all_precomposed_nukta_letters_fold_to_base() -> None:
    for cp in (0x0929, 0x0931, 0x0934, *range(0x0958, 0x0960)):
        out = normalize(chr(cp))
        assert NUKTA not in out
        assert out == unicodedata.normalize("NFD", chr(cp))[0]


def test_fold_nukta_off_keeps_one_canonical_form() -> None:
    a = normalize("\u095b", fold_nukta=False)
    b = normalize("ज\u093c", fold_nukta=False)
    assert a == b and NUKTA in a


def test_invisible_characters_removed() -> None:
    # ZWJ/ZWNJ inside a conjunct, BOM, soft hyphen, ZWSP
    assert normalize("\ufeffक्\u200dष\u00adा\u200b") == "क्षा"


def test_collapse_space_optional() -> None:
    s = "  धारा \n 8\t(1)  "
    assert normalize(s) == s
    assert normalize(s, collapse_space=True) == "धारा 8 (1)"


def test_idempotent() -> None:
    s = "\ufeffज़मीन  का   ख़सरा\u200d"
    once = normalize(s, collapse_space=True)
    assert normalize(once, collapse_space=True) == once
