# Stages: base -> test (lint and unit tests) -> train (model and quality gate) -> runtime.
FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --root-user-action=ignore -r requirements.txt

FROM base AS test
COPY requirements-dev.txt pyproject.toml ./
RUN pip install --root-user-action=ignore -r requirements-dev.txt
COPY src ./src
COPY data ./data
COPY tests ./tests
CMD ["pytest"]

FROM base AS train
ARG MODEL_VERSION=dev
COPY src ./src
COPY data ./data
# A failed quality gate exits non-zero and aborts the image build.
RUN python -m qaznews.train --out artifacts --model-version "$MODEL_VERSION"

FROM base AS runtime
ARG MODEL_VERSION=dev
LABEL org.opencontainers.image.title="qaznews-nlp" \
      org.opencontainers.image.version="$MODEL_VERSION"
RUN useradd --system --uid 10001 --no-create-home app
COPY src ./src
COPY --from=train /app/artifacts ./artifacts
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "qaznews.api:app", "--host", "0.0.0.0", "--port", "8000"]
