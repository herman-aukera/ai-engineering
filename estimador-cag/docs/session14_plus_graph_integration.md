# Session 14 Plus — Provider and Context Graph Integration

## Slice

`14P-2`

## Architecture

The submitted `session14_estimation_graph` remains unchanged. Plus work uses a separate graph:

```text
START
→ policy_bootstrap
→ supervisor
→ least-privilege specialist
→ supervisor
→ ...
→ human_review_gate | finalize
```

The Plus graph adds two deterministic controls:

1. `policy_bootstrap`
   - derives bounded complexity signals;
   - creates the versioned V3 route plan;
   - validates every primary route against an injected capability registry;
   - fails closed when a model is unregistered, disabled, or lacks the required output, reasoning, or tool capabilities;
   - creates the first compacted context projection.
2. context-aware supervisor wrapper
   - preserves the mandatory hand-built supervisor and its deterministic guards;
   - refreshes the compacted context after every route decision;
   - records a replay-safe compaction event before the graph can enter human review or finalize.

## Authority and source of truth

The capability registry is server-owned and injected at graph construction. Documentation or configuration alone does not enable a provider route.

The compacted context is derived evidence. Authoritative data remains in:

- graph checkpoints;
- route events;
- specialist contributions;
- human action records;
- evidence references;
- estimate and validation state.

The projection excludes raw transcript, prompts, hidden reasoning, raw provider output, credentials, and secret-like values.

## State additions

- `plus_policy_version`
- `plus_execution_profile`
- `plus_context_detail`
- `plus_complexity_assessment`
- `plus_routing_plan`
- `plus_authorized_capabilities`
- `plus_context_source_revision`
- `plus_compacted_context`
- replay-safe `plus_context_compaction_events`

## Compatibility

- Mandatory branch: unchanged.
- Mandatory graph: unchanged.
- Existing API: unchanged.
- Plus graph: additive and not selected by the current production composition root.
- Rollback: select the mandatory graph or reset the Plus branch to the previous Plus checkpoint.

## Claim boundary

This slice proves graph-level policy authorization and deterministic context refresh. It does not prove live provider availability, provider quality superiority, lossless compaction, or product API/UI exposure.
