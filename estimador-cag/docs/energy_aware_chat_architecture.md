# Energy Aware Chat architecture

Status: verified at `a207d7114d386c8009fe43d5d3a54dc274c71c15`, then updated by the graph-state milestone.

## Current runtime map

The existing deterministic `/energy-chat/chat` route calls a product-local linear function:

```text
request -> lexical project retrieval -> deterministic draft
        -> deterministic critics -> energy sum -> deterministic decision
        -> optional one-pass deterministic repair -> Energy Card
```

The live route substitutes a provider-backed draft through the existing DeepSeek/Kimi adapter seam. Normal CI does not make live calls.

`graph_runtime.py` now compiles the first real sequential LangGraph proof:

```text
START -> interpret_request -> load_policy_and_constraints
      -> determine_evidence_need
         -> skip_evidence ---------------------+
         -> retrieve_project_evidence ---------+-> generate_candidate
         -> await_external_evidence -> END         -> run_critic_panel
                                                    -> calculate_energy
                                                    -> decide_candidate -> END
```

This graph is not yet wired to the public API. It has no checkpointer, repair loop, or human interrupt lifecycle.

Domain truth remains in `app/energy_chat`: Pydantic transport contracts, policy penalties, critics, scorer, decider, repair functions, evidence classification, retrieval, and Energy Card projection. `graph_state.py` provides the versioned checkpoint-safe state contract. `graph_nodes.py` provides provider-free interpretation and policy/constraint nodes. `evidence_nodes.py` provides deterministic source-need classification plus skip, project-retrieval, and external-required routing. `candidate_provider.py` defines deterministic and baseline-backed candidate adapters with observable budgets and metrics; `candidate_node.py` retains immutable candidate/provider-call history and avoids duplicate calls on replay. `evaluation_nodes.py` binds the existing critic, scoring, and decision functions to the active candidate and records immutable panel, score, and outcome history. These remain independently testable typed deltas; none executes a graph or alters the current API runtime path.

## Verified requirement map

| Requirement | Current evidence | Classification |
|---|---|---|
| Deterministic critics, score, decision, repair | Existing evaluator and tests | verified |
| Project retrieval baseline | Deterministic committed-source retriever | verified |
| Versioned graph state and reducers | v1 contract, fixture, focused tests | verified |
| Interpretation and policy node contracts | Typed deltas, replay-safe application, policy parity tests | verified |
| Evidence classification and routing nodes | Existing classifier/retriever parity, attribution and replay tests | verified |
| Candidate provider abstraction | Local and baseline adapters, budgets, metrics, malformed output and replay tests | verified |
| Critic, score, and decision nodes | Candidate-linked records and exact evaluator parity tests | verified |
| Sequential LangGraph orchestration | Compiled graph, conditional routes, delta and parity tests | verified wiring proof |
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
8. Project retrieval cannot satisfy a current/external evidence requirement; that route waits for external evidence.
9. A retained candidate prevents a provider call from repeating during checkpoint replay.
10. Token, cost, latency, and retry budgets are deterministic gates over typed provider metrics.
11. Critics, scores, and decisions fail closed unless their records reference the active candidate and policy version.
12. LangGraph nodes return explicit field deltas; append-only runtime channels reuse domain reducer semantics.
13. An evaluated state routes directly from `START` to `END`, preventing replay from repeating work.

## Current claim boundary

Allowed: browser-testable, production-oriented MVP candidate with a deterministic project retrieval and evaluation path.

Blocked: production-ready, public deployment live, quality improvement over plain DeepSeek, frontier-model superiority, persistent LangGraph orchestration, and production telemetry.
