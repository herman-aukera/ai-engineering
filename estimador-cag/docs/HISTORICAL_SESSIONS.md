# Historical Sessions

This document preserves older coursework context without letting it masquerade as the current branch state.

## Session 06 CAG stress baseline

Artifacts:

```text
evals/stress/scenarios.py
evals/stress/metrics.py
evals/stress/run.py
evals/stress/results.csv
evals/stress/REPORT.md
```

The committed stress report is deterministic coursework evidence. A bounded live provider smoke was validated with DeepSeek, but normal tests do not depend on live provider calls.

## Session 07 embedding and chunking work

Artifacts:

```text
app/embedding_pipeline/chunker.py
app/embedding_pipeline/embedder.py
app/embedding_pipeline/comparison.py
scripts/compare.py
scripts/compare_chunkers.py
docs/session07_live_plus_plan.md
docs/session07_live_plus_readiness.md
docs/session07_chunking_comparison_report.md
```

Session 07 introduced the embedding and chunking foundation. Some scripts still mention Session 07 because they are historical learning tools.

## Session 08 pgvector semantic search baseline

Artifacts:

```text
alembic/versions/0001_session08_pgvector_documents_chunks.py
alembic/versions/0002_session08_hnsw_vector_index.py
app/persistence/
app/embedding_pipeline/ingestion_service.py
app/routers/search.py
query_examples.py
output_examples.txt
docs/session08_search_demo.html
```

Session 08 introduced persisted PostgreSQL plus pgvector retrieval, document and chunk tables, JSONB metadata, cosine distance search, duplicate source path handling, and opt-in DB integration tests.

The historical Session 08 API examples are preserved in `query_examples.py` and `output_examples.txt`.

## Session 08 search-quality evaluation workflow

Artifacts:

```text
evals/session08_search_quality/cases.jsonl
evals/session08_search_quality/evaluator.py
evals/session08_search_quality/capture.py
evals/session08_search_quality/REPORT.md
```

Safety boundaries:

1. No LLM judge.
2. No live provider call in tests.
3. No benchmark superiority claim.
4. Captured responses should be reviewed before committing.

Dry-run capture payloads before any live API call:

```bash
cd /workspaces/ai-engineering/estimador-cag
uv run python -m evals.session08_search_quality.capture --output /tmp/session08_search_responses.json --dry-run
```

Capture responses from a running local FastAPI service:

```bash
cd /workspaces/ai-engineering/estimador-cag
uv run python -m evals.session08_search_quality.capture --base-url http://localhost:8000 --output /tmp/session08_search_responses.json --report /tmp/session08_search_quality_report.md
```

Evaluate an already captured response map offline:

```bash
cd /workspaces/ai-engineering/estimador-cag
uv run python -m evals.session08_search_quality.evaluator --responses /tmp/session08_search_responses.json --report /tmp/session08_search_quality_report.md
```

## Provider policy inherited by later sessions

DeepSeek is the preferred real provider for bounded live checks. Kimi is useful as fallback or comparison. Normal CI and committed evaluation reports should stay deterministic.
