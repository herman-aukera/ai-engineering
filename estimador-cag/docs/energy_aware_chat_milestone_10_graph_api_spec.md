# EACHAT Milestone 10 — graph-backed API specification

## 1. Objective

Make the verified EACHAT LangGraph the active implementation behind additive deterministic and live API routes without silent legacy fallback, double execution, or public-contract breakage.

This milestone does not add persistence, human interrupts, UI redesign, live-provider quality claims, or deployment.

## 2. Requirements

### R1 — Stable identity

A graph request must resolve:

- `thread_id`;
- `request_id`;
- `trace_id`.

Caller-supplied IDs must be validated and bounded. Server-generated IDs must be opaque. Tests must inject a deterministic ID factory.

### R2 — One canonical execution

Each graph route invokes exactly one graph runtime.

It must not:

- execute the legacy agent and graph together;
- silently fall back to legacy after graph failure;
- retry a provider outside configured graph budgets;
- convert missing external evidence into project retrieval.

### R3 — Additive routes and rollback

Introduce additive routes first:

```text
POST /energy-chat/v2/chat
POST /energy-chat/v2/chat/live
```

Keep current routes unchanged as rollback surfaces until parity and browser evidence pass.

A configuration flag controls whether a later compatibility route may dispatch to the graph. The default remains explicit and testable; no per-request hidden fallback is allowed.

### R4 — Typed request and response

Define strict product-local contracts.

Request:

- current `EnergyAwareChatAgentRequest` fields;
- optional validated identity fields;
- explicit execution profile;
- optional human-gate mode declaration for future compatibility, without claiming HITL support.

Response:

- identity;
- graph status;
- source-need classification;
- final answer when present;
- Energy Card v2 when present;
- final disposition;
- evidence references;
- candidate and repair counts;
- provider metrics safe summary;
- ledger entry IDs;
- safe trace summary;
- limitations;
- explicit `awaiting_evidence` outcome.

Do not expose prompts, evidence bodies, hidden reasoning, credentials, or raw provider transcripts.

### R5 — Deterministic route

The deterministic route uses `DeterministicCandidateProvider` and remains CI-safe and keyless.

### R6 — Live route

The live route uses `BaselineCandidateProvider` through the existing DeepSeek/Kimi seam. It must be opt-in and remain monkeypatchable in CI. Real credentials are never required by normal tests.

### R7 — Compatibility and parity

Create an adapter that maps the authoritative graph state to the V2 response. Do not reconstruct authority from UI strings.

Parity tests must compare legacy and graph behavior only for the supported deterministic compatibility set:

- project evidence retrieval;
- candidate answer before optional repair;
- final disposition;
- final energy;
- final answer;
- evidence references.

Any deliberate difference must be documented, especially Energy Card v2 and complete disposition semantics.

### R8 — Failure behavior

Return typed safe errors for:

- invalid identity;
- unsupported mode/profile;
- provider budget failure;
- malformed provider result;
- missing external evidence;
- internal graph invariant failure.

No stack trace, secret, prompt, or raw provider body is returned.

## 3. Design

### 3.1 Proposed modules

```text
app/energy_chat/api_v2_contracts.py
app/energy_chat/graph_application.py
app/energy_chat/router.py
app/config.py
```

### 3.2 Application service

`run_graph_chat(request, *, provider, id_factory)` performs:

1. validate/resolve identity;
2. construct `EnergyChatGraphState`;
3. invoke `run_energy_chat_graph` once;
4. project authoritative state to the V2 response;
5. return typed response.

The router owns HTTP concerns only. Domain and graph decisions remain outside FastAPI.

### 3.3 Execution profiles

Start with two explicit profiles:

| Profile | Provider | CI | Purpose |
|---|---|---|---|
| `deterministic` | deterministic local | yes | parity and product contract |
| `live_bounded` | existing DeepSeek/Kimi seam | manual only | bounded provider integration |

Do not add profile complexity without measured need.

### 3.4 Pending evidence

When status is `awaiting_evidence`:

- HTTP request succeeds with a typed non-terminal product response;
- no candidate, decision ledger, Energy Card, or final answer is fabricated;
- response includes the source-need decision and next action;
- later checkpoint resume is deferred to Milestones 11–13.

## 4. Tasks

1. Add strict V2 request/response/error contracts.
2. Add deterministic ID factory interface and production UUID implementation.
3. Add graph application service.
4. Add deterministic V2 route.
5. Add live bounded V2 route with injected/monkeypatched provider.
6. Add feature flag/configuration and explicit rollback behavior.
7. Add parity, no-double-execution, awaiting-evidence, budget, and error tests.
8. Update OpenAPI-facing documentation and reviewer entry point.
9. Run focused and full deterministic gates.
10. Push and verify exact-head CI.
11. Do not switch existing `/chat` routes by default in this milestone.

## 5. Acceptance criteria

Milestone 10 is green only when:

- each route invokes one graph execution;
- deterministic CI makes zero external provider calls;
- live route is explicitly bounded and opt-in;
- no silent legacy fallback exists;
- stable IDs are returned;
- waiting for external evidence is represented without fabricated output;
- Energy Card v2 and ledger IDs come from authoritative graph state;
- legacy routes remain unchanged;
- parity tests pass for supported cases;
- malformed output and budget failures are safe;
- Ruff, compile, focused tests, full tests, diff check, and secret scan pass;
- remote CI is green.

## 6. Migration plan

Phase A:

- add `/energy-chat/v2/*` routes;
- preserve legacy routes;
- document explicit user choice.

Phase B after API and browser proof:

- allow a configuration-controlled compatibility dispatcher;
- default only after explicit release decision;
- never run both runtimes implicitly.

Phase C after persistence and HITL:

- expose checkpoint-aware resume actions;
- retain V1 rollback through a later green release boundary.

## 7. Rollback

Rollback must be one of:

- disable V2 route registration through configuration;
- revert the additive router/application commit;
- continue serving unchanged legacy routes.

No data rollback is required before persistence exists.

## 8. Threat model additions

| Threat | Control |
|---|---|
| attacker-controlled identity strings | strict format/length validation; opaque generated IDs |
| duplicate external provider calls | one application invocation; retained candidate IDs; no double execution |
| secret leakage in errors | typed safe errors and sanitized logging |
| raw prompt/provider transcript exposure | exclude from response and ledger |
| legacy fallback masks graph failure | fail explicitly; no silent fallback |
| project evidence used for current claim | preserve `awaiting_evidence` route |
| client trusts candidate rather than decision | response uses final projection and ledger authority |
| unsupported completion claim | response includes limitations and current claim boundary |

## 9. Test and evidence plan

### Unit

- identity resolution;
- state initialization;
- response projection;
- error sanitization;
- profile selection.

### Integration

- deterministic V2 route;
- external-evidence wait;
- refuse/reject/escalate projections;
- bounded repair;
- live route with fake provider;
- provider called exactly once;
- no legacy agent invocation;
- feature-flag rollback.

### Evidence levels

- contract and deterministic route: L2 after remote CI;
- browser/API user journey: L3 after manual smoke;
- live provider: L3 only after credentialed sanitized run;
- persistence: remains L0 until later milestones.

## 10. Claim boundary

Completing Milestone 10 permits:

> EACHAT exposes an additive graph-backed API with deterministic CI proof and a bounded live-provider integration path.

It does not permit claims of persistent orchestration, human-in-the-loop completeness, live provider quality improvement, public deployment, or production readiness.
