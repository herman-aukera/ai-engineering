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
