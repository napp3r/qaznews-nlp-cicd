from pathlib import Path

import pytest

from qaznews.train import train

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "news_sample.csv"


@pytest.fixture(scope="session")
def data_path() -> Path:
    return DATA_PATH


@pytest.fixture(scope="session")
def artifacts(tmp_path_factory) -> Path:
    out_dir = tmp_path_factory.mktemp("artifacts")
    train(DATA_PATH, out_dir, model_version="test")
    return out_dir
