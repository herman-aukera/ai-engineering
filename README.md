# AI Engineering Coursework

This repository contains the LIDR AI Engineering coursework.

## Current submission

- Active project: `estimador-cag/`
- Current branch: `gg-session-13/pre-work`
- Teacher-facing branch: `session-13/pre-work`
- Deliverable: **Session 13 — agent orchestration with LangGraph**

Teacher-facing branch:

https://github.com/herman-aukera/ai-engineering/tree/session-13/pre-work

## What Session 13 delivers

The Session 12 hand-written estimation loop has been re-expressed as an
explicit LangGraph workflow inside the AI service:

```text
START
  -> extract_requirements
  -> classify_components
  -> search_budgets
  -> generate_estimate
  -> validate_and_consolidate
  -> END
```

The mandatory pre-session implementation includes:

1. Typed shared graph state.
2. Accumulator reducers using `Annotated[..., operator.add]`.
3. Five sequential nodes that return partial state updates.
4. An additive graph endpoint at `POST /api/v1/estimate/graph`.
5. PostgreSQL persistence through `AsyncPostgresSaver`.
6. Stable thread identity derived from the estimation identifier.
7. A Logfire root span and one child span per graph node.
8. A complete execution trace for the complex sample transcript.
9. Deterministic fake adapters for CI.
10. Separate live PostgreSQL, Logfire, and provider evidence.

## Evidence

- Deterministic execution:
  `estimador-cag/artifacts/session13/complex_graph_execution_deterministic.json`
- PostgreSQL persistence:
  `estimador-cag/artifacts/session13/postgres_persistence_proof.json`
- Live PostgreSQL and Logfire trace:
  `estimador-cag/artifacts/session13/live_postgres_logfire_trace_summary.json`
- Auxiliary live-provider smoke:
  `estimador-cag/artifacts/session13/live_provider_smoke/`
- Mandatory compliance:
  `estimador-cag/docs/session13_task13_compliance.md`
- Non-mandatory Plus roadmap:
  `estimador-cag/docs/session13_plus_roadmap.md`
- Plus credentialed runtime evidence:
  `estimador-cag/docs/session13_plus_live_runtime_evidence.md`
- Spanish presentation guide:
  `estimador-cag/docs/session13_presentation_guide_es.md`

## Validation snapshot

The latest implementation checkpoint passed:

```text
667 passed, 9 skipped
Ruff passed
Python compilation passed
Secret scan passed
Remote CI passed
```

Normal CI remains deterministic. Real-provider and hosted observability checks
are manual and opt-in.

## Scope boundary

Parallel retrieval with the LangGraph `Send` API, advanced retry/fallback
policies, circuit breakers, `interrupt()`-based human review, and the full graph
wizard UI are tracked as Session 13 Plus work. They are not claimed as part of
the mandatory pre-session submission.

## Historical Session 10 retrieval work

Session 10 remains available as historical coursework:

```text
Branch: gg-session-10/pre-work
Deliverable: Session 10 — advanced retrieval compass and A/B/C/D retrieval evaluation
```

### A/B/C/D retrieval variants

The deterministic historical runner is:

```zsh
cd /workspaces/ai-engineering/estimador-cag
uv run python -m evals.session10_retrieval.run   --output evals/session10_retrieval/results.json   --report evals/session10_retrieval/REPORT.md   --k 5   --recall-k 8
```

Historical outputs:

```text
evals/session10_retrieval/results.json
evals/session10_retrieval/REPORT.md
```

The historical report distinguishes `result budget precision@5` from
`unique budget precision@5`. The small corpus provided wiring and smoke
evidence; it was not proof that hybrid search or reranking improves quality in
production.

Historical provider policy: prefer DeepSeek first and use Kimi only as fallback
or comparison.

Security policy: Do not commit `.env`, real API keys, copied credentials, or
credential-bearing connection strings.
