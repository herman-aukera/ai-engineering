# Estimation Control Room V2 architecture

## Direction

V2 is an additive product API over the durable reviewed LangGraph execution. It
does not ask the user to choose `legacy` or `graph`, and it does not run both
estimators before selecting a result.

```text
V2 request
  -> canonical execution policy
  -> reviewed LangGraph service
  -> PostgreSQL checkpoint thread
  -> canonical V2 projection
  -> V2 API and Control Room
```

The existing V1 and session endpoints remain available as rollback and
compatibility surfaces. The graph remains the V2 source of execution truth.

## First vertical slice

The first slice introduces:

- strict Pydantic V2 domain models for context, requirements, modules, tasks,
  deterministic estimates, evidence, provenance, policies, provider usage,
  human decisions, lineage and audit metadata;
- Python-owned task, module and project arithmetic;
- four operational execution profiles;
- a projection from one reviewed graph checkpoint into one canonical V2
  response;
- additive create, inspect, action, checkpoint, scenario, comparison and audit
  endpoints;
- the same durable structure and final-review gates already proven by the Plus
  graph.

At this slice boundary, one graph component projects to one module containing
one task. Rich multi-task structure generation and the unified visual editor
are the next product slice; the audit endpoint records this limitation.

## Invariants

- One V2 request creates one graph estimation identity and one checkpoint
  thread.
- Provider output cannot author authoritative arithmetic.
- V2 actions resume the same thread and use existing stale-revision guards.
- V1 remains unchanged.
- Profiles are checkpointed as `v2_profile`, not held only in browser memory.
- Prompts, transcripts, credentials and raw provider responses are excluded
  from audit exports.
