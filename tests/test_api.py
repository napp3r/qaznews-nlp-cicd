import pytest
from fastapi.testclient import TestClient

from qaznews import api


@pytest.fixture(scope="module")
def client(artifacts):
    original = api.ARTIFACTS_DIR
    api.ARTIFACTS_DIR = artifacts
    with TestClient(api.app) as test_client:
        yield test_client
    api.ARTIFACTS_DIR = original


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_version_exposes_model_provenance(client):
    body = client.get("/version").json()
    assert body["model_version"] == "test"
    assert set(body["macro_f1"]) == {"kk", "ru"}


@pytest.mark.parametrize(
    ("text", "language", "topic"),
    [
        ("Депутаты мажилиса поддержали новый закон", "ru", "politics"),
        ("Сборная выиграла матч и вышла в финал", "ru", "sport"),
        ("Үкімет жаңа заң жобасын мақұлдады", "kk", "politics"),
        ("Теңге бағамы мен инфляция банктер үшін маңызды", "kk", "economy"),
        ("Mäjilis jaña zañ jobasyn maqūldady", "kk", "politics"),
    ],
)
def test_predict_returns_language_and_topic(client, text, language, topic):
    response = client.post("/predict", json={"text": text})
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == language
    assert body["topic"] == topic
    assert 0.0 <= body["confidence"] <= 1.0


@pytest.mark.parametrize("payload", [{}, {"text": ""}, {"text": "   "}, {"text": 5}])
def test_predict_rejects_invalid_input(client, payload):
    assert client.post("/predict", json=payload).status_code == 422
