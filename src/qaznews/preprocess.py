"""Text normalisation and language detection for Kazakh and Russian news.

Kazakh is being moved from Cyrillic to a Latin alphabet (2021 version), so the
same news can arrive in either script. Latin text is converted to Cyrillic
before classification, which lets one model cover both scripts.
"""

import re

KAZAKH_ONLY_LETTERS = frozenset("әғқңөұүһі")
# Some Kazakh sentences use only letters shared with Russian; these words settle them.
KAZAKH_FUNCTION_WORDS = frozenset({"және", "мен", "пен", "бен", "туралы", "бойынша"})

# Kazakh Latin alphabet (2021) to Cyrillic. Where one Latin letter covers two Cyrillic
# letters (h for х and һ), the more frequent reading is used.
# fmt: off
LATIN_TO_CYRILLIC = {
    "ş": "ш", "ç": "ч", "ä": "ә", "ö": "ө", "ü": "ү", "ğ": "ғ", "ū": "ұ", "ñ": "ң",
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х", "i": "і",
    "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ",
    "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "y": "ы", "z": "з",
}
# fmt: on
# "q" marks Kazakh only outside the English "qu" digraph.
_KAZAKH_LATIN_MARKER = re.compile(r"[äöüğūñş]|q(?!u)")

_URL = re.compile(r"https?://\S+|www\.\S+")
_NON_WORD = re.compile(r"[^\w\s-]", re.UNICODE)
_SPACES = re.compile(r"\s+")


def is_kazakh_latin(text: str) -> bool:
    """Return True for mostly Latin text that carries Kazakh-specific letters."""
    lowered = text.lower()
    latin = sum("a" <= ch <= "z" or ch in LATIN_TO_CYRILLIC for ch in lowered)
    cyrillic = sum("а" <= ch <= "я" or ch == "ё" or ch in KAZAKH_ONLY_LETTERS for ch in lowered)
    return latin > cyrillic and _KAZAKH_LATIN_MARKER.search(lowered) is not None


def latin_to_cyrillic(text: str) -> str:
    # Lower-cased "İ" is "i" plus a combining dot; it stands for Cyrillic "и".
    lowered = text.lower().replace("i\u0307", "и")
    return "".join(LATIN_TO_CYRILLIC.get(ch, ch) for ch in lowered)


def normalize(text: str) -> str:
    """Lower-case, drop URLs and punctuation, and unify the Kazakh script."""
    cleaned = _URL.sub(" ", text.lower().replace("ё", "е"))
    if is_kazakh_latin(cleaned):
        cleaned = latin_to_cyrillic(cleaned)
    cleaned = _NON_WORD.sub(" ", cleaned)
    return _SPACES.sub(" ", cleaned).strip()


def detect_language(text: str) -> str:
    """Return "kk", "ru" or "unknown" from alphabet and function-word features."""
    normalized = normalize(text)
    letters = [ch for ch in normalized if ch.isalpha()]
    if not letters:
        return "unknown"
    if any(ch in KAZAKH_ONLY_LETTERS for ch in letters):
        return "kk"
    if KAZAKH_FUNCTION_WORDS.intersection(normalized.split()):
        return "kk"
    cyrillic = sum("а" <= ch <= "я" for ch in letters)
    return "ru" if cyrillic / len(letters) > 0.5 else "unknown"
