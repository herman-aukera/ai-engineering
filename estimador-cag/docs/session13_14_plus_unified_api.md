# Session 13 + 14 Plus — Unified API

## Additive routes

The unified product path is additive and versioned. Existing routes remain available.

### Runtime readiness

```http
GET /api/v1/estimate/graph/unified/readiness
```

Response:

```json
{
  "ready": true,
  "graph_name": "session13_14_plus_unified_graph",
  "graph_version": "session13_14_plus.unified.v1",
  "runtime_error": null,
  "rollback_paths": [
    "/api/v1/estimate/graph",
    "/api/v1/estimate/graph/reviewed/start"
  ]
}
```

The error field contains only a sanitized exception type. It never includes credentials or connection strings.

### Standard estimate

```http
POST /api/v1/estimate/graph/unified
Content-Type: application/json
```

```json
{
  "transcript": "Source request",
  "estimation_id": "optional-uuid"
}
```

The response uses the existing `GraphEstimationResponse` contract. It exposes the structured estimate and lifecycle status but not internal state.

### Standard resume

```http
POST /api/v1/estimate/graph/unified/{estimation_id}/resume
Content-Type: application/json
```

Approve:

```json
{
  "action": "approve",
  "expected_revision": 1,
  "actor": "reviewer",
  "reason": null,
  "adjustments": [],
  "idempotency_key": "decision-unique-key"
}
```

Adjust requires typed adjustments. Reject requires a reason. A stale revision or conflicting idempotency key returns HTTP 409.

## Sanitized Control Room routes

### Start/control projection

```http
POST /api/v1/estimate/graph/unified/control
```

The request matches the standard estimate request. The response is `UnifiedControlProjection`, an allowlisted control-plane view containing:

- estimation and thread identity;
- execution status and unified phase;
- human-review status, revision and reason codes;
- unified route ledger;
- typed Critic report;
- Boss recommendation;
- reliability report;
- candidate IDs, totals, fingerprints and Energy assessment;
- capability record IDs;
- compact-context ID, fingerprint, detail and source revision;
- evidence references;
- proposal projection;
- rollback paths.

It excludes:

- transcript;
- prompts;
- hidden reasoning;
- raw provider responses;
- tokens, keys and passwords;
- DSNs and authorization values.

### Resume/control projection

```http
POST /api/v1/estimate/graph/unified/control/{estimation_id}/resume
```

This resumes the same persisted thread and returns a refreshed sanitized projection.

## Error contract

| Condition | Status |
|---|---:|
| unified runtime unavailable | 503 |
| estimation/thread not found | 404 |
| stale revision or idempotency conflict | 409 |
| incomplete adjustment/reject contract | 422 |
| invalid backend projection | 502 |
| internal execution failure | 502 |

Internal error details are logged through sanitized observability and are not returned as raw provider/database content.

## Composition-root isolation

FastAPI owns three independent services:

```text
app.state.graph_estimation_service
app.state.reviewed_graph_estimation_service
app.state.unified_graph_estimation_service
```

Each initialization failure is captured separately. The unified path failing does not change the route contracts of older paths.

## Control Room

Run:

```zsh
cd /workspaces/ai-engineering/estimador-cag
ESTIMADOR_BACKEND_URL=http://localhost:8000 \
  uv run streamlit run app/ui/unified_control_room.py
```

The UI communicates only with the unified readiness and control endpoints. It does not request raw graph state.

## Rollback paths

```text
Supervised Session 14:
POST /api/v1/estimate/graph

Reviewed Session 13 Plus:
POST /api/v1/estimate/graph/reviewed/start
```

No automatic migration or fallback between graph versions occurs for an existing thread.
