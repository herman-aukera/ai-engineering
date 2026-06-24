# AI Engineering Coursework

This repository contains the LIDR AI Engineering coursework.

## Current submission

Active project:

```text
estimador-cag/
```

Current branch:

```text
gg-session-10/pre-work
```

Current deliverable:

```text
Session 10 — advanced retrieval compass and A/B/C/D retrieval evaluation
```

## What this branch delivers

This branch upgrades the existing pgvector retrieval baseline with advanced retrieval experiments:

1. PostgreSQL full text search support for lexical retrieval.
2. Hybrid vector plus lexical retrieval using Reciprocal Rank Fusion.
3. Optional service level reranking.
4. A deterministic keyword overlap reranker for CI safe measurement.
5. A golden retrieval set.
6. An A/B/C/D measurement runner.
7. Hardened retrieval metrics that distinguish repeated chunk relevance from unique budget relevance.

The current evidence is intentionally bounded. It proves that the retrieval paths are wired, testable, and measurable on the small course corpus. It does not claim benchmark superiority.

## A/B/C/D retrieval variants

| Config | Meaning |
| --- | --- |
| A | Vector retrieval baseline |
| B | Hybrid retrieval with vector plus lexical search fused by RRF |
| C | Vector retrieval with wider recall followed by deterministic reranking |
| D | Hybrid retrieval with wider RRF pool followed by deterministic reranking |

## Latest deterministic retrieval result

The latest committed Session 10 retrieval report is:

```text
estimador-cag/evals/session10_retrieval/REPORT.md
```

Summary on the 12 case golden set:

| Config | result budget precision@5 | unique budget precision@5 | budget hit@5 | component hit@5 | top1 budget | top1 component |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 0.4000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| B | 0.4000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| C | 0.4000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| D | 0.4000 | 0.2000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Interpretation:

The current corpus is very small and clean, so all variants solve the golden cases. This is wiring and smoke evidence, not proof that hybrid search or reranking improves quality in production.

## Main files

```text
estimador-cag/app/embedding_pipeline/fusion.py
estimador-cag/app/embedding_pipeline/reranker.py
estimador-cag/app/embedding_pipeline/search_service.py
estimador-cag/app/persistence/repository.py
estimador-cag/app/routers/search.py
estimador-cag/alembic/versions/0003_session10_full_text_search.py
estimador-cag/evals/session10_retrieval/golden_retrieval.json
estimador-cag/evals/session10_retrieval/evaluator.py
estimador-cag/evals/session10_retrieval/run.py
estimador-cag/evals/session10_retrieval/results.json
estimador-cag/evals/session10_retrieval/REPORT.md
```

## Run deterministic Session 10 retrieval measurement

```bash
cd /workspaces/ai-engineering/estimador-cag

uv run python -m evals.session10_retrieval.run \
  --output evals/session10_retrieval/results.json \
  --report evals/session10_retrieval/REPORT.md \
  --k 5 \
  --recall-k 8
```

This runner is local and deterministic. It does not call FastAPI, PostgreSQL, OpenAI, DeepSeek, Kimi, or a live reranker model.

## Run local gates

```bash
cd /workspaces/ai-engineering/estimador-cag

uv run ruff check --fix app evals tests scripts query_examples.py streamlit_app.py
uv run ruff check app evals tests scripts query_examples.py streamlit_app.py
uv run python -m py_compile $(find app tests evals scripts -name '*.py' -type f 2>/dev/null) streamlit_app.py query_examples.py
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q
```

## Optional DB integration smoke

The persisted retrieval stack still uses PostgreSQL plus pgvector for the API path.

```bash
cd /workspaces/ai-engineering

docker compose up -d postgres redis

cd /workspaces/ai-engineering/estimador-cag
DATABASE_URL=postgresql+asyncpg://estimator:estimator@localhost:5432/estimator uv run alembic upgrade head
SESSION08_DB_INTEGRATION=1 DATABASE_URL=postgresql+asyncpg://estimator:estimator@localhost:5432/estimator uv run pytest tests/test_session08_db_search_integration.py -q
```

## Real provider policy

Normal tests and committed reports must stay deterministic.

If a real provider smoke is needed, prefer DeepSeek first. Use Kimi only as fallback or comparison. Keep real provider checks separate from deterministic CI gates.

## Historical coursework notes

Historical Session 06, 07, and 08 material is preserved in:

```text
estimador-cag/docs/HISTORICAL_SESSIONS.md
estimador-cag/evals/stress/
estimador-cag/evals/session08_search_quality/
estimador-cag/query_examples.py
estimador-cag/output_examples.txt
```

## Security notes

Do not commit `.env`, real API keys, screenshots with secrets, copied terminal output containing secrets, or generated cache files.

Normal CI uses dummy provider keys for deterministic test execution.
