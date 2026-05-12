# Session 03 Phase 6 handoff

## Branch

gg-sesion-03-canonical-compliance

## Latest commit

2e7273f feat: add conversation history manager

## Completed

- Phase 5 extras completed:
  - Kimi K2.6 live verification
  - LiteLLM Moonshot routing fixed
  - LLM cost tracking
  - Rich streaming metrics
  - Streamlit routed through FastAPI backend
  - Redis cache for sync and streaming calls

- Phase 6 completed:
  - Added conversation manager service
  - Added bounded sliding history window
  - Preserved canonical system prompt as first message
  - Rejected non user or assistant history roles
  - Added explicit summary stub for future compression
  - LiteLLMProvider complete and stream accept history
  - llm_service estimate and estimate_stream pass history
  - API schema accepts history and max_history_turns
  - Router passes history to sync and streaming paths
  - Streamlit builds backend history from previous visible chat messages
  - Streamlit excludes the current prompt from history before sending

## Real smoke proof

History payload was accepted by:

- POST /api/v1/estimate
- POST /api/v1/estimate/stream

The response estimated the second scope using previous context.

Streaming cache remained functional:

- first sync generated Redis cache
- streaming request reused Redis cache
- metrics preserved cost and rich streaming metadata

Observed metrics included:

- cost_usd
- cost_source
- pricing_model
- stream_output_chars
- stream_chunks
- stream_cached
- stream_started_at
- stream_finished_at

## Validation gates passed

Focused Phase 6 gate passed:

- ruff
- py_compile
- pytest focused conversation and Streamlit tests

Earlier full Phase 5 gates passed:

- ruff
- pytest full suite
- py_compile
- real FastAPI smoke
- secret scan

## Important implementation notes

- Streamlit is presentation only. It calls FastAPI backend endpoints.
- Backend remains the source of truth for Redis cache, LiteLLM routing, fallback, metrics, and structured logging.
- Streaming SSE metrics require consuming the whole stream. Do not pipe SSE to head when proving final metrics.
- Redis port 6379 should stay private in Codespaces.
- FastAPI should run on port 8000.
- Streamlit should run on port 8501.

## Next recommended phase

Start the next canonical phase from a clean branch or continue this branch depending on teacher requirements.

Suggested next work:

1. Add stronger conversation summary compression.
2. Add persistent conversation IDs if required.
3. Add UI controls for history window size.
4. Add README documentation for Phase 5 and Phase 6 features.
5. Run final audit against teacher rubric before merging.

## Startup commands for next Codespace

```bash
cd /workspaces/ai-engineering

git switch gg-sesion-03-canonical-compliance
git pull
git status --short

cd estimador-cag

docker compose up -d redis

uv run ruff check app/ tests/ streamlit_app.py
uv run pytest tests/ -v

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload


In a second terminal:

cd /workspaces/ai-engineering/estimador-cag

uv run streamlit run streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port 8501