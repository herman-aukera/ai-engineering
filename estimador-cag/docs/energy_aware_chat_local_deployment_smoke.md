# Energy Aware Chat Local Deployment Smoke Guide

status: local-deployment-smoke-guide
branch: EACHAT
scope: Docker and local runtime proof
claim_boundary: local deployment smoke, not public production deployment

## Purpose

This guide proves that the deployment skeleton is not decorative. It gives a bounded local smoke path for FastAPI, Docker compose, browser demo, and deterministic chat route.

## What this proves

1. The app can start through the local development runtime.
2. The app can expose a health endpoint.
3. The Energy Aware Chat browser demo loads from FastAPI.
4. The deterministic chat route works without live provider keys.
5. Docker compose can be used as a local deployment rehearsal when the environment supports Docker.

## What this does not prove

1. Public URL deployment.
2. Production readiness.
3. Live-provider benchmark quality.
4. User authentication or privacy hardening.
5. Monitoring, rollback, or incident response.

## FastAPI local smoke

Terminal 1:

```bash
cd /workspaces/ai-engineering/estimador-cag

UV_HTTP_TIMEOUT=600 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Terminal 2:

```bash
cd /workspaces/ai-engineering/estimador-cag

curl -s http://127.0.0.1:8000/health | python -m json.tool

curl -s -L http://127.0.0.1:8000/ | head -40

curl -s http://127.0.0.1:8000/energy-chat/benchmark/fixed | python -m json.tool
```

Expected:

1. `/health` returns status ok.
2. `/` redirects to `/energy-chat/demo`.
3. fixed benchmark JSON includes `measurement_only_no_quality_claim`.

## Deterministic chat smoke

```bash
cd /workspaces/ai-engineering/estimador-cag

curl -s -X POST http://127.0.0.1:8000/energy-chat/chat \
  -H "Content-Type: application/json" \
  --data @demo_payloads/energy_chat/chat_project_mvp.json \
  | python -m json.tool
```

Expected:

1. JSON response has `energy_card`.
2. JSON response has `rag`.
3. JSON response has `metadata.claim_boundary`.
4. No live provider key is needed.

## Docker compose smoke

Use this only when Docker is available in the current Codespace.

```bash
cd /workspaces/ai-engineering/estimador-cag

docker compose -f docker-compose.energy-chat.yml up --build
```

In a second terminal:

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
curl -s -L http://127.0.0.1:8000/ | head -40
curl -s http://127.0.0.1:8000/energy-chat/benchmark/fixed | python -m json.tool
```

## Acceptance rule

Accept the local deployment smoke only if:

1. health is green
2. browser demo loads
3. deterministic chat works
4. fixed benchmark evidence works
5. no production claim is made

## Next production step

For final delivery, either:

1. deploy to a public URL, or
2. record a 2 to 3 minute demo video following `energy_aware_chat_mvp_recording_script_final.md`.
