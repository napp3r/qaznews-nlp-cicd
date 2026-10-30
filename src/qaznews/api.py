"""REST API that serves the trained topic model."""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from qaznews import __version__
from qaznews.preprocess import detect_language

ARTIFACTS_DIR = Path(os.environ.get("QAZNEWS_ARTIFACTS", "artifacts"))


class ArticleIn(BaseModel):
    text: str = Field(min_length=3, max_length=20_000, pattern=r"\S")


class Prediction(BaseModel):
    language: str
    topic: str
    confidence: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = joblib.load(ARTIFACTS_DIR / "model.joblib")
    app.state.metrics = json.loads((ARTIFACTS_DIR / "metrics.json").read_text(encoding="utf-8"))
    yield


app = FastAPI(title="QazNews-NLP API", version=__version__, lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/version")
def version(request: Request) -> dict:
    metrics = request.app.state.metrics
    return {
        "api_version": __version__,
        "model_version": metrics["model_version"],
        "macro_f1": metrics["macro_f1"],
        "data_sha256": metrics["data_sha256"],
    }


@app.post("/predict")
def predict(article: ArticleIn, request: Request) -> Prediction:
    model = request.app.state.model
    probabilities = model.predict_proba([article.text])[0]
    best = int(probabilities.argmax())
    return Prediction(
        language=detect_language(article.text),
        topic=str(model.classes_[best]),
        confidence=round(float(probabilities[best]), 4),
    )
