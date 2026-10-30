"""Topic classifier: character n-gram TF-IDF with logistic regression."""

import csv
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from qaznews.preprocess import normalize

TOPICS = ("economy", "politics", "sport", "technology")
RANDOM_STATE = 42


@dataclass(frozen=True)
class Article:
    text: str
    lang: str
    topic: str


def load_dataset(path: Path) -> list[Article]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [Article(row["text"], row["lang"], row["topic"]) for row in csv.DictReader(handle)]


def build_pipeline() -> Pipeline:
    # Character n-grams tolerate Kazakh agglutination better than word tokens.
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    preprocessor=normalize,
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    sublinear_tf=True,
                ),
            ),
            ("clf", LogisticRegression(C=20.0, max_iter=2000, random_state=RANDOM_STATE)),
        ]
    )
