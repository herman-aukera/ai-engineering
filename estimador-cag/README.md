# LIDR AI Engineering: Estimador CAG

## Session 08: pgvector semantic search

Current working branch:

    gg-session-08-pgvector-search

This branch upgrades the historical-budget embedding pipeline into a persisted semantic search baseline using PostgreSQL plus pgvector. It stores ingested budget documents and their structural chunks, embeds the chunks with OpenAI, and exposes retrieval through a public `POST /search` endpoint.

### What this session adds

    docker-compose.yml
    estimador-cag/alembic.ini
    estimador-cag/alembic/
    estimador-cag/app/persistence/
    estimador-cag/app/embedding_pipeline/ingestion_service.py
    estimador-cag/app/embedding_pipeline/search_service.py
    estimador-cag/app/routers/search.py
    estimador-cag/query_examples.py
    estimador-cag/output_examples.txt

### Run Session 08 with Docker Compose

From the repository root:

    cd /workspaces/ai-engineering
    docker compose up -d postgres redis ai_service
    docker compose exec -T ai_service uv run alembic upgrade head

Health check:

    docker compose exec -T ai_service python -c "import json, urllib.request; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8000/health', timeout=10).read().decode('utf-8')), indent=2))"

Dry-run the required queries without calling the API:

    docker compose run --rm ai_service uv run python query_examples.py --dry-run

Run the real workflow with a configured `OPENAI_API_KEY`:

    docker compose run --rm ai_service uv run python query_examples.py --ingest-example-corpus

The committed `output_examples.txt` was generated from that real Compose workflow. It shows one successful example corpus ingest and five real `/search` calls with chunk ids, cosine distances, chunk metadata, server timings, and client timings.

### API contract

Persist a historical budget document and its chunks:

    POST /embeddings/ingest

Request shape:

    {
      "source_path": "examples/session08/query_examples_budget.json",
      "document_type": "historical_budget",
      "content": {
        "budgets": []
      }
    }

Successful response shape:

    {
      "document_id": 5,
      "chunks_created": 4,
      "embedding_dimension": 1536,
      "ingestion_time_ms": 2879
    }

Duplicate source paths return `409` with the existing `document_id`.

Search persisted chunks:

    POST /search

Request shape:

    {
      "query": "REST API development with JWT authentication for financial sector",
      "k": 5
    }

Successful response shape:

    {
      "query": "REST API development with JWT authentication for financial sector",
      "k": 5,
      "search_time_ms": 199,
      "results": [
        {
          "chunk_id": 9,
          "document_id": 5,
          "chunk_type": "budget_component",
          "content": "...",
          "distance": 0.3081,
          "metadata": {}
        }
      ]
    }

### Why two tables

Session 08 uses a `documents` table and a `chunks` table instead of one flat table.

The `documents` table owns source-level identity, document type, ingest timestamp, and document-level metadata. The `chunks` table owns the searchable units: chunk type, content, embedding vector, chunk metadata, and the foreign key back to the source document.

That split keeps one-to-many document integrity explicit. It avoids duplicating document-level fields on every chunk while still allowing each chunk to carry retrieval-specific metadata.

### Why JSONB metadata

Budget chunks carry flexible metadata such as `budget_id`, `component_id`, `client_sector`, `tech_stack`, `complexity`, token count, year, country, and estimated hours.

JSONB is the right baseline because chunk metadata will evolve as chunking strategies evolve. Adding a new metadata key should not require a new migration every time. The migration still adds a GIN index on chunk metadata so later metadata filters can be introduced without redesigning the schema.

### Why cosine distance

The retrieval endpoint ranks chunks by pgvector cosine distance. Cosine distance is a good baseline for text embeddings because it compares vector direction rather than raw magnitude. That makes it suitable for semantic similarity: queries about authentication should land closer to authentication chunks than unrelated chunks.

The repository deliberately returns distance rather than hiding it. That makes the baseline auditable and helps compare future changes such as thresholds, filters, or alternative embedding models.

### Why no vector index yet

The migration intentionally does not create a vector index. Sequential scan is the correct learning baseline before tuning.

A vector index such as HNSW or IVFFlat should be added only after measuring corpus size, latency, recall quality, write frequency, and the chosen operator class. Adding an index too early can hide baseline behavior and make it harder to explain why retrieval improved or regressed.

The current schema is ready for a later vector index, but Session 08 keeps the first version simple and measurable.

### Known limitation

Out-of-domain queries still return nearest neighbors because `/search` currently has no similarity threshold. The restaurant-reservation query in `output_examples.txt` is intentionally useful as a negative-control example: it proves the system always returns the nearest chunks, even when the corpus is not a good semantic match.

A future slice can add a maximum distance threshold or a confidence label so clearly weak matches are surfaced as low-confidence results.

### Validation commands

Normal validation, no real provider calls:

    cd /workspaces/ai-engineering/estimador-cag
    uv run ruff check --fix app evals tests scripts query_examples.py
    uv run ruff check app evals tests scripts query_examples.py
    uv run python -m py_compile $(find app tests evals scripts -name '*.py' -type f 2>/dev/null) streamlit_app.py query_examples.py
    OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q
    env -u OPENAI_API_KEY DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q

Opt-in DB integration tests:

    cd /workspaces/ai-engineering
    docker compose up -d postgres redis
    cd /workspaces/ai-engineering/estimador-cag
    DATABASE_URL=postgresql+asyncpg://estimator:estimator@localhost:5432/estimator uv run alembic upgrade head
    SESSION08_DB_INTEGRATION=1 DATABASE_URL=postgresql+asyncpg://estimator:estimator@localhost:5432/estimator uv run pytest tests/test_session08_db_ingest_integration.py tests/test_session08_db_search_integration.py -q

### Security notes

Never commit `.env`, real API keys, screenshots containing secrets, or copied terminal output containing secrets. `query_examples.py` reads the API through the running service environment; it does not print secrets.

---

## Session 07: Embedding pipeline pre-exercise

Current working branch:

    gg-session-07-pre-exercise

Official delivery alias branch to create at the end:

    session-07/pre-exercise

This branch adds the minimum embedding and structural chunking pipeline for the Session 07 pre-exercise. The goal is to turn normalized historical budget JSON into structural chunks, generate OpenAI embeddings in memory, expose them through FastAPI, and provide a CLI sanity helper for comparing two texts.

This is intentionally not a RAG implementation yet.

### What embeddings are

An embedding is a numeric vector that represents the meaning of a text. Texts with similar meaning tend to produce vectors that are close to each other. The CLI compares two vectors with cosine similarity, which measures whether they point in a similar direction.

### Why one component equals one chunk

For these historical budgets, a budget component is the smallest useful semantic unit. A component such as “OAuth 2.0 authentication backend” becomes more meaningful when the chunk includes parent context such as project summary, sector, country, year, main technology, and total estimated hours.

Embedding the entire budget JSON as one vector would blur together unrelated components, metadata, estimates, dependencies, and implementation details. That produces a noisy vector that is harder to reuse later for retrieval.

### Scope boundaries

Included:

    app/embedding_pipeline/schemas.py
    app/embedding_pipeline/chunker.py
    app/embedding_pipeline/embedder.py
    app/embedding_pipeline/router.py
    scripts/compare.py
    data/budgets_sample.json

Not included yet:

    vector database
    pgvector persistence
    retrieval endpoint
    semantic search
    recursive chunking
    semantic chunking
    hierarchical chunking
    late chunking
    Contextual Retrieval implementation
    LLM-generated chunk enrichment
    UI changes

Contextual Retrieval is relevant conceptually because parent context helps chunks stand alone, but this task only implements deterministic contextual headers from the existing budget fields. It does not call an LLM to enrich chunks.

### Configure OpenAI

Set the key in your local environment or Codespaces secret. Do not paste the value into README or terminal logs that will be committed.

Example, without showing the value:

    export OPENAI_API_KEY

Do not commit `.env`, real API keys, screenshots with secrets, or copied terminal output containing secrets.

Normal tests do not call OpenAI. They use fake clients and can run with:

    OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q

### Start FastAPI

From the project directory:

    cd /workspaces/ai-engineering/estimador-cag
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Health check:

    curl http://localhost:8000/health

Open Swagger UI:

    http://localhost:8000/docs

The Session 07 endpoint appears as:

    POST /embeddings/ingest

### Invoke POST /embeddings/ingest

Example using the committed sample data:

    cd /workspaces/ai-engineering/estimador-cag
    curl -s -X POST "http://localhost:8000/embeddings/ingest" \
      -H "Content-Type: application/json" \
      --data-binary @<(python - <<'PY'
    import json
    from pathlib import Path

    budgets = json.loads(Path("data/budgets_sample.json").read_text(encoding="utf-8"))
    print(json.dumps({"budgets": budgets}))
    PY
    )

The response contains vectorized chunks and stats:

    chunks: list of embedded structural chunks
    stats.total_budgets
    stats.total_chunks
    stats.total_tokens
    stats.estimated_cost_usd
    stats.model

### Run compare.py locally

    cd /workspaces/ai-engineering/estimador-cag
    uv run python scripts/compare.py \
      --text-a "OAuth 2.0 authentication backend for fintech" \
      --text-b "JWT-based authorization service for banking app"

Expected output shape:

    Text A: OAuth 2.0 authentication backend for fintech
    Text B: JWT-based authorization service for banking app
    Cosine similarity: 0.xxxx

### Run compare.py in Docker if the service name is known

    Docker service name was not documented here because no known service name was detected. Use the local uv command below, or inspect docker-compose.yml before adding a container command.

### Run the three-pair sanity check

After configuring a real `OPENAI_API_KEY`, run these commands and record the three values in `app/embedding_pipeline/SANITY_CHECK.md`:

    uv run python scripts/compare.py --text-a "OAuth 2.0 authentication backend with JWT tokens for fintech mobile app" --text-b "Authorization service using JSON Web Tokens for a banking application"

    uv run python scripts/compare.py --text-a "OAuth 2.0 authentication backend with JWT tokens for fintech mobile app" --text-b "Database migration from MySQL to PostgreSQL with zero downtime"

    uv run python scripts/compare.py --text-a "Backend services" --text-b "API development"

The sanity file is committed in a later slice because it must contain real live embedding results. It is only a smoke sanity check, not a formal retrieval evaluation.

### Run validation gates

    cd /workspaces/ai-engineering/estimador-cag
    uv run ruff check --fix app evals tests scripts
    uv run ruff check app evals tests scripts
    uv run python -m py_compile $(find app tests scripts -name '*.py' -type f 2>/dev/null)
    OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q

---



## Codespaces startup modes

The default Codespaces startup mode is now API only:

    ESTIMADOR_START_MODE=api

That starts Redis and FastAPI, which is enough for Session 07 work:

    /docs
    POST /embeddings/ingest
    scripts/compare.py

Manual startup commands from the repository root:

    bash .devcontainer/start-estimador-services.sh none
    bash .devcontainer/start-estimador-services.sh redis
    bash .devcontainer/start-estimador-services.sh api
    bash .devcontainer/start-estimador-services.sh ui

Modes:

    none   Starts nothing and prints help.
    redis  Starts Redis only.
    api    Starts Redis and FastAPI.
    ui     Starts Redis, FastAPI, and Streamlit.
    all    Alias for ui.

Use `ui` when revisiting older sessions that require the Streamlit human interface. Streamlit is no longer auto previewed on every Codespaces start.


## Current branch: Session 06 CAG stress test baseline

Current branch:

```text
gg-pre-session-06-cag-stress-test
```

This branch adds the Session 06 stress test baseline for the existing CAG system.

Required deliverables:

```text
evals/stress/REPORT.md
evals/stress/results.csv
```

The committed stress output contains 900 deterministic rows:

```text
3 scenarios × 5 attachment sizes × 3 repeats × 20 turns = 900 rows
```

A bounded live provider smoke was also validated locally with DeepSeek:

```text
3 scenarios × 5 attachment sizes × 3 repeats × 2 turns = 90 rows
```

The goal of this session is measurement, not RAG implementation. The stress runner measures latency, token use, cost, cache behavior, attachment impact, and memory drift so the CAG baseline can be compared against RAG in the next step.

Session 06 additions:

```text
evals/stress/scenarios.py
evals/stress/metrics.py
evals/stress/run.py
evals/stress/fixtures/build_pdfs.py
evals/stress/results.csv
evals/stress/REPORT.md
```

Validation:

```text
GitHub Actions CI green
232 local pytest tests passed
ruff clean
py_compile clean
```

Historical notes for Sessions 04 and 05 remain below. Some branch names and runtime proof sections in the historical notes refer to the older branch where that work was originally introduced.

---

## Historical architecture notes from Sessions 04 and 05

Architecture: FastAPI, Streamlit, typed product estimation, structured JSON output, Redis exact cache, semantic cache shadow mode, LiteLLM provider routing, DeepSeek and Kimi fallback, input/output guardrails.

## Session 04 Live Plus

This branch turns the estimator into a production-shaped product estimation workflow.

The user-facing path is no longer a free chat. Streamlit sends a typed product request to FastAPI. The backend renders versioned prompts, calls the LLM through LiteLLM, validates structured JSON with Pydantic, normalizes deterministic totals, applies guardrails, stores only valid results in Redis exact cache, records semantic cache shadow metadata, and returns fields that the UI can render directly.

## What this branch includes

Core product interface:

* Streamlit typed product form with project description, project type, detail level, output format, prompt version, and optional reference projects.
* FastAPI typed `EstimationRequest`.
* Versioned Jinja2 prompt templates.
* Separate system and user messages sent to the provider.
* Structured `EstimationResult` returned as primary data.
* Compatibility markdown text returned for older consumers.

Structured output and validation:

* Structured JSON output for typed product estimates.
* JSON only structured system prompt.
* Pydantic validation for request and response contracts.
* Deterministic aggregate normalization:
  * `total_cost_eur` is computed from phase costs.
  * `total_duration_weeks` is computed from phase durations.
* Output guardrails block invalid structured estimates before cache storage.

Provider fallback ladder:

* DeepSeek flash → DeepSeek pro → Kimi 2.5 backup → Kimi 2.6 backup_pro
* Kimi remains configured as fallback because DeepSeek can fail under provider load.
* All structured provider output is locally parsed and validated.
* Kimi is treated as useful but less reliable for structured JSON.

Cache and observability:

* Exact Redis cache runs before semantic cache.
* Exact cache is deterministic and can serve responses.
* Semantic cache shadow mode observes candidate matches only.
* Semantic cache does not serve responses in this branch.
* Exact cache hits skip semantic lookup.
* Invalid output is never stored in exact cache or semantic shadow cache.
* API responses expose:
  * `requested_tier`
  * `served_tier`
  * `fallback_used`
  * `semantic_cache_mode`
  * `semantic_candidate_found`

Guardrails:

* Input guardrails block prompt injection and sensitive data before typed service execution.
* Output guardrails block unsafe or invalid structured results before cache storage.

## Project layout

    estimador-cag/
      app/
        main.py
        config.py
        routers/
          estimations.py
        schemas/
          estimation.py
        guardrails/
          input.py
          output.py
        services/
          llm_service.py
          litellm_provider.py
          cache.py
          semantic_cache.py
          costs.py
          conversation.py
        prompts/
          loader.py
          estimation/
            v1/
              system.j2
              user.j2
              examples.j2
            v2/
              system.j2
              user.j2
              examples.j2
      streamlit_app.py
      tests/
      docker-compose.yml
      pyproject.toml

## API endpoints

    GET  /health
    GET  /metrics
    POST /api/v1/estimate
    POST /api/v1/estimate/stream

Main typed product endpoint:

    POST /api/v1/estimate?prompt_version=v2

The legacy transcription request and streaming endpoint are still present to preserve the stable Session 03 backend while the product interface evolves.

## Typed request contract

The Session 04 typed request uses:

    description: string, 20 to 2000 characters
    project_type: web_saas, internal_tool, automation, data_ai, mobile_app
    detail_level: summary, medium, detailed
    output_format: narrative, phases_table
    reference_projects: optional list

Example payload:

    {
      "description": "Build a B2B onboarding SaaS with account approval, role based admin review, email notifications, audit logs, and an operations reporting dashboard for managers.",
      "project_type": "web_saas",
      "detail_level": "medium",
      "output_format": "phases_table"
    }

Expected response includes:

    {
      "prompt_version": "v2",
      "result": {
        "summary": "...",
        "total_duration_weeks": 20,
        "total_cost_eur": 200000,
        "confidence_pct": 80,
        "phases": []
      },
      "text": "## Product estimate...",
      "cached": true,
      "cache_backend": "redis",
      "model": "deepseek-v4-flash",
      "provider": "deepseek",
      "tier": "flash",
      "requested_tier": "flash",
      "served_tier": "flash",
      "fallback_used": false,
      "semantic_cache_mode": "shadow",
      "semantic_candidate_found": false
    }

## Prompt templates

Prompt files:

    app/prompts/loader.py
    app/prompts/estimation/v1/system.j2
    app/prompts/estimation/v1/user.j2
    app/prompts/estimation/v1/examples.j2
    app/prompts/estimation/v2/system.j2
    app/prompts/estimation/v2/user.j2
    app/prompts/estimation/v2/examples.j2

The loader function is:

    render_estimation_prompt(request, version="v1") -> tuple[str, str]

Jinja2 is configured with:

    StrictUndefined
    trim_blocks=True
    lstrip_blocks=True

## Start Redis

Redis is used by the exact response cache.

    cd /workspaces/ai-engineering
    docker compose up -d redis
    docker compose ps redis
    docker compose exec -T redis redis-cli ping
    cd estimador-cag

Expected:

    PONG

## Start FastAPI

    cd /workspaces/ai-engineering/estimador-cag
    uv sync --extra dev
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Health check:

    curl http://localhost:8000/health

Metrics check:

    curl http://localhost:8000/metrics

## Typed estimate curl

    cd /workspaces/ai-engineering/estimador-cag

    cat > /tmp/estimate_payload.json <<'JSON'
    {
      "description": "Build a B2B onboarding SaaS with account approval, role based admin review, email notifications, audit logs, and an operations reporting dashboard for managers.",
      "project_type": "web_saas",
      "detail_level": "medium",
      "output_format": "phases_table"
    }
    JSON

    curl -sS -X POST 'http://localhost:8000/api/v1/estimate?prompt_version=v2' \
      -H 'Content-Type: application/json' \
      --data-binary @/tmp/estimate_payload.json

Check for:

    result.summary
    result.phases
    cached
    cache_backend
    provider
    tier
    requested_tier
    served_tier
    fallback_used
    semantic_cache_mode
    semantic_candidate_found

## Start Streamlit

In another terminal:

    cd /workspaces/ai-engineering/estimador-cag
    uv run streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0

When running in Codespaces, open the forwarded Streamlit port 8501.

If the frontend needs a non default backend URL:

    export ESTIMADOR_BACKEND_URL="https://your-forwarded-fastapi-url"
    uv run streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0

## Codespaces port visibility

After Codespaces starts, open the PORTS tab.

Check:

* 8000 FastAPI backend
* 8501 Streamlit UI

If either port is Private and browser access returns 401, 402, tunnel auth, or 502:

1. Right click the port.
2. Select Port Visibility.
3. Choose Public.
4. Reload the browser page.

Terminal option:

    gh codespace ports visibility 8000:public 8501:public -c "$CODESPACE_NAME"

## Streamlit human test path

1. Start Redis.
2. Start FastAPI on port 8000.
3. Start Streamlit on port 8501.
4. Open Streamlit.
5. Fill the product form.
6. Select prompt version `v2` for the final demo.
7. Submit.
8. Confirm summary, metrics, phase table, assumptions, risks, and recommendations render.
9. Confirm prompt version and cache info render.
10. Confirm request payload is visible in the expander.

## Focused Session 04 tests

    uv run pytest \
      tests/test_session04_estimation_schema.py \
      tests/test_prompt_estimation_v1.py \
      tests/test_session04_backend_product_endpoint.py \
      tests/test_session04_provider_messages.py \
      tests/test_session04_llm_service_product.py \
      tests/test_session04_structured_provider.py \
      tests/test_session04_structured_schema.py \
      tests/test_session04_structured_endpoint.py \
      tests/test_session04_input_guardrails.py \
      tests/test_session04_output_guardrails.py \
      tests/test_session04_semantic_cache.py \
      tests/test_session04_semantic_cache_integration.py \
      tests/test_session04_streamlit_product_form.py \
      tests/test_session04_streamlit_structured_rendering.py \
      tests/test_streamlit_backend_client.py \
      -v

## Full regression gate

    uv run ruff check app/ tests/ streamlit_app.py --fix
    uv run ruff check app/ tests/ streamlit_app.py
    uv run pytest tests/ -v
    uv run python -m py_compile \
      app/main.py \
      app/config.py \
      app/services/llm_service.py \
      app/services/cache.py \
      app/services/semantic_cache.py \
      app/services/costs.py \
      app/services/conversation.py \
      app/services/litellm_provider.py \
      app/middleware/logging.py \
      app/routers/estimations.py \
      app/schemas/estimation.py \
      app/prompts/loader.py \
      streamlit_app.py

## Runtime proof from live plus branch

Final runtime smoke confirmed:

* FastAPI `/health` returns ok.
* Typed estimate endpoint returns structured JSON.
* Redis exact cache metadata appears in API response.
* Fallback metadata appears in API response.
* Semantic cache shadow metadata appears in API response.
* Streamlit renders product form, summary, metrics, phases, assumptions, risks, recommendations, compatibility text, prompt version, cache info, and request payload.

## Known limitations

* Semantic cache is shadow only and does not serve responses.
* Semantic cache uses deterministic local embeddings for plumbing, not production embeddings.
* Semantic cache is process local in this branch, not Redis Stack or vector database backed.
* Kimi fallback remains configured but is less reliable for strict structured JSON than DeepSeek.
* The legacy transcription and streaming endpoints remain for compatibility.

## Session 05 conversational memory and attachments

Session 05 upgrades the estimator from a one request one estimate workflow into a session aware product interface.

### Backend endpoints

The backend now exposes:

POST /sessions

POST /sessions/{session_id}/estimate

POST /sessions creates a volatile in process conversation and returns a UUID v4 session_id.

POST /sessions/{session_id}/estimate accepts multipart/form-data with:

transcript: latest client conversation turn
attachments: optional repeated PDF or DOCX files
project_type: typed project category
detail_level: typed detail level
output_format: typed output format
prompt_version: v1 or v2
tier: starting model tier

### Memory model

The implementation separates raw history from durable project facts:

ConversationHistory
ProjectMetadata
SessionStore

ConversationHistory keeps a sliding window of recent user and assistant turns. The default is six retained turns. This is intentionally process local for the pre session exercise. It disappears on restart, deploy, or multi worker reshuffle.

project_metadata is stored separately from raw messages and injected into the system prompt on each turn. It currently captures facts such as:

project_name
assumed_team_size
mentioned_technologies
agreed_scope
open_questions
attachments_seen

The extractor uses deterministic heuristics because this phase prioritizes speed, cost control, and testability over a second LLM extraction call.

### Attachment path chosen

This project uses local text extraction instead of provider specific multimodal file APIs.

Chosen path:

PDF extraction: pypdf
DOCX extraction: python-docx

Why this path:

Provider independent
Works with the existing LiteLLM structured path
Easy to test without external APIs
Prepares the project for later chunking or RAG work

Extracted attachment text is added to the prompt with clear delimiters:

--- attachment: filename.pdf ---
...
--- end attachment: filename.pdf ---

### Streamlit usage

Start the backend and Streamlit app:

uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

uv run streamlit run streamlit_app.py --server.port 8501

When running outside localhost, set:

export ESTIMADOR_BACKEND_URL="https://your-forwarded-backend-url"

The Streamlit UI now creates a backend session automatically, stores the session_id in st.session_state, and sends estimates through the session endpoint.

Use New conversation to reset the session.

The sidebar shows Project metadata so the memory state can be inspected during demos and class review.

The form supports:

Transcript text area
PDF uploads
DOCX uploads
typed project controls
prompt version selector
model tier selector
structured estimate rendering
