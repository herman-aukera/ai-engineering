# Non-mandatory Session 13 Plus roadmap

## Scope

This roadmap preserves product and architecture work intentionally
excluded from the mandatory pre-session branch.

Every item below is **planned**, not claimed as implemented.

The teacher-facing `session-13/pre-work` branch remains the stable
mandatory checkpoint. Plus work should continue from a separate branch
such as `gg-session-13/plus`.

## P0 — Existing-product integration bridge

Status: planned.

- Prove parity between legacy and graph response contracts.
- Add a configuration-controlled backend selector.
- Route one controlled product path through the graph service.
- Preserve rollback to the legacy implementation.
- Avoid duplicate estimation logic.

## P1 — Read-only graph-aware UI

Status: planned.

Expose:

- estimation and thread identifiers;
- graph status;
- extracted requirements;
- classified components;
- retrieved provenance;
- component estimates;
- node timeline;
- domain trace events;
- checkpoint metadata;
- validated versus review-required state.

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
