import pytest

from qaznews.preprocess import detect_language, is_kazakh_latin, latin_to_cyrillic, normalize


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Мәжіліс заң жобасын мақұлдады", "kk"),
        ("Мажилис одобрил законопроект", "ru"),
        ("Mäjilis zañ jobasyn maqūldady", "kk"),
        ("Университет жасанды интеллект пен робототехника зертханасын ашты", "kk"),
        ("The quick brown fox", "unknown"),
        ("Breaking news from London", "unknown"),
        ("12345 !!!", "unknown"),
        ("", "unknown"),
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_normalize_removes_urls_and_punctuation():
    assert normalize("Курс тенге: https://kase.kz/x вырос!!!") == "курс тенге вырос"


def test_normalize_unifies_yo():
    assert normalize("Ещё") == "еще"


def test_normalize_keeps_hyphenated_terms():
    assert normalize("Премьер-министр") == "премьер-министр"


def test_normalize_converts_kazakh_latin_to_cyrillic():
    assert normalize("Qazaqstan") == "қазақстан"


def test_latin_to_cyrillic_handles_kazakh_letters():
    assert latin_to_cyrillic("Maqūldady şäñ") == "мақұлдады шәң"


def test_latin_to_cyrillic_handles_dotted_capital_i():
    assert latin_to_cyrillic("İran") == "иран"


def test_english_text_is_not_treated_as_kazakh_latin():
    assert not is_kazakh_latin("the central bank raised rates")
