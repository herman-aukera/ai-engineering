# Session 13 Task 13 Compliance

## Purpose

This document maps the implementation to the mandatory Session 13
homework and separates required evidence from non-mandatory evolution.

## Mandatory compliance matrix

| Homework requirement | Status | Implementation or evidence |
| --- | --- | --- |
| Typed shared state | Complete | `app/generation/graph/state.py` |
| At least one accumulator reducer | Complete | `budget_matches`, `errors`, `trace_events` |
| Five required nodes | Complete | `app/generation/graph/nodes/` |
| Sequential `START` to `END` topology | Complete | `app/generation/graph/build.py` |
| Nodes return partial updates | Complete | Node tests and reducer invariants |
| Existing S9–S12 logic reused | Complete | Injected runtime ports and retrieval adapters |
| Existing outward contract preserved | Complete | Additive `POST /api/v1/estimate/graph` adapter |
| Structured estimate includes status | Complete | `validated` or `needs_review` |
| PostgreSQL checkpointer | Complete | `AsyncPostgresSaver` in FastAPI lifespan |
| Existing PostgreSQL reused | Complete | Same project PostgreSQL service |
| Stable thread identity | Complete | Derived from `estimation_id` |
| Complete execution | Complete | Deterministic complex execution artifact |
| One span per node | Complete | Five `session13.graph.node` child spans |
| Complete trace | Complete | Root span plus five children in Logfire |
| Complex sample evidence | Complete | Deterministic and hosted trace artifacts |
| Branch accessible | Complete | `session-13/pre-work` |
| Remote deterministic CI | Complete | Latest implementation checkpoint green |

## Mandatory topology

```text
START
  -> extract_requirements
  -> classify_components
  -> search_budgets
  -> generate_estimate
  -> validate_and_consolidate
  -> END
```

## Persistence evidence

`artifacts/session13/postgres_persistence_proof.json` proves:

- graph state was written to PostgreSQL;
- the checkpointer was closed;
- a new checkpointer instance reopened the same database;
- the same thread was reread;
- completed graph nodes were not executed again;
- the recovered state matched the written state.

## Observability evidence

`artifacts/session13/live_postgres_logfire_trace_summary.json` records:

```text
Trace ID:
019f66df5be5e9f5db11c167f81b79dd

Root span:
session13.graph.run

Child spans:
5 x session13.graph.node

Terminal status:
validated

Total hours:
168.0
```

Hosted telemetry excludes transcript text, prompts, raw state, provider
payloads, credentials, and database DSNs.

## Validation evidence

Pre-documentation implementation checkpoint:

```text
667 passed, 9 skipped
Ruff passed
Python compilation passed
Secret scan passed
Remote CI run 29441093693 passed
```

Real-provider execution remains separate from deterministic CI.

## Improvements beyond the minimum reference

1. Deterministic Python arithmetic instead of model-generated totals.
2. Provenance-rich retrieval evidence.
3. Provider-neutral ports and deterministic fakes.
4. Root graph span plus the five mandatory node spans.
5. Separate domain trace, telemetry trace, and logs.
6. Explicit new, resume, completed-duplicate, replay, and recalculation semantics.
7. Reducer duplication protection.
8. Adversarial mutation-isolation tests for external adapters.
9. PostgreSQL close/reopen/reread proof.
10. Sanitized observability attributes.
11. Immutable execution evidence protected by tests.
12. Manual live-provider smoke separated from normal CI.

## Optional Level 3

A conditional terminal edge was optional. The mandatory graph keeps the
direct edge to `END`; `validate_and_consolidate` sets either
`validated` or `needs_review`.

This avoids pretending that serious retry, fallback, or human
intervention already exists.

## Explicitly not implemented in the pre-session branch

- `Send` API parallel retrieval;
- retry with backoff;
- provider fallback nodes;
- circuit breakers;
- `interrupt()`-based HITL;
- Actor-Critic-Boss orchestration;
- full graph review wizard;
- production provider benchmark matrix.

They are tracked in `docs/session13_plus_roadmap.md`.

## Delivery checklist

- [x] Teacher-facing branch exists.
- [x] Mandatory graph executes end to end.
- [x] PostgreSQL persistence is proven.
- [x] Hosted trace is visible.
- [x] One span exists for every node.
- [x] Deterministic CI is green.
- [x] Evidence artifacts are committed.
- [x] Front-door documentation describes Session 13.
- [ ] Direct shareable Logfire trace URL copied into the email.
- [ ] Email sent to Lia.
