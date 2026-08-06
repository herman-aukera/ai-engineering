# Estimador CAG

## Current consolidation candidate

```text
Working mode: LIDR coursework continuity + Session 13/14 Plus semantic consolidation
Branch: gg-session-14/plus-consolidated
Draft PR: #21
PR base: gg-session-14/plus
Graph: session13_14_plus_unified_graph
Graph version: session13_14_plus.unified.v1
Status: draft, open, unmerged; review candidate with bounded evidence debt
```

This branch semantically consolidates the mature Session 13 Plus reviewed lifecycle with Session 14 Plus supervision, persistent human authority, capability/context controls, deterministic candidate competition and Energy policy. It does not replace or modify the source branches.

Canonical entrypoints:

- `docs/session13_14_plus_unified_architecture.md`
- `docs/session13_14_plus_unified_migration_map.md`
- `docs/session13_14_plus_unified_state_and_reducers.md`
- `docs/session13_14_plus_unified_api.md`
- `docs/session13_14_plus_unified_evidence.md`
- `docs/session13_14_plus_unified_audit.md`
- `docs/session13_14_plus_unified_final_handoff.md`

## Authority model

```text
Models and specialists -> typed proposals, findings and evidence
Critic                -> typed defects; no route authority
Boss policy           -> deterministic bounded recommendation
Unified supervisor    -> every graph transition
Python policy         -> arithmetic, hard constraints, Energy, budgets and privileges
Persistent human gate -> approve, adjust or reject protected outcomes
```

Every final human decision returns to the supervisor:

```text
approve/adjust -> supervisor -> proposal -> supervisor -> finalize
reject         -> supervisor -> stopped finalization
```

## Unified lifecycle

```text
START
-> policy_bootstrap
-> supervisor
-> structure phase and optional structure review
-> supervisor
-> bounded retrieval with sequential fallback
-> deterministic estimate
-> supervisor
-> four-candidate competition and Energy
-> supervisor
-> reliability analysis
-> typed Critic and deterministic Boss recommendation
-> supervisor
-> bounded selective recovery when justified
-> supervisor
-> independent coherence validation
-> supervisor
-> persistent human review when required
-> supervisor
-> proposal or stopped finalization
-> supervisor/finalize
-> END
```

## Unified API

```text
GET  /api/v1/estimate/graph/unified/readiness
POST /api/v1/estimate/graph/unified
POST /api/v1/estimate/graph/unified/{estimation_id}/resume
POST /api/v1/estimate/graph/unified/control
POST /api/v1/estimate/graph/unified/control/{estimation_id}/resume
```

Rollback routes remain available:

```text
POST /api/v1/estimate/graph
POST /api/v1/estimate/graph/reviewed/start
```

The control routes return an allowlisted projection. Raw graph state, source transcript, prompts, hidden reasoning, raw provider output, credentials and connection strings are excluded.

## Persistence, reducers and provider boundary

The unified runtime uses `AsyncPostgresSaver` and stable `estimate:<estimation_id>` thread identity. Exact-head infrastructure evidence covers interrupt, close/reopen, same-thread revision-guarded resume, finalization and terminal reread equality.

Replay-sensitive core evidence/error/trace reducers use stable semantic identities, deduplicate identical replay, reject conflicting reuse and retain first-seen rank/order/chronology. The inherited `stage_route_events` accumulator remains documented bounded debt because it still relies on completed-node guards.

Historical benchmark calibration is distinct from present reachability. Both primary and fallback routes must be capability-authorized. Unsupported effort, excessive output, missing fallback and unknown model identities fail closed. Deterministic CI performs no paid provider calls.

## Control Room

```zsh
ESTIMADOR_BACKEND_URL=http://localhost:8000 \
  uv run streamlit run app/ui/unified_control_room.py
```

The implementation and privacy/decision helpers are deterministic-contract-tested. No browser screenshot or human-visible smoke artifact is part of current CI evidence, so the UI is browser-unverified.

## Current Session 13 status — historical submission compatibility

This section preserves the mandatory Session 13 coursework front door and its tested historical contracts. It is not the current consolidation branch.

Current branch:

```text
gg-session-13/pre-work
```

Teacher-facing branch:

```text
session-13/pre-work
```

Historical graph endpoint:

```text
POST /api/v1/estimate/graph
```

Historical Session 13 evidence and instructions:

- `docs/session13_task13_compliance.md`
- `docs/session13_plus_roadmap.md`
- `docs/session13_plus_live_runtime_evidence.md`
- `docs/session13_presentation_guide_es.md`
- `artifacts/session13/complex_graph_execution_deterministic.json`
- `artifacts/session13/postgres_persistence_proof.json`
- `artifacts/session13/live_postgres_logfire_trace_summary.json`

Deterministic validation command retained for coursework compatibility:

```zsh
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q
```

Historical provider policy: prefer DeepSeek first and use Kimi only as fallback or comparison.

The Session 13 trace identifier remains historical evidence:

```text
019f66df5be5e9f5db11c167f81b79dd
```

## Historical Session 12 agentic work

The Session 12 — hand-written agent loop is preserved from branch `gg-session-12/pre-work`.

Session 12 agentic handoff:

- `docs/session12_agentic_handoff.md`
- `docs/session12_task12_compliance.md`

That material documents the hand-written tool loop, provider-plan evidence and its original claim boundaries. It does not replace the LangGraph Session 13/14 paths.

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
uv run python -m evals.session10_retrieval.run \
  --output evals/session10_retrieval/results.json \
  --report evals/session10_retrieval/REPORT.md \
  --k 5 \
  --recall-k 8
```

The report distinguishes `result budget precision@5` from `unique budget precision@5`. The corpus has only four budgets, eight component chunks and a small query set, so it does not prove hybrid retrieval or reranking superiority.

Historical session references remain indexed in `docs/HISTORICAL_SESSIONS.md`.

## Claim boundary

Supported only by a successful exact-head workflow and same-SHA artifacts:

- a separately versioned unified graph exists;
- one supervisor owns graph transitions;
- protected human decisions return through the supervisor;
- additive API and rollback paths exist;
- PostgreSQL and production-container gates validate the exact source head.

Not established:

- production readiness or superiority;
- current reachability of every historically calibrated provider;
- lossless context compaction;
- automatic migration of historical checkpoints;
- browser-validated Control Room usability;
- authorization to merge or retire rollback paths.
