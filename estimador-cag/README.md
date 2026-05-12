# LIDR AI Engineering: Estimador CAG

Architecture: FastAPI, Streamlit, CAG, Redis exact cache, LiteLLM provider routing.

Current branch:

    gg-pre-session-04-product-interface

This branch prepares the mandatory pre Session 04 exercise. The estimator is no longer a free chat in the frontend. It is now a typed product estimation interface.

## What this branch changes

Mandatory Session 04 scope:

* Streamlit uses a typed product form with `st.form`.
* The backend accepts a typed `EstimationRequest`.
* Prompts live in versioned Jinja2 templates.
* The prompt loader renders separate system and user prompts.
* The provider receives separate `system` and `user` messages.
* The typed response returns `text` and `prompt_version`.
* Template tests are included.
* README run and test instructions are updated.

Intentionally not included because the exercise reserves them for live session:

* Structured JSON output from the LLM.
* Guardrails.
* Semantic cache.

Allowed optional extras included after the mandatory branch was green:

* Prompt version `v2`.
* Query parameter `?prompt_version=v2`.
* Optional `reference_projects`.
* Prompt render hash logging.
* Cleaner typed validation errors.
* Stable Session 03 backend infrastructure preserved where harmless.

## Project layout

    estimador-cag/
      app/
        main.py
        config.py
        routers/
          estimations.py
        schemas/
          estimation.py
        services/
          llm_service.py
          litellm_provider.py
          cache.py
          costs.py
          conversation.py
        prompts/
          loader.py
          estimation/
            v1/
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

For Session 04, the main mandatory endpoint is:

    POST /api/v1/estimate

It accepts the new typed product request and returns:

    {
      "text": "...",
      "prompt_version": "v1"
    }

The legacy transcription request and backend streaming endpoint are still present to preserve the working Session 03 backend while the product interface evolves.

## Typed request contract

The Session 04 typed request uses:

    description: string, 20 to 2000 characters
    project_type: mobile_app, web_saas, internal_tool, data_pipeline
    detail_level: summary, medium, detailed
    output_format: phases_table, line_items, narrative

Example payload:

    {
      "description": "Build a B2B onboarding SaaS with account approval, role-based admin review, email notifications, and an operations reporting dashboard.",
      "project_type": "web_saas",
      "detail_level": "medium",
      "output_format": "phases_table"
    }

## Prompt templates

Prompt files:

    app/prompts/loader.py
    app/prompts/estimation/v1/system.j2
    app/prompts/estimation/v1/user.j2
    app/prompts/estimation/v1/examples.j2

The loader function is:

    render_estimation_prompt(request, version="v1") -> tuple[str, str]

Jinja2 is configured with:

    StrictUndefined
    trim_blocks=True
    lstrip_blocks=True

## Start Redis

Redis is still used by the existing exact cache infrastructure.

    cd /workspaces/ai-engineering
    docker compose up -d redis
    docker compose ps redis
    cd estimador-cag

## Start FastAPI

    uv sync
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Health check:

    curl http://localhost:8000/health

Metrics check:

    curl http://localhost:8000/metrics

## Start Streamlit

In another terminal:

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

## Typed estimate curl

    curl -X POST http://localhost:8000/api/v1/estimate \
      -H "Content-Type: application/json" \
      -d '{
        "description": "Build a B2B onboarding SaaS with account approval, role-based admin review, email notifications, and an operations reporting dashboard.",
        "project_type": "web_saas",
        "detail_level": "medium",
        "output_format": "phases_table"
      }'

Expected response shape:

    {
      "text": "## ...",
      "prompt_version": "v1"
    }

## Streamlit human test path

1. Start Redis.
2. Start FastAPI on port 8000.
3. Start Streamlit on port 8501.
4. Open Streamlit.
5. Fill the product form.
6. Submit.
7. Confirm the estimate text appears.
8. Confirm the prompt version is displayed as `v1`.

## Focused Session 04 tests

    uv run pytest \
      tests/test_session04_estimation_schema.py \
      tests/test_prompt_estimation_v1.py \
      tests/test_session04_backend_product_endpoint.py \
      tests/test_session04_provider_messages.py \
      tests/test_session04_llm_service_product.py \
      tests/test_session04_streamlit_product_form.py \
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
      app/services/provider.py \
      app/services/cache.py \
      app/services/costs.py \
      app/services/conversation.py \
      app/services/litellm_provider.py \
      app/middleware/logging.py \
      app/routers/estimations.py \
      app/schemas/estimation.py \
      app/prompts/loader.py \
      streamlit_app.py

## Live session notes

The Session 04 mandatory product path is complete when:

* The typed schemas exist.
* The prompt templates render and are tested.
* The backend endpoint accepts typed requests.
* The provider receives separate system and user messages.
* Streamlit uses a typed product form.
* The response includes `text` and `prompt_version`.
* README and tests are green.

After the live session, cleanup can happen in a separate branch:

* Remove or deprecate legacy transcription endpoints if the teacher confirms they are no longer useful.
* Remove unused conversation UI assumptions if they stop serving backend compatibility tests.
* Add structured JSON output.
* Add guardrails.
* Add semantic cache.
