# Estimador CAG

## Current Session 13 status

Current branch:

```text
gg-session-13/pre-work
```

Teacher-facing branch:

```text
session-13/pre-work
```

Current focus:

> Replace the Session 12 hand-written agent loop with a typed, persistent, and
> observable LangGraph workflow while preserving the existing external
> estimation contract.

## Mandatory graph

```text
START
  -> extract_requirements
  -> classify_components
  -> search_budgets
  -> generate_estimate
  -> validate_and_consolidate
  -> END
```

The mandatory path remains sequential. Parallel fan-out, advanced recovery, and
human intervention are deliberately deferred to the Plus roadmap.

## Public API integration

The graph is exposed through the additive endpoint:

```text
POST /api/v1/estimate/graph
```

The existing estimation endpoint and Streamlit path were not silently replaced
during the mandatory milestone. This preserves rollback and allows
compatibility to be proven before broader migration.

The graph endpoint receives a transcript and returns a structured estimate with
a terminal status. Graph internals are not leaked into the business-backend
contract.

## Shared state

`app/generation/graph/state.py` defines checkpoint-safe typed state containing:

- transcript and estimation identity;
- structured requirements;
- classified components;
- provenance-rich budget matches;
- deterministic component estimates;
- consolidated estimate and status;
- structured issues;
- domain trace events;
- sanitized provider metadata;
- execution metadata.

Reducer-backed fields include:

- `budget_matches`;
- `errors`;
- `trace_events`.

Nodes return partial updates. Reducer-backed nodes return only newly generated
entries, not the complete accumulated list.

## Node responsibilities

| Node | Responsibility |
| --- | --- |
| `extract_requirements` | Convert the transcript into atomic structured requirements |
| `classify_components` | Group requirements into implementation components |
| `search_budgets` | Retrieve reference evidence sequentially per component |
| `generate_estimate` | Calculate hours and totals deterministically in Python |
| `validate_and_consolidate` | Apply invariants and set terminal status |

Model and retrieval access is hidden behind injected ports. Deterministic fakes
are used in normal CI; concrete adapters are used at runtime.

## Persistence

The graph uses `AsyncPostgresSaver` with the existing project PostgreSQL
database.

Application lifecycle responsibilities are:

1. Open the checkpointer during FastAPI lifespan.
2. Run checkpointer setup.
3. Compile the graph with the saver.
4. Invoke with a stable storage-safe thread identifier.
5. Close resources during shutdown.

The implementation includes close/reopen/reread evidence proving that state can
be recovered without executing completed nodes again.

## Execution semantics

- New execution: starts a new thread.
- Resume: continues only an incomplete thread.
- Completed duplicate: returns the existing terminal result idempotently.
- Replay: requires an explicit checkpoint identity.
- Recalculation: uses a new thread.

These semantics prevent accumulator reducers from appending historical values a
second time.

## Observability

Logfire is used for hosted telemetry.

Each execution produces:

- one root span named `session13.graph.run`;
- five child spans named `session13.graph.node`;
- sanitized identifiers, counts, status, and totals;
- no transcript, prompt, provider response, API token, or database DSN.

The domain trace stored in graph state is separate from telemetry spans and
operational logs.

Final trace identifier:

```text
019f66df5be5e9f5db11c167f81b79dd
```

Logfire project:

https://logfire-eu.pydantic.dev/herman-aukera/starter-project

## Evidence files

```text
artifacts/session13/complex_graph_execution_deterministic.json
artifacts/session13/postgres_persistence_proof.json
artifacts/session13/live_postgres_logfire_trace_summary.json
artifacts/session13/live_provider_smoke/REPORT.md
artifacts/session13/live_provider_smoke/metadata.json
artifacts/session13/live_provider_smoke/results.csv
```

The auxiliary live-provider smoke completed operationally, but its historical
Session 06 latency and memory-drift thresholds did not pass. That result is
preserved honestly and is not treated as a mandatory Session 13 acceptance
gate.

## Deterministic validation

```zsh
cd /workspaces/ai-engineering/estimador-cag

uv run ruff check app scripts tests evals

find app scripts tests evals -name '*.py' -type f -print0 |
  xargs -0 uv run python -m py_compile

OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q
```

## Session 13 documentation

- `docs/session13_task13_compliance.md`
- `docs/session13_plus_roadmap.md`
- `docs/session13_presentation_guide_es.md`

## Historical Session 12 agentic work

The Session 12 — hand-written agent loop is preserved from branch
`gg-session-12/pre-work`.

Session 12 agentic handoff:

- `docs/session12_agentic_handoff.md`
- `docs/session12_task12_compliance.md`

## Historical Session 10 retrieval background

The historical retrieval stack remains available:

| Layer | Files |
| --- | --- |
| Fusion | `app/embedding_pipeline/fusion.py` |
| Reranking | `app/embedding_pipeline/reranker.py` |
| Search API | `POST /search` |
| Evaluation | `evals/session10_retrieval/` |

Historical A/B/C/D matrix:

| Config | Search | Reranking |
| --- | --- | --- |
| A | Vector | No |
| B | Hybrid | No |
| C | Vector | Yes |
| D | Hybrid | Yes |

Historical runner:

```zsh
uv run python -m evals.session10_retrieval.run   --output evals/session10_retrieval/results.json   --report evals/session10_retrieval/REPORT.md   --k 5   --recall-k 8
```

The report distinguished `result budget precision@5` from
`unique budget precision@5`. The corpus has only four budgets, eight component
chunks, and seven clean queries plus challenge cases, so the result does not
prove hybrid retrieval or reranking superiority.

Historical provider policy: prefer DeepSeek first and use Kimi only as fallback
or comparison.

Historical notes remain indexed in `docs/HISTORICAL_SESSIONS.md`.
