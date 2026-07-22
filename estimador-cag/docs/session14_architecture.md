# Session 14 multi-agent architecture

## Purpose

Session 14 reorganizes the inherited estimation workflow as a supervised
LangGraph without replacing the business contract or the Session 13
PostgreSQL checkpointer.

## Control flow

```text
START
  -> supervisor
     -> requirements_extractor -> supervisor
     -> budget_searcher        -> supervisor
     -> estimate_generator     -> supervisor
     -> coherence_validator    -> supervisor
     -> human_review_gate
          -> interrupt
          -> approve / adjust / reject
     -> finalize
  -> END
```

The supervisor is implemented directly with `StateGraph` and typed
`Command` returns. Python owns prerequisites, route allow-lists, hop limits,
reliability policy, authoritative arithmetic, and human-review enforcement.
The graph does not use `create_supervisor` or a hidden routing abstraction.

## Shared-state contract

`Session14EstimationGraphState` extends the Session 13 state with:

- supervisor identity and route metadata;
- replay-safe `route_events` and `agent_contributions` reducers;
- reliability signals and human-review state;
- revision and idempotency metadata;
- partial specialist contributions.

Runtime clients, database connections, checkpointers, secrets, prompts, and
hidden reasoning are excluded from graph state.

## Agents and authority

| Agent | Business-tool privilege | Responsibility |
| --- | --- | --- |
| `requirements_extractor` | none | Extract and classify requirements |
| `budget_searcher` | `search_budgets` | Retrieve historical evidence |
| `estimate_generator` | `calculate_estimate` | Derive component hours |
| `coherence_validator` | `validate_estimate` | Validate reliability |
| `supervisor` | none | Route only |

The privilege registry is static and server-owned. A transcript cannot grant
an agent another tool.

## Human-in-the-loop boundary

The graph pauses when confidence is below the configured threshold, the
estimate is outside its historical range, or no historical precedent exists.
The interrupt payload exposes identifiers, revision, reason codes, a compact
estimate summary, confidence, range status, evidence count, findings, and
allowed actions. It excludes the transcript and infrastructure secrets.

`approve`, `adjust`, and `reject` resume the original thread. Adjustments are
recalculated in Python. Revision checks prevent stale decisions; idempotency
keys make exact retries safe and reject conflicting reuse.

## Persistence and observability

`AsyncPostgresSaver` persists the pause. A stable thread ID derived from the
estimation ID reconnects a later request to the same checkpoint. Root graph
spans and node spans use sanitized attributes; the domain trace separately
records route decisions, specialist contributions, pause, and resume.

## Claim boundary

This architecture proves the required cooperative supervisor/workers pattern
and durable human control. It does not claim that multi-agent orchestration is
universally better than a linear graph, that provider routing is calibrated,
or that this coursework system is production-ready.
