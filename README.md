# AI Engineering Coursework

This repository contains the LIDR AI Engineering coursework.

## Current submission

- Active project: `estimador-cag/`
- Current branch: `session-14/pre-work`
- Teacher-facing branch: `session-14/pre-work`
- Deliverable: **Session 14 — supervised specialists and persistent human review**

Teacher-facing branch:

https://github.com/herman-aukera/ai-engineering/tree/session-14/pre-work

## Current Session 14 status

The hand-built supervisor, least-privilege specialists, guarded model route
proposals, persistent approve/adjust/reject review, revision/idempotency guards,
and sanitized Level 3 action audit are implemented. Local validation at the
observability-repair worktree passed `908 passed, 11 skipped`, Ruff, Python
compilation, and the real PostgreSQL three-lifecycle restart test.

A secure hosted evidence workflow now exists for the exact ORBITA teacher
fixture. It creates one parent Logfire journey containing the pause, PostgreSQL
close/reopen, same-thread resume through the public endpoint, terminal reread,
and sanitized hosted verification. The workflow reads
`SESSION14_LOGFIRE_TOKEN` only from GitHub Actions secrets and never commits or
uploads the credential. A fresh public share URL must be created from the
captured trace after the credentialed workflow succeeds.

Session 13 material below is retained as historical architecture inherited by
Session 14.

Inherited Session 13 references retained for coursework continuity:
`gg-session-13/pre-work` (development) and `session-13/pre-work`
(teacher-facing).
Historical deliverable label: **Session 13 — agent orchestration with LangGraph**.

## Historical Session 13 delivery

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
