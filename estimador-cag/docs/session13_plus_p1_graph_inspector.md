# Session 13 Plus P1 — Read-only Graph Inspector

Status: implementation, consolidated validation, and browser evidence complete.

## Objective

Make the checkpointed estimation graph understandable without exposing hidden
chain-of-thought or destabilizing the established Streamlit product path.

The inspector is a separate application:

```zsh
cd /workspaces/ai-engineering/estimador-cag
uv run streamlit run app/ui/graph_inspector.py
```

It uses the existing additive graph endpoint:

```text
POST /api/v1/estimate/graph
```

The main `streamlit_app.py` and conversational session UI remain unchanged.

## Control-room capabilities

### Execution header

The header displays only safe product and execution facts:

- estimation ID;
- thread ID;
- graph version;
- terminal status;
- review-required state;
- provider, model, and prompt version when present;
- deterministic total hours and cost;
- requirement, component, and evidence counts.

### Graph topology and timeline

The inspector renders the mandatory sequential topology:

```text
START
  -> extract_requirements
  -> classify_components
  -> search_budgets
  -> generate_estimate
  -> validate_and_consolidate
  -> END
```

Checkpointed domain events are grouped by node and converted into a stable
timeline showing:

- observed versus not-observed nodes;
- event count;
- last event type and summary;
- state keys changed;
- evidence references.

This is domain-event inspection, not model chain-of-thought.

### Provenance explorer

Each component estimate is joined deterministically to retained historical
references. The view exposes:

- component ID and name;
- estimated hours;
- grounding status;
- confidence;
- derivation method;
- source range;
- retained budget IDs;
- source document IDs;
- source chunk IDs;
- review reasons.

### Trace separation

The UI has distinct views for:

1. domain trace events stored in graph state;
2. sanitized provider and execution metadata;
3. the complete checkpoint-safe HTTP payload.

Hosted telemetry remains in Logfire. Operational logs and hidden reasoning are
not merged into the domain trace.

### Offline inspection

A saved `GraphEstimationResponse` can be pasted into the inspector. This makes
review possible without re-executing providers or retrieval.

### Idempotent reopen

The execution form accepts an optional estimation UUID. Reusing the same ID with
the identical transcript exercises the existing completed-run idempotency path.

## Tests

`tests/test_session13_plus_graph_inspector.py` characterizes:

- strict request-payload construction;
- offline JSON parsing;
- execution-header extraction;
- stable graph ordering;
- observed and unobserved timeline states;
- deterministic provenance joins;
- graph-diagram generation.

The tests do not require PostgreSQL, providers, network access, or a browser.

## Current limitations

- The current public graph response represents the terminal execution. A future
  read-only checkpoint endpoint should expose interrupted and historical
  checkpoints without re-execution.
- Per-node wall-clock duration and checkpoint IDs are not present in the current
  domain response. Logfire remains the source for span timing.
- The inspector is read-only. Durable edit/approve/reject/resume behavior belongs
  to P3.
- Browser proof is captured as part of the deterministic Session 13 Plus UI
  journey; external provider and PostgreSQL gates remain purposefully separate.

## Required validation

```zsh
cd /workspaces/ai-engineering/estimador-cag

uv run ruff check app/ui/graph_inspector.py tests/test_session13_plus_graph_inspector.py
uv run python -m py_compile app/ui/graph_inspector.py tests/test_session13_plus_graph_inspector.py
uv run pytest -q tests/test_session13_plus_graph_inspector.py
```

Then run FastAPI and the inspector, execute a deterministic graph run, and
capture screenshots of:

1. execution header;
2. graph topology and timeline;
3. provenance explorer;
4. domain trace tab;
5. telemetry metadata tab;
6. checkpoint-safe payload tab.

## Thirty-second explanation in Spanish

> Construimos un Graph Inspector separado para hacer visible el grafo sin tocar
> la interfaz estable. Muestra identidad de ejecución, estado, topología,
> eventos por nodo, procedencia de cada estimación y metadatos seguros. Separa
> claramente la traza de dominio, la telemetría y el estado persistible, y nunca
> presenta chain-of-thought. También puede cargar una respuesta guardada sin
> volver a ejecutar proveedores. La implementación está terminada; faltan los
> gates consolidados y la evidencia de navegador.
