# Energy Aware Chat Demo Ready Checklist

status: demo-ready-checklist
branch: EACHAT
scope: local final-project MVP demo
claim_boundary: production-oriented MVP candidate, not production-ready

## Purpose

This checklist turns the Energy Aware Chat branch into a repeatable reviewer demo. It is meant for the final-project evaluator, a teaching assistant, or a future portfolio reviewer.

## What this demo proves

1. FastAPI starts locally.
2. Opening port 8000 lands on the Energy Aware Chat browser demo.
3. The browser demo can run live provider mode.
4. The browser demo can run deterministic RAG-only mode.
5. The browser demo can inspect fixed benchmark evidence.
6. Streamlit provides a richer human UI with mode and execution selectors.
7. The Energy Card shows decision, energy, repairs, evidence, and caveats.
8. The execution audit shows provider calls, deterministic critics, decider, and repair behavior.
9. The fixed benchmark stays measurement-only.
10. CI proves the deterministic gates.

## What this demo does not prove

1. Public production deployment.
2. Real-user production readiness.
3. Validated quality improvement over plain DeepSeek.
4. Vector database RAG for Energy Aware Chat.
5. A full live-provider benchmark dataset.

## Required local services

1. Redis for old estimator/SSE flows when needed.
2. FastAPI on port 8000.
3. Optional Streamlit on port 8501.
4. DeepSeek and Kimi keys only for live provider smoke or live chat mode.

## Commands

Run from the repository root:

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch EACHAT
git pull --ff-only

git rev-parse --short HEAD
git status --short
```

Run FastAPI:

```bash
cd /workspaces/ai-engineering/estimador-cag

UV_HTTP_TIMEOUT=600 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open the forwarded port 8000 URL. The root URL redirects to:

```text
/energy-chat/demo
```

Run Streamlit in another terminal:

```bash
cd /workspaces/ai-engineering/estimador-cag

ESTIMADOR_BACKEND_URL=https://<your-codespace-8000-url> \
UV_HTTP_TIMEOUT=600 \
uv run streamlit run energy_chat_streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

Open the forwarded port 8501 URL.

## Demo path

### Browser demo

1. Open port 8000.
2. Confirm the Energy Aware Chat demo appears by default.
3. Select `project` mode.
4. Select live provider mode.
5. Ask a final-project or release-readiness question.
6. Inspect the Energy Card.
7. Inspect the visible execution audit.
8. Run RAG only.
9. Run fixed benchmark evidence.
10. Point out the measurement-only claim boundary.

### Streamlit demo

1. Open port 8501.
2. Confirm the backend URL points to the forwarded FastAPI URL.
3. Select mode and execution mode.
4. Run Energy Aware Chat.
5. Inspect Energy Card, execution audit, RAG evidence, and provider metadata.
6. Show fixed benchmark evidence.

## Validation gate

Run after any demo-readiness change:

```bash
cd /workspaces/ai-engineering/estimador-cag

UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh

cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

## Accepted wording

```text
Energy Aware Chat is a browser-testable and Streamlit-testable production-oriented MVP candidate with deterministic RAG baseline, live provider path, Energy Card, visible execution audit, fixed deterministic benchmark evidence, local validation proof, and dedicated CI proof.
```

## Forbidden wording

```text
production-ready
real-user ready
validated quality improvement over plain DeepSeek
frontier-model superiority
public deployed service
```
