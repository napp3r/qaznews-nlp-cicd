"""Smoke test for a running API: used after the container start and after the rollout."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

SAMPLE_TEXT = "Сборная Казахстана выиграла матч и вышла в финал"


def call(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def wait_until_healthy(base_url: str, attempts: int, delay: float) -> None:
    for attempt in range(1, attempts + 1):
        try:
            if call(f"{base_url}/health") == {"status": "ok"}:
                return
        except (urllib.error.URLError, OSError):
            pass
        if attempt < attempts:
            time.sleep(delay)
    raise SystemExit(f"{base_url} did not become healthy after {attempts} attempts")


def run(base_url: str, attempts: int = 30, delay: float = 1.0) -> dict:
    wait_until_healthy(base_url, attempts, delay)
    prediction = call(f"{base_url}/predict", {"text": SAMPLE_TEXT})
    if prediction["language"] != "ru" or prediction["topic"] != "sport":
        raise SystemExit(f"Unexpected prediction: {prediction}")
    return {"version": call(f"{base_url}/version"), "prediction": prediction}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    print(json.dumps(run(args.url.rstrip("/")), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
