# Session 13 Plus P0 — Existing-product integration bridge

Status: implementation complete; consolidated validation pending.

This document applies only to branch `gg-session-13/plus`. The mandatory
teacher-facing Session 13 branches remain frozen at commit
`a90390d7f912d98988a2e09de078b6b5e55d108e`.

## Objective

Integrate the checkpointed Session 13 graph with one controlled existing product
path without replacing the mandatory endpoint or duplicating estimation
arithmetic.

Controlled path:

```text
POST /sessions/{session_id}/estimate
```

Unchanged paths:

```text
POST /api/v1/estimate
POST /api/v1/estimate/stream
POST /api/v1/estimate/graph
```

## Configuration and rollback

```text
ESTIMATION_BACKEND=legacy
```

remains the default and preserves the established `estimate_product` call.

```text
ESTIMATION_BACKEND=graph
```

selects the lifespan-owned `GraphEstimationApplication` for the conversational
session route.

Rollback requires only restoring `ESTIMATION_BACKEND=legacy` and restarting the
application. Legacy mode does not require the graph runtime to be available.
Unsupported values fail during Pydantic settings validation.

The Session 06 stress fake remains an explicit operational override and runs
before backend dispatch. It is not treated as a third product backend.

## Call path

```text
multipart session request
  -> session lookup and input guardrails
  -> attachment extraction
  -> typed EstimationRequest
  -> stress fake override, when enabled
  -> async estimation dispatcher
       -> legacy operation
            -> existing estimate_product call shape
       -> graph operation
            -> lifespan-owned GraphEstimationApplication
            -> GraphEstimationRun
            -> graph/product response adapter
  -> session history and metadata update
  -> TurnObservation
  -> HTTP response
```

The dispatcher owns selection only. It does not estimate, adapt responses,
create PostgreSQL resources, or initialize LangGraph.

## Response compatibility

Legacy and graph responses are not claimed to be semantically identical.

The legacy product contract contains phases, duration in weeks, confidence, and
a structured `EstimationResult`. The graph contract contains component hours,
retrieval provenance, deterministic totals, review state, trace events,
checkpoint identifiers, and provider metadata.

Graph mode therefore returns:

- `result: null` rather than fabricated legacy phases;
- deterministic Markdown in `text` for the existing UI fallback;
- `estimation_backend: graph`;
- `compatibility.parity: partial`;
- the complete validated graph payload under `graph_estimation`.

The additive `/api/v1/estimate/graph` endpoint and the session bridge reuse the
same graph-run-to-response validation function to avoid contract drift.

## Error behavior

| Condition | HTTP behavior on session route |
| --- | --- |
| Graph selected and lifespan service unavailable | `503` |
| Graph selected and execution fails | `502` |
| Legacy provider timeout | Existing `502` mapping preserved |
| Legacy runtime failure | Existing `502` mapping preserved |
| Stress fake enabled | Deterministic stress response, before dispatch |

Graph mode does not silently fall back to legacy. Silent fallback would hide a
broken deployment and make backend evidence ambiguous.

## Implemented contracts

- typed backend selector with `legacy` default;
- async selection dispatcher with exactly-one-operation semantics;
- session bridge preserving the existing legacy call shape;
- graph response validation and honest partial adaptation;
- configuration-only rollback;
- explicit graph-unavailable and graph-failure mapping;
- stress-fake precedence;
- focused unit and route integration tests.

## Current limitations

- Consolidated local Ruff, compilation, full pytest, secret scan, and remote CI
  evidence must still be captured after pulling the final implementation.
- Graph mode includes the current transcript and extracted attachment text in
  graph input. Conversation history and project metadata remain owned and
  updated by the session layer, but the mandatory graph service does not yet
  consume them as separate typed inputs.
- Each session request starts a new graph estimation identity. Cross-turn graph
  resume is not claimed.
- The current Streamlit UI uses its existing text fallback for graph mode. A
  graph-aware read-only UI belongs to P1.
- Live provider, PostgreSQL persistence, Logfire trace, and browser evidence for
  this integrated path remain pending final validation.

## Required final validation

```zsh
cd /workspaces/ai-engineering/estimador-cag

uv run ruff check --fix app tests
uv run ruff check app tests
uv run python -m py_compile $(find app tests -name '*.py' -type f)
uv run pytest -q
git diff --check
```

Then capture:

1. secret-scan evidence;
2. remote CI result for the final Plus commit;
3. legacy configuration smoke;
4. graph configuration smoke with PostgreSQL;
5. graph-unavailable `503` proof;
6. live provider and Logfire trace proof when explicitly enabled;
7. Streamlit browser proof for legacy and graph text-fallback behavior.

## Thirty-second explanation in Spanish

> Añadimos un puente de migración controlado para que la ruta conversacional
> pueda elegir entre el estimador legacy y el grafo mediante configuración.
> Legacy sigue siendo el valor por defecto y el rollback solo requiere cambiar
> una variable de entorno. El dispatcher selecciona exactamente un backend y no
> duplica cálculos. Como los contratos no son equivalentes, el modo graph no
> inventa fases legacy: devuelve texto compatible, declara paridad parcial y
> conserva todo el estado estructurado y la procedencia del grafo. La
> implementación está terminada; faltan las pruebas consolidadas, PostgreSQL,
> proveedor real, Logfire y smoke de UI.
