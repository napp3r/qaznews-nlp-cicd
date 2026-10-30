# QazNews-NLP CI/CD

A small research prototype of the QazNews-NLP project with a complete CI/CD pipeline
(Assignment 5, Applied Software Development Project). The service detects the language of a
Kazakh or Russian news text, normalises Latin-script Kazakh and classifies the topic.

`data/news_sample.csv` is a hand-written demonstration corpus of 160 headlines, not real
published news. The metrics it produces show that the pipeline works; they say nothing about
how the method would perform on real news.

## Pipeline

Every commit on any branch is picked up by SCM polling and runs:

| Stage | Action | Branches |
| --- | --- | --- |
| Prepare | Derives image tags from the commit hash | all |
| Lint | `ruff check`, `ruff format --check` | all |
| Unit tests | `pytest` with JUnit report and a coverage threshold of 85% | all |
| Train and quality gate | Trains the model; macro-F1 must reach 0.80 (kk) and 0.85 (ru) | all |
| Build image | Builds the multi-stage `runtime` image | all |
| Smoke test | Starts the container and checks the live API | all |
| Push to Docker Hub | Pushes the commit tag and `latest` | `main` |
| Deploy to Kubernetes | Rolling update on kind, automatic rollback on failure | `main` |
| Verify deployment | Runs the smoke test in a pod against the Service | `main` |

## Run the service

```bash
docker build --target runtime -t qaznews-nlp .
docker run --rm -p 8000:8000 qaznews-nlp
curl -X POST localhost:8000/predict -H 'Content-Type: application/json' \
  -d '{"text": "Ұлттық банк базалық мөлшерлемені сақтады"}'
```

## Run the tests

```bash
docker build --target test -t qaznews-nlp:test .
docker run --rm qaznews-nlp:test
```

## Start the CI/CD environment

Requires Docker and kind.

```bash
cd jenkins
kind create cluster --config kind-cluster.yaml
kind get kubeconfig --internal --name qaznews > kubeconfig
cp .env.example .env                     # set JENKINS_ADMIN_PASSWORD
docker compose up -d --build
```

Open <http://localhost:8090>, log in as `admin` and run the `qaznews-nlp` job once. The first
run registers the polling trigger from the `Jenkinsfile`; later commits start builds on their own.
To enable the push stage, set `DOCKERHUB_ENABLED=true` and the two `DOCKERHUB_*` values in `.env`.

Jenkins runs on one machine and mounts the Docker socket, which gives it root-equivalent access
to the host. That is acceptable for this local demonstration only.
