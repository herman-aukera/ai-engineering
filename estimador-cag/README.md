# LIDR AI Engineering: Estimador CAG

## Energy Aware Chat reviewer entry point

Status: browser-testable, production-oriented MVP candidate on the `EACHAT` incubator branch.

Claim boundary:

```text
measurement_only_no_quality_claim
```

Energy Aware Chat is a constraint-governed assistant for AI project and release-readiness questions. It retrieves project evidence, asks a provider for a draft in live mode, evaluates the candidate with deterministic critics, computes energy, applies one deterministic repair when appropriate, and returns a visible Energy Card.

Start here for review:

```text
docs/energy_aware_chat_reviewer_index.md
```

Fast reviewer documents:

1. `docs/energy_aware_chat_examiner_quickstart.md`
2. `docs/energy_aware_chat_evaluator_landing_page.md`
3. `docs/energy_aware_chat_final_project_acceptance_matrix.md`
4. `docs/energy_aware_chat_final_project_proof_packet.md`
5. `docs/energy_aware_chat_fixed_benchmark_report.md`

Human demo paths:

```text
/energy-chat/demo
energy_chat_streamlit_app.py
```

Primary API paths:

```text
GET  /health
GET  /metrics
GET  /energy-chat/demo
POST /energy-chat/rag/search
POST /energy-chat/chat
POST /energy-chat/chat/live
GET  /energy-chat/benchmark/fixed
GET  /energy-chat/benchmark/fixed/report
POST /energy-chat/benchmark/deepseek-energy-aware
```

Run the local Energy Chat validation gate:

```bash
cd /workspaces/ai-engineering/estimador-cag
UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh
```

Check exact branch CI proof from the repository root:

```bash
cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

Allowed short description:

```text
Energy Aware Chat is a browser-testable, production-oriented MVP candidate on the EACHAT incubator branch.
```

Do not claim:

1. production readiness
2. public deployment is live
3. quality improvement over plain DeepSeek
4. frontier-model superiority
5. vector database RAG grounding for Energy Aware Chat

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
