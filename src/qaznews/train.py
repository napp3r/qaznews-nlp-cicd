"""Train the topic model, evaluate it per language and enforce a quality gate.

Exits with a non-zero code when a macro-F1 target is missed, which stops the
Docker build and therefore the CI pipeline.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import joblib
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from qaznews.model import RANDOM_STATE, Article, build_pipeline, load_dataset

# Targets from requirement NFR1 of the project.
MIN_MACRO_F1 = {"kk": 0.80, "ru": 0.85}
CV_FOLDS = 5


def evaluate(articles: list[Article]) -> dict:
    """Return per-language macro-F1 from out-of-fold predictions."""
    texts = [a.text for a in articles]
    topics = [a.topic for a in articles]
    strata = [f"{a.lang}-{a.topic}" for a in articles]
    folds = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    predicted = cross_val_predict(build_pipeline(), texts, topics, cv=folds.split(texts, strata))

    scores = {}
    for lang in sorted({a.lang for a in articles}):
        index = [i for i, a in enumerate(articles) if a.lang == lang]
        scores[lang] = round(
            float(
                f1_score(
                    [topics[i] for i in index],
                    [predicted[i] for i in index],
                    average="macro",
                )
            ),
            4,
        )
    return scores


def gate_failures(scores: dict) -> list[str]:
    return [
        f"{lang}: macro-F1 {scores.get(lang, 0.0):.4f} < {target:.2f}"
        for lang, target in MIN_MACRO_F1.items()
        if scores.get(lang, 0.0) < target
    ]


def train(data_path: Path, out_dir: Path, model_version: str) -> dict:
    articles = load_dataset(data_path)
    scores = evaluate(articles)

    model = build_pipeline().fit([a.text for a in articles], [a.topic for a in articles])
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / "model.joblib")

    metrics = {
        "model_version": model_version,
        "n_articles": len(articles),
        "cv_folds": CV_FOLDS,
        "macro_f1": scores,
        "min_macro_f1": MIN_MACRO_F1,
        "data_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "passed": not gate_failures(scores),
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/news_sample.csv"))
    parser.add_argument("--out", type=Path, default=Path("artifacts"))
    parser.add_argument("--model-version", default="dev")
    args = parser.parse_args()

    metrics = train(args.data, args.out, args.model_version)
    print(json.dumps(metrics, indent=2))
    failures = gate_failures(metrics["macro_f1"])
    if failures:
        print("Quality gate failed: " + "; ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
