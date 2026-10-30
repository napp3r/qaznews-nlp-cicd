import pytest

from qaznews import smoke


def _fake_api(language="ru", topic="sport", unhealthy_calls=0):
    calls = {"health": 0}

    def call(url, payload=None):
        if url.endswith("/health"):
            calls["health"] += 1
            if calls["health"] <= unhealthy_calls:
                raise OSError("connection refused")
            return {"status": "ok"}
        if url.endswith("/version"):
            return {"model_version": "abc"}
        return {"language": language, "topic": topic, "confidence": 0.9}

    return call


def test_run_returns_version_and_prediction(monkeypatch):
    monkeypatch.setattr(smoke, "call", _fake_api())
    result = smoke.run("http://api", delay=0)
    assert result["version"] == {"model_version": "abc"}


def test_run_waits_for_the_service_to_start(monkeypatch):
    monkeypatch.setattr(smoke, "call", _fake_api(unhealthy_calls=2))
    assert smoke.run("http://api", attempts=3, delay=0)["prediction"]["topic"] == "sport"


def test_run_fails_when_the_service_never_starts(monkeypatch):
    monkeypatch.setattr(smoke, "call", _fake_api(unhealthy_calls=99))
    with pytest.raises(SystemExit, match="did not become healthy"):
        smoke.run("http://api", attempts=2, delay=0)


def test_run_fails_on_a_wrong_prediction(monkeypatch):
    monkeypatch.setattr(smoke, "call", _fake_api(topic="economy"))
    with pytest.raises(SystemExit, match="Unexpected prediction"):
        smoke.run("http://api", delay=0)
