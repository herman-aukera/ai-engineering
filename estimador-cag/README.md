# LIDR Session 02: Estimador CAG

**Architecture:** FastAPI + CAG (Context-Augmented Generation) + Tier Routing

## Layer Diagram

```
Frontend          | (Task 3: streamlit_app.py)
HTTP Transport    | routers/
Data Contracts    | schemas/
Business Logic    | services/
Static Context    | context/
Configuration     | config.py
```

## Tier Ladder

| Priority | Tier | Provider | Model | Use Case |
|---|---|---|---|---|
| 1 | flash | DeepSeek | V4-Flash | Default, cheapest |
| 2 | pro | DeepSeek | V4-Pro | Escalation |
| 3 | backup | Kimi | K2.5 | Fallback |
| 4 | backup_pro | Kimi | K2.6 | Heavy fallback |

## Quick Start

```bash
# Database (for future RAG modules)
docker compose up -d

# Backend
cd estimador-cag
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing

```bash
uv run pytest tests/ -v
uv run ruff check app/ tests/
```

## API Endpoints

- `GET /health` -> Health check
- `POST /api/v1/estimate` -> CAG estimation from transcription

## Session Roadmap

- **Session 2 (NOW):** Static CAG, FastAPI, Pydantic, schemas/
- **Session 3:** Streamlit wrapper, streaming, provider abstraction
- **Modules 3-4:** RAG with embeddings, retrieval, ingestion
- **Module 5:** Agents with orchestrator, tools, validators

## Human test path in Codespaces

This project can be tested by a developer with curl and by a non technical user through Streamlit or the browser SSE demo.

### Option A: Streamlit interface

Start the FastAPI backend:

```bash
cd /workspaces/ai-engineering/estimador-cag
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
## Codespaces port visibility

After Codespaces starts, open the PORTS tab.

Check:

- 8000 FastAPI backend and `/demo`
- 8501 Streamlit UI

If either port is Private and browser access returns 401, 402, tunnel auth, or 502:

1. Right click the port.
2. Select Port Visibility.
3. Choose Public.
4. Reload the browser page.

You can also set visibility from the terminal:

```bash
gh codespace ports visibility 8000:public 8501:public -c "$CODESPACE_NAME"

## Redis exact cache proof

This project uses Redis as an exact response cache for synchronous estimations.

Redis is a response cache. It is not retrieval, not RAG, not semantic search, and not the source of project knowledge. The CAG knowledge still comes from static examples injected into the prompt.

Start Redis:

```bash
docker compose up -d redis
docker compose ps redis
