# LIDR AI Engineering: Estimador CAG

Architecture: FastAPI, Streamlit, typed product estimation, structured JSON output, Redis exact cache, semantic cache shadow mode, LiteLLM provider routing, DeepSeek and Kimi fallback, input/output guardrails.

Current branch:

    gg-session-04-live-plus

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
