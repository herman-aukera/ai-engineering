# Non-mandatory Session 13 Plus roadmap

## Scope

This roadmap preserves product and architecture work intentionally
excluded from the mandatory pre-session branch.

The teacher-facing `session-13/pre-work` branch remains the stable
mandatory checkpoint. Plus work continues on `gg-session-13/plus`.

## P0 — Existing-product integration bridge

Status: implementation and consolidated deterministic validation complete.

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

Full local gates, remote CI, PostgreSQL restart, trace, deterministic browser,
benchmark evidence, and a credentialed DeepSeek/Kimi plus Logfire export smoke
are captured. See `docs/session13_plus_live_runtime_evidence.md`.

## P1 — Read-only Graph Inspector UI

Status: implementation, consolidated validation, and browser proof complete.

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

Status: implementation and consolidated runtime evidence complete.

Separate the workflow into:

1. structure extraction and classification;
2. retrieval and estimation;
3. validation and recovery.

## P3 — Human review with `interrupt()`

Status: implementation, PostgreSQL process-restart proof, and deterministic
browser proof complete.

Support explicit modes:

- disabled;
- required;
- risk-based.

Add checkpoint-safe pause, approval, edit, reject, and resume behavior.

Implemented:

- structure gate with approve, edit, reject and regenerate;
- distinct post-Critic/Boss final estimate gate;
- approve, reject, selective-recovery request and typed human override;
- actor, reason, revision, evidence refs and old/new field audit records;
- stale revision protection and same-thread resume API;
- integrated control-room forms for both durable gates.

See `docs/session13_plus_final_estimate_gate.md`.

## P4 — Iterative provider tool runtimes

Status: implementation and bounded DeepSeek/Kimi live-turn evidence complete.

Implement bounded DeepSeek and Kimi tool-call loops where the model
chooses a tool, Python validates it, the tool runs, the result is
returned with its tool-call identity, and the model observes the
result before the graph continues.

## P5 — Structured Critic

Status: implementation complete.

Produce typed findings with issue code, severity, state path,
explanation, proposed repair, and supporting evidence.

## P6 — Deterministic Boss and policy router

Status: implementation complete.

Bound and route retry count, provider fallback, latency budget, cost
budget, tool-call budget, and human escalation.

## P7 — Send API parallel retrieval benchmark

Status: implementation, consolidated validation, and course-scale benchmark
evidence complete. Production-scale performance is explicitly not claimed.

Implemented:

- sequential baseline retained unchanged and used as configuration rollback;
- one LangGraph 1.2.9 `Send` packet per validated component;
- explicit semaphore concurrency bound;
- replay-idempotent result-envelope reducer;
- canonical fan-in ordering and stable provenance deduplication;
- sibling result preservation for missing, invalid, and failed workers;
- sanitized dispatch, worker, and merge domain events and spans;
- deterministic sequential/parallel estimate and provenance parity tests;
- reproducible local benchmark with measured latency and honest scope limits.

See `docs/session13_plus_p7_parallel_retrieval.md`.

## P8 — Full checkpoint and review wizard UI

Status: implementation and deterministic end-to-end browser proof complete.

Checkpoint history and scenario branching foundation implemented:

- newest-first persisted checkpoint listing and exact checkpoint inspection;
- non-destructive branching into a new thread with explicit lineage;
- deterministic comparison of hours, evidence, findings, cost and latency;
- control-room history, branch and comparison controls;
- no destructive canonical rollback.

See `docs/session13_plus_checkpoint_scenarios.md`.

The control room also exports an allow-listed JSON audit packet with final
estimate, provenance, unresolved issues, Critic/Boss/human decisions, lineage,
sanitized execution metadata, domain trace, and explicit limitations. See
`docs/session13_plus_audit_export.md`.

Add editable structure review, human approvals, conflict and no-data
states, checkpoint navigation, resume and recalculation controls,
provider profiles, trace links, and browser smoke evidence.

## P9 — Production smoke and provider matrix

Status: deterministic scenario matrix and bounded credentialed DeepSeek/Kimi
plus Logfire export evidence complete. A production-scale provider matrix is
not claimed.

Compare deterministic fakes, DeepSeek, Kimi, and an optional reference
provider across success rate, latency, token use, cost, output parity,
retrieval quality, trace completeness, and recovery behavior.

See `docs/session13_plus_evaluation_matrix.md` for the 19-scenario keyless
contract matrix and its explicit evidence limits.

## Promotion rule

No Plus item should replace the mandatory path until it has:

1. focused tests;
2. full deterministic regression;
3. persistence proof where applicable;
4. trace evidence;
5. rollback behavior;
6. remote CI;
7. an honest limitations statement.
