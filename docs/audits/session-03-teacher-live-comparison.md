# Session 03 Teacher Live Version Comparison

Branch:

gg-sesion-03-canonical-compliance

Purpose:

Compare the stable Session 03 implementation with the teacher live version before adopting code.

## Current stable baseline

Green gates already proven:

- ruff passed
- pytest passed
- py_compile passed
- GET /health works
- GET /metrics works
- POST /api/v1/estimate works
- POST /api/v1/estimate/stream works
- FastAPI / works in browser
- FastAPI /demo works in browser
- Streamlit 8501 works after starting Streamlit and setting port visibility

## Comparison table

| Area | My current version | Teacher live version | Adopt? | Reason |
| --- | --- | --- | --- | --- |
| Redis cache | In memory decorator in `app/services/cache.py`, TTL 300, key uses tier and transcription | `EstimationCache` with Redis, TTL 86400, deterministic JSON SHA key including system prompt, user message, model, max tokens, thinking budget | Yes | Teacher version is closer to canonical. Adapt key to include tier, model, prompt hash or prompt version, and transcription hash. |
| LiteLLM wrapper | Manual OpenAI compatible client through `get_model_config` | `LLMWrapper` using `litellm.Router`, fallback, cost, streaming, cache | Yes later | Good abstraction shape, but must be adapted to DeepSeek and Kimi instead of OpenAI and Anthropic only. |
| structlog | Basic stdlib logging plus custom metrics middleware | structlog used in cache and wrapper | Yes | Adopt structured logs, but preserve `/metrics` and enrich it. |
| SSE | Working `/api/v1/estimate/stream` using `EventSourceResponse` | Has SSE endpoint and tests for token/done events and multiline chunks | Yes | Your endpoint works. Teacher tests are useful canonical coverage. |
| Streamlit | Works, but calls `estimate` and `estimate_stream` directly | Calls FastAPI backend HTTP/SSE | Yes in Phase 5 | Teacher direction is canonical. Change only after backend Redis, metrics, and LiteLLM are stable. |
| Browser demo | Same origin `/` and `/demo`, uses `window.location.origin` | Static file under `app/static/sse_demo.html` | Keep current | Current approach is better for Codespaces and avoids port 8080, CORS, mixed content, and hardcoded URLs. |
| Metrics | `/metrics` exists with basic last call metrics | No stronger `/metrics` visible from zip inspection | Keep and enrich current | Current version is ahead here. |
| Tests | Only `test_health.py` | Tests for cache, endpoint, stream, wrapper, examples, evaluation | Adopt selectively | Use teacher tests as TDD inspiration, adapted to DeepSeek and Kimi. |
| README | Codespaces and port guidance now being improved | Teacher README is useful but less Codespaces specific | Merge useful pieces only | Preserve the human browser path and port visibility instructions. |
| Docker compose | Redis service not yet adopted in current project | Teacher has Redis compose | Adopt | Required for canonical Redis proof. |

## Adoption strategy

Do not overwrite the current project with the teacher version.

Adopt surgically:

1. Redis cache pattern.
2. Redis docker compose service.
3. Cache tests.
4. SSE tests.
5. structlog pattern.
6. LiteLLM wrapper shape, adapted to DeepSeek and Kimi.
7. Streamlit backend API calling pattern.

Preserve:

1. Same origin `/` and `/demo`.
2. Codespaces friendly browser workflow.
3. DeepSeek and Kimi tiering.
4. Kimi temperature guard.
5. Empty response failure rule.
6. Existing `/metrics`, then enrich it.
7. Human README path.

## Next phase

Phase 2: Redis exact cache with TDD.

First write failing tests. Then implement the smallest Redis cache change.
