import pytest

from madhya_kanoon_saathi.eval.ocr_metrics import edit_distance, error_rate, score


@pytest.mark.parametrize(
    ("a", "b", "d"),
    [
        ("", "", 0),
        ("abc", "", 3),
        ("", "ab", 2),
        ("kitten", "sitting", 3),
        ("धारा", "धरा", 1),
        ("abc", "abc", 0),
    ],
)
def test_edit_distance(a: str, b: str, d: int) -> None:
    assert edit_distance(a, b) == d
    assert edit_distance(b, a) == d


def test_error_rate_empty_reference() -> None:
    assert error_rate("", "") == 0.0
    assert error_rate("", "x") == 1.0


def test_perfect_and_wrong_hypothesis() -> None:
    s = score("धारा 8 (1)", "धारा 8 (1)")
    assert s.cer_raw == s.wer_raw == s.cer_norm == s.wer_norm == 0.0
    assert s.ref_chars == len("धारा 8 (1)") and s.ref_words == 3
    assert score("धारा 8", "धारा 9").cer_raw == pytest.approx(1 / 6)
    assert score("धारा 8", "धारा 9").wer_raw == pytest.approx(1 / 2)


def test_whitespace_differences_ignored() -> None:
    assert score("धारा  8\n(1)", " धारा 8 (1) ").cer_raw == 0.0


def test_nukta_and_invisibles_count_raw_but_not_normalised() -> None:
    ref = "ज़मीन का ख़सरा"
    hyp = "जमीन का खसरा‍"  # nukta dropped (OCR habit) + stray ZWJ
    s = score(ref, hyp)
    assert s.cer_raw > 0
    assert s.cer_norm == 0.0 and s.wer_norm == 0.0


def test_matra_counts_as_one_character() -> None:
    # missing ा (one code point) on a 4-code-point word
    assert score("धारा", "धरा").cer_raw == pytest.approx(1 / 4)
