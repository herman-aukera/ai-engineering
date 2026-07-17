# Energy Aware Chat architecture

Status: verified at `a207d7114d386c8009fe43d5d3a54dc274c71c15`, then updated by the graph-state milestone.

## Current runtime map

The deterministic `/energy-chat/chat` route calls a product-local linear function:

```text
request -> lexical project retrieval -> deterministic draft
        -> deterministic critics -> energy sum -> deterministic decision
        -> optional one-pass deterministic repair -> Energy Card
```

The live route substitutes a provider-backed draft through the existing DeepSeek/Kimi adapter seam. Normal CI does not make live calls. The current runtime is not a LangGraph graph and has no checkpoint/resume lifecycle.

Domain truth remains in `app/energy_chat`: Pydantic transport contracts, policy penalties, critics, scorer, decider, repair functions, evidence classification, retrieval, and Energy Card projection. `graph_state.py` provides the versioned checkpoint-safe state contract. `graph_nodes.py` now provides provider-free interpretation and policy/constraint nodes as independently testable typed deltas. Neither module executes a graph or alters the current API runtime path.

## Verified requirement map

| Requirement | Current evidence | Classification |
|---|---|---|
| Deterministic critics, score, decision, repair | Existing evaluator and tests | verified |
| Project retrieval baseline | Deterministic committed-source retriever | verified |
| Versioned graph state and reducers | v1 contract, fixture, focused tests | verified |
| Interpretation and policy node contracts | Typed deltas, replay-safe application, policy parity tests | verified |
| LangGraph orchestration | No dependency or graph builder | missing |
| Checkpoint resume and human gates | No runtime implementation | missing |
| `refuse` and `escalate` dispositions | State vocabulary only; current decider has four outcomes | missing at runtime |
| Typed domain trace and decision ledger | Typed trace-event state exists; no ledger writer | partial |
| Retry, cost, token, latency budgets | Provider metadata exists in older contracts; no graph budget enforcement | missing |
| Persistent evidence/ledger redaction and retention | No product-local persistence policy enforcement | missing |
| Browser smoke, live benchmark, deployment telemetry | Claim gate remains blocked | missing evidence |

## Architectural invariants

1. Models may propose candidates and observations; deterministic Python owns energy, evidence sufficiency, and disposition.
2. LangGraph may orchestrate transitions but must not own domain truth.
3. Append-only records use immutable IDs. Identical retry is a no-op; conflicting ID reuse fails.
4. Singular authoritative values replace: active candidate, final answer, status, policy version, and Energy Card are not reducers.
5. Hidden chain-of-thought and sensitive evidence bodies are not checkpoint fields.
6. The existing API remains unchanged until parity tests demonstrate graph behavior.
7. Node trace events persist safe counts and versions, not user request or constraint text.

## Current claim boundary

Allowed: browser-testable, production-oriented MVP candidate with a deterministic project retrieval and evaluation path.

Blocked: production-ready, public deployment live, quality improvement over plain DeepSeek, frontier-model superiority, persistent LangGraph orchestration, and production telemetry.
