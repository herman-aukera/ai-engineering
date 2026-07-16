# Session 13 Plus evidence matrix

This comparison records what is implemented and separates deterministic proof
from promotion evidence that still requires external services.

| Teacher capability | Plus implementation and why stronger | Deterministic evidence | Runtime evidence | Remaining limitation |
| --- | --- | --- | --- | --- |
| Structure review | Durable LangGraph interrupt, typed edits, reject/regenerate, revision guard | `test_session13_plus_structure_review.py`, reviewed graph E2E | Control room loads in Chrome | PostgreSQL restart browser journey pending |
| Agent loop | Provider-neutral typed tools with iteration, call, time, cost and size budgets | `test_session13_plus_agent_tool_runtime.py` | None required for fake CI | DeepSeek/Kimi live comparison pending |
| Recovery | Only selected unresolved components; server owns evidence and Python owns hours | `test_session13_plus_selective_recovery.py` | None required for fake CI | Live retrieval/provider behavior is not claimed |
| Critic | Typed field-path findings with evidence refs and explicit repair scope | `test_session13_plus_review_policy.py` | Rendered by control room | Seeded precision is contract-level only |
| Boss | Deterministic retry/fallback/human/reject routing under explicit budgets | `test_session13_plus_review_policy.py` | Rendered by control room | No live fallback claim yet |
| Trace | Checkpointed domain events separated from spans and logs | graph observability and reviewed graph tests | Browser renders safe trace surfaces | External Logfire capture pending |
| Retrieval | Bounded `Send` workers, stable fan-in, failure isolation, sequential rollback | parallel retrieval tests and benchmark test | 8 components: 249.115 ms vs 67.022 ms, 3.717x | Local course-scale fake only |
| Persistence | PostgreSQL checkpointer and stable thread identity | persistence contract/integration tests | Not yet repeated in this promotion run | Docker engine currently unavailable |
| Rollout | Off/shadow/serve, explicit errors, no silent legacy fallback | rollout, dispatcher and bridge tests | Shadow dashboard exists | Production canary is not claimed |
| UI | One control room for reconnect, both gates, provenance, findings, decisions, history, scenarios and audit | control-room and deterministic demo API tests | Chrome/Brave launch and deterministic backend binding verified | Live-provider browser journey requires credentials |
| Evaluation | 19 adverse and happy scenarios with structured outcomes plus retrieval benchmark | `test_session13_plus_evaluation_matrix.py` | Benchmark recorded locally | Matrix is deterministic contract evidence |
| Auditability | Provenance, issue lifecycle, checkpoint history, scenario lineage and allow-listed export | audit and checkpoint scenario tests | JSON download exposed in UI | External archival/signing is out of scope |

Promotion remains gated on remote CI, real PostgreSQL restart/resume, full API
and browser journey, live-provider evidence when keys are available, and an
external telemetry capture. The PR must remain draft until those applicable
gates are recorded truthfully.
