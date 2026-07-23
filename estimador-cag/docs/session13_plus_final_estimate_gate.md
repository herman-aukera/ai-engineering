# Session 13 Plus — durable final estimate gate

The reviewed graph now places a distinct human gate after the typed Critic and
deterministic Boss. It uses LangGraph `interrupt()` and the same stable thread
identity as structure review.

Supported decisions:

- `approve`: accept the deterministic evidence-backed estimate;
- `reject`: stop with an auditable reason;
- `request_recovery`: run only selective recovery, deterministic recalculation,
  validation, Critic and Boss before presenting a new gate revision;
- `override`: apply typed per-component human baselines with actor, reason,
  evidence references, old/new values and changed fields.

Every decision includes `expected_revision`. An obsolete response fails with a
conflict instead of overwriting newer state. Overrides do not replace or delete
retrieval evidence: the original budget matches remain in checkpoint state and
the estimate explicitly records `human_baseline_override` as its derivation.

API endpoint:

```text
POST /api/v1/estimate/graph/reviewed/{estimation_id}/resume/final
```

The Streamlit control room renders the final interrupt and supports all four
actions. PostgreSQL process-restart proof remains a separate promotion gate;
in-memory and graph-contract tests do not claim that higher evidence level.
