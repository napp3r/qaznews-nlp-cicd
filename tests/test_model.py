import json
from collections import Counter

import joblib

from qaznews import train as train_module
from qaznews.model import TOPICS, load_dataset
from qaznews.preprocess import detect_language
from qaznews.train import gate_failures, train


def test_dataset_is_balanced_across_language_and_topic(data_path):
    counts = Counter((a.lang, a.topic) for a in load_dataset(data_path))
    assert set(counts) == {(lang, topic) for lang in ("kk", "ru") for topic in TOPICS}
    assert len(set(counts.values())) == 1


def test_dataset_language_labels_match_detector(data_path):
    mismatched = [a.text for a in load_dataset(data_path) if detect_language(a.text) != a.lang]
    assert mismatched == []


def test_dataset_has_no_duplicate_texts(data_path):
    texts = [a.text for a in load_dataset(data_path)]
    assert len(texts) == len(set(texts))


def test_metrics_file_records_data_fingerprint_and_gate(artifacts):
    metrics = json.loads((artifacts / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["model_version"] == "test"
    assert len(metrics["data_sha256"]) == 64
    assert metrics["passed"] is True


def test_gate_reports_each_language_below_target():
    failures = gate_failures({"kk": 0.79, "ru": 0.90})
    assert len(failures) == 1
    assert failures[0].startswith("kk")


def test_gate_fails_when_a_language_is_missing():
    assert len(gate_failures({"ru": 0.99})) == 1


def test_training_is_reproducible(data_path, tmp_path):
    first = train(data_path, tmp_path / "a", model_version="x")
    second = train(data_path, tmp_path / "b", model_version="x")
    assert first == second

    sample = ["Цены на нефть выросли", "Құрама матчта жеңді"]
    probabilities_a = joblib.load(tmp_path / "a" / "model.joblib").predict_proba(sample)
    probabilities_b = joblib.load(tmp_path / "b" / "model.joblib").predict_proba(sample)
    assert (probabilities_a == probabilities_b).all()


def _run_cli(monkeypatch, data_path, out_dir):
    argv = ["train", "--data", str(data_path), "--out", str(out_dir), "--model-version", "cli"]
    monkeypatch.setattr("sys.argv", argv)
    return train_module.main()


def test_cli_exits_zero_when_gate_passes(monkeypatch, data_path, tmp_path):
    assert _run_cli(monkeypatch, data_path, tmp_path) == 0


def test_cli_exits_nonzero_when_gate_fails(monkeypatch, data_path, tmp_path):
    monkeypatch.setattr(train_module, "MIN_MACRO_F1", {"kk": 1.01, "ru": 0.85})
    assert _run_cli(monkeypatch, data_path, tmp_path) == 1
