# Non-mandatory Session 13 Plus roadmap

## Scope

This roadmap preserves product and architecture work intentionally
excluded from the mandatory pre-session branch.

The teacher-facing `session-13/pre-work` branch remains the stable
mandatory checkpoint. Plus work continues on `gg-session-13/plus`.

## P0 — Existing-product integration bridge

Status: implementation complete; consolidated validation pending.

Implemented:

- configuration-controlled `legacy | graph` backend selector;
- `legacy` default and configuration-only rollback;
- async dispatcher with exactly-one-operation semantics;
- controlled integration of `POST /sessions/{session_id}/estimate`;
- unchanged `/api/v1/estimate`, `/api/v1/estimate/stream`, and
  `/api/v1/estimate/graph` paths;
- shared graph-run response validation;
- honest partial graph-to-product adaptation without fabricated legacy phases;
- explicit `503` for unavailable graph runtime;
- explicit `502` for graph execution failure;
- Session 06 stress-fake precedence;
- focused unit and route integration tests;
- `.env.example` and P0 implementation documentation.

The graph and legacy response contracts are not claimed to be identical. Graph
mode exposes a deterministic text fallback plus the complete validated graph
payload and explicit compatibility metadata.

See `docs/session13_plus_p0_bridge.md` for architecture, rollback, limitations,
and the final validation plan.

Promotion remains blocked until the final local gates, remote CI, PostgreSQL
smoke, trace evidence, live-provider smoke where required, and browser proof are
captured.

## P1 — Read-only Graph Inspector UI

Status: implementation complete; consolidated validation and browser proof
pending.

Implemented as the separate application `app/ui/graph_inspector.py`:

- safe execution header with estimation, thread, graph, status, provider, hours,
  cost, and count metadata;
- stable graph topology diagram;
- node timeline reconstructed from checkpointed domain events;
- deterministic component-to-source provenance explorer;
- structured issue view;
- explicit separation of domain trace, telemetry metadata, and checkpoint-safe
  payload;
- offline inspection of a saved graph response;
- optional idempotent reopen through an existing estimation UUID;
- deterministic pure-helper tests that require no provider, PostgreSQL, network,
  or browser.

The inspector does not expose hidden chain-of-thought and does not modify the
established Streamlit application. See
`docs/session13_plus_p1_graph_inspector.md` for the run command, contracts,
limitations, and browser-proof plan.

A future checkpoint-read API remains desirable for inspecting interrupted and
historical checkpoints without re-executing the graph.

## P2 — Reviewed subgraphs

Status: planned.

Separate the workflow into:

1. structure extraction and classification;
2. retrieval and estimation;
3. validation and recovery.

## P3 — Human review with `interrupt()`

Status: planned.

Support explicit modes:

- disabled;
- required;
- risk-based.

Add checkpoint-safe pause, approval, edit, reject, and resume behavior.

## P4 — Iterative provider tool runtimes

Status: planned.

Implement bounded DeepSeek and Kimi tool-call loops where the model
chooses a tool, Python validates it, the tool runs, the result is
returned with its tool-call identity, and the model observes the
result before the graph continues.

## P5 — Structured Critic

Status: planned.

Produce typed findings with issue code, severity, state path,
explanation, proposed repair, and supporting evidence.

## P6 — Deterministic Boss and policy router

Status: planned.

Bound and route retry count, provider fallback, latency budget, cost
budget, tool-call budget, and human escalation.

## P7 — Send API parallel retrieval benchmark

Status: planned.

- Measure the sequential baseline.
- Fan out one search per component using the LangGraph `Send` API.
- Use order-independent reducer semantics.
- Bound concurrency.
- Compare latency, cost, parity, and failure behavior.
- Retain the sequential path as a regression baseline.

## P8 — Full checkpoint and review wizard UI

Status: planned.

Add editable structure review, human approvals, conflict and no-data
states, checkpoint navigation, resume and recalculation controls,
provider profiles, trace links, and browser smoke evidence.

## P9 — Production smoke and provider matrix

Status: planned.

Compare deterministic fakes, DeepSeek, Kimi, and an optional reference
provider across success rate, latency, token use, cost, output parity,
retrieval quality, trace completeness, and recovery behavior.

## Promotion rule

No Plus item should replace the mandatory path until it has:

1. focused tests;
2. full deterministic regression;
3. persistence proof where applicable;
4. trace evidence;
5. rollback behavior;
6. remote CI;
7. an honest limitations statement.
