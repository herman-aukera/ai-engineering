# Session 13 Plus — checkpoint history and scenarios

The control room exposes persisted checkpoint history without invoking graph
nodes or mutating canonical state. A selected checkpoint can be inspected with
its exact checkpoint ID, state, timestamp and pending nodes.

Scenario branching clones checkpoint-safe state into a new estimation UUID and
thread. The branch records `scenario_id`, `parent_estimation_id` and
`parent_checkpoint_id`; the source thread is never updated. Comparison reports
hours, evidence count, Critic findings, estimated cost and elapsed time.

Endpoints:

```text
GET  /api/v1/estimate/graph/reviewed/{id}/checkpoints
GET  /api/v1/estimate/graph/reviewed/{id}/checkpoints/{checkpoint_id}
POST /api/v1/estimate/graph/reviewed/{id}/scenarios
POST /api/v1/estimate/graph/reviewed/scenarios/compare
```

The Streamlit control room can load history, create an isolated scenario and
compare two estimation IDs. This is non-destructive time travel; canonical
rollback or history rewriting is intentionally unsupported.
