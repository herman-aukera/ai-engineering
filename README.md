# AI Engineering Coursework

This repository contains the LIDR AI Engineering coursework.

## Current submission

Active project:

```text
estimador-cag/
```

Current branch:

```text
gg-session-08-pgvector-search
```

Current deliverable:

```text
Session 08 — pgvector semantic search baseline
```

## What this branch delivers

This branch upgrades the historical-budget embedding pipeline into a persisted semantic search baseline.

It uses PostgreSQL plus pgvector to store budget documents and structural chunks, embeds those chunks with OpenAI, and exposes retrieval through a public `/search` endpoint.

The goal is not to tune vector indexes yet. The goal is to create a measurable, reproducible retrieval baseline before adding HNSW, IVFFlat, metadata filters, Streamlit search UI, or search metrics dashboards.

## Required deliverables

```text
docker-compose.yml
estimador-cag/alembic.ini
estimador-cag/alembic/
estimador-cag/app/persistence/
estimador-cag/app/embedding_pipeline/ingestion_service.py
estimador-cag/app/embedding_pipeline/search_service.py
estimador-cag/app/routers/search.py
estimador-cag/query_examples.py
estimador-cag/output_examples.txt
```

The committed `output_examples.txt` was generated from a real Docker Compose run with the FastAPI service, PostgreSQL, pgvector, Alembic migration, OpenAI embeddings, one example corpus ingest, and five `/search` calls.

## Main Session 08 additions

```text
documents table
chunks table
pgvector extension
async SQLAlchemy persistence
async Alembic migration baseline
persistent /embeddings/ingest endpoint
semantic /search endpoint
Docker Compose ai_service
query_examples.py
output_examples.txt
DB-backed opt-in integration tests
```

## Repository map

```text
.
├── estimador-cag/      Active estimator project
├── docs/               Shared notes and sample files
├── scripts/            Helper scripts
├── docker-compose.yml  Root compose file with postgres, redis, and ai_service
└── README.md           Current repository review guide
```

## Run the active project with Docker Compose

```bash
cd /workspaces/ai-engineering

docker compose up -d postgres redis ai_service
docker compose exec -T ai_service uv run alembic upgrade head
```

Health check:

```bash
docker compose exec -T ai_service python -c "import json, urllib.request; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8000/health', timeout=10).read().decode('utf-8')), indent=2))"
```

Dry-run the required queries:

```bash
docker compose run --rm ai_service uv run python query_examples.py --dry-run
```

Run the real workflow after configuring `OPENAI_API_KEY`:

```bash
docker compose run --rm ai_service uv run python query_examples.py --ingest-example-corpus
```

## API endpoints added or upgraded

```text
POST /embeddings/ingest
POST /search
```

`POST /embeddings/ingest` persists one source document and its embedded chunks. Duplicate source paths return `409` with the existing `document_id`.

`POST /search` embeds a query once and returns the nearest persisted chunks by pgvector cosine distance.

## Why this schema

The implementation uses two tables:

```text
documents
chunks
```

`documents` stores source-level identity and document metadata.

`chunks` stores the searchable units, their text, embeddings, metadata, and the foreign key to the source document.

Chunk metadata is stored as JSONB because chunk fields evolve quickly across experiments. JSONB lets the project add retrieval metadata such as sector, country, tech stack, complexity, year, and token count without a migration for every new key.

## Why no vector index yet

The first Session 08 baseline intentionally uses sequential pgvector search without HNSW or IVFFlat.

That keeps behavior easy to explain and measure before adding index-specific tuning. A vector index should be added later only after observing corpus size, latency, recall needs, write patterns, metadata filter needs, and chosen operator class.

## Known limitations

Out-of-domain queries still return nearest neighbors because the current `/search` endpoint does not apply a similarity threshold.

This is visible in `output_examples.txt` and is useful baseline evidence. A later slice can add a maximum distance threshold or confidence label.

## Extra-mile roadmap

```text
E0 Fix /api/v1/estimate 503 in the Compose demo path
E1 Add metadata filters for /search
E2 Add search metrics dashboard
E3 Add measured HNSW vector_cosine_ops index migration
E4 Add Streamlit search UI
E5 Add DevEx cleanup: pager defaults and lighter optional dependencies
```

## Run local gates

```bash
cd /workspaces/ai-engineering/estimador-cag

uv run ruff check --fix app evals tests scripts query_examples.py
uv run ruff check app evals tests scripts query_examples.py
uv run python -m py_compile $(find app tests evals scripts -name '*.py' -type f 2>/dev/null) streamlit_app.py query_examples.py
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q
env -u OPENAI_API_KEY DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q
```

## Run opt-in DB integration tests

```bash
cd /workspaces/ai-engineering

docker compose up -d postgres redis

cd /workspaces/ai-engineering/estimador-cag

DATABASE_URL=postgresql+asyncpg://estimator:estimator@localhost:5432/estimator uv run alembic upgrade head

SESSION08_DB_INTEGRATION=1 DATABASE_URL=postgresql+asyncpg://estimator:estimator@localhost:5432/estimator uv run pytest tests/test_session08_db_ingest_integration.py tests/test_session08_db_search_integration.py -q
```

## Security notes

Do not commit `.env`, real API keys, screenshots with secrets, or copied terminal output containing secrets.

Normal CI uses dummy provider keys for deterministic test execution.
