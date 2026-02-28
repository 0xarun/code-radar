# Code Radar AI

Production-grade static code analysis platform that scans uploaded source repositories with **Semgrep**, enriches security findings with **Ollama LLM reasoning**, caches responses in **Redis**, and persists jobs/findings into **PostgreSQL**.

## Architecture (Clean Architecture)

```text
                +---------------------+
                |  FastAPI API Layer  |
                | /upload /jobs /...  |
                +----------+----------+
                           |
          +----------------+----------------+
          |                                 |
+---------v----------+           +----------v----------+
|  Services Layer    |           | Dashboard Layer     |
| semgrep/cache/llm  |           | Jinja2 UI + metrics |
+---------+----------+           +----------+----------+
          |                                 |
+---------v----------------+   +------------v---------+
| Workers (async queue)    |   | Core utilities/logging|
| job lifecycle pipeline   |   | config, hashing, zip  |
+---------+----------------+   +-----------------------+
          |
+---------v-----------------------------+
| Persistence & Infra                   |
| PostgreSQL (jobs/findings), Redis TTL |
+---------------------------------------+
```

## Folder Tree

```text
app/
  api/
    deps.py
    routes.py
  core/
    config.py
    logging.py
  services/
    cache_service.py
    job_service.py
    ollama_service.py
    scan_pipeline.py
    semgrep_service.py
  models/
    finding.py
    job.py
  schemas/
    health.py
    job.py
    upload.py
  db/
    base.py
    redis.py
    session.py
  workers/
    job_queue.py
    runner.py
  utils/
    archive.py
    hashing.py
    semgrep_parser.py
  templates/dashboard/
    index.html
    logs.html
  main.py
alembic/
  env.py
  versions/0001_initial.py
semgrep_rules/default.yml
Makefile
.env.example
requirements.txt
README.md
```

## Core Workflow

1. `POST /upload` accepts a ZIP repository.
2. Job created in PostgreSQL with `pending` state.
3. ZIP persisted to local `uploads/` and enqueued to background worker.
4. Worker safely extracts ZIP into `data/job_<id>/` (path traversal protected).
5. Semgrep runs in JSON mode against extracted tree.
6. Findings parsed and filtered to `HIGH/CRITICAL`.
7. For each finding hash (`file + rule + snippet`):
   - Redis lookup `llm:{hash}`.
   - Cache miss triggers Ollama API call (`/api/generate`) with retries + timeout.
8. Findings inserted in bulk into DB.
9. Job status updated with duration, total findings, cache hits.

## Setup Instructions (No Docker)

### Prerequisites
- Python 3.11+
- PostgreSQL running locally
- Redis running locally
- Semgrep CLI installed (`pipx install semgrep` or package manager)
- Ollama installed and running with model:
  - `ollama pull llama3:8b`

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` for your local services.

### DB Migration

```bash
make migrate
```

### Run App

```bash
make run
```

### Optional Dedicated Worker Process

```bash
make worker
```

> `make run` already starts an in-process async worker queue at startup for single-node local deployment.

## Endpoints

- `POST /upload` – upload ZIP and enqueue job.
- `GET /jobs/{id}` – job status and metrics.
- `GET /health` – DB/Redis/Ollama/Semgrep health.
- `GET /dashboard` – status dashboard with system metrics.
- `GET /dashboard/logs` – last 200 logs with filters.

## Example Request/Response

### Upload
```bash
curl -F "file=@repo.zip" http://localhost:8000/upload
```

```json
{
  "job_id": 3,
  "status": "queued",
  "message": "Repository uploaded and queued"
}
```

### Health
```json
{
  "db": "ok",
  "redis": "ok",
  "ollama": "ok",
  "semgrep": "ok"
}
```

## How Semgrep Works

- Executes configured rule set from `semgrep_rules/default.yml`.
- Runs with `--json` output.
- Parser normalizes fields and only keeps `HIGH`/`CRITICAL` severities.

## How Ollama Works

- HTTP call to `POST <OLLAMA_URL>/api/generate`.
- Prompt requests:
  - vulnerability explanation,
  - concrete fix,
  - severity rating,
  - max 200 words.
- Retries with backoff + timeout guarding.

## Caching Strategy (Redis)

- Key format: `llm:{hash}`.
- TTL: 24h (`REDIS_TTL_SECONDS=86400`).
- Cache-first path reduces repetitive LLM requests across jobs.

## Logging & Monitoring

- Structured JSON logs written to `logs/app.log`.
- Captures semgrep lifecycle, ollama calls, cache hits, db writes, job duration, and exceptions.
- `/dashboard/logs` renders last 200 lines with `level` + `job_id` filters.

## Performance Notes

- Async Ollama requests with semaphore-constrained concurrency.
- `asyncio.gather` for parallel enrichment.
- Bulk insert semantics via `session.add_all` + single commit.
- Worker queue enables non-blocking upload endpoint.

## Debug Mode

`DEBUG=True` enables:
- verbose logging level,
- dashboard debug markers,
- FastAPI debug behavior.

## Scaling Notes

- Run API and worker as separate processes (`make run` + `make worker`) for stronger isolation.
- Replace in-memory queue with Redis/RabbitMQ for horizontal workers.
- Add object storage for ZIP artifacts and archive retention policies.
- Add partitioning/retention strategy for `findings` table.

## Troubleshooting

- **Semgrep health = error**: verify `SEMGREP_BIN` in `.env` and executable path.
- **Ollama timeouts**: increase `OLLAMA_TIMEOUT_SECONDS` or reduce `MAX_LLM_CONCURRENCY`.
- **DB migration failure**: validate `DATABASE_URL` and PostgreSQL credentials.
- **Redis errors**: verify `REDIS_URL` and server memory policy.
- **No findings stored**: check semgrep rule coverage and severity mapping (`HIGH/CRITICAL`).
