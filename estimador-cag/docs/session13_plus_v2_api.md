# Unified Estimation API V2

## Endpoints

```text
POST /api/v2/estimations
GET  /api/v2/estimations/{estimation_id}
POST /api/v2/estimations/{estimation_id}/actions
GET  /api/v2/estimations/{estimation_id}/checkpoints
POST /api/v2/estimations/{estimation_id}/scenarios
POST /api/v2/estimations/scenarios/compare
GET  /api/v2/estimations/{estimation_id}/audit
```

Create accepts a `ProjectContextV2`, an optional stable UUID and one profile:

```text
cost_first | balanced | quality_first | human_controlled
```

The response contains the canonical estimation, valid next actions and safe
LangGraph interrupt payloads. Structure actions are approve, edit, reject and
regenerate. Final actions are approve, override, request recovery and reject.

All request models reject undeclared fields. Final actions require an actor;
edits require typed requirements and modules; stale revisions return HTTP 409.

## Compatibility

V2 is additive. `/api/v1`, reviewed graph and session endpoints remain intact.
There is no implicit graph-to-legacy fallback. A runtime outage remains an
explicit service error.
