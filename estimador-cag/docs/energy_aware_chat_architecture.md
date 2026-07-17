# Energy Aware Chat architecture

## Status

Milestone 9 code checkpoint: `dd79bf4befd625ce673242e843c14a023c0862d6`.

Remote CI run `29608614284` passed with 519 tests.

## Current public runtime

The existing deterministic `/energy-chat/chat` route still calls the legacy product-local linear function:

```text
request -> lexical project retrieval -> deterministic draft
        -> deterministic critics -> energy sum -> deterministic decision
        -> optional one-pass deterministic repair -> compact Energy Card
```

The live route substitutes a provider-backed draft through the existing DeepSeek/Kimi adapter seam. Normal CI does not make live calls.

These routes remain compatibility and rollback surfaces. They are not yet backed by the new graph.

## Current internal graph

`graph_runtime.py` compiles the canonical internal LangGraph:

```text
START -> interpret_request -> load_policy_and_constraints
      -> determine_evidence_need
         -> skip_evidence ---------------------+
         -> retrieve_project_evidence ---------+-> generate_candidate
         -> await_external_evidence -> END         -> run_critic_panel
                                                    -> calculate_energy
                                                    -> decide_candidate
                                                       -> plan_repair
                                                          -> apply_repair
                                                          -> full reevaluation
                                                          -> finalize_repair
                                                       -> record_decision
                                                       -> build_final_projection
                                                       -> END
```

Terminal authoritative decisions pass through:

```text
record_decision
→ append-only Decision Ledger
→ Energy Card v2
→ safe final-answer projection
```

The repair branch is bounded by typed retry and cumulative cost budgets. It creates candidate version 2, fully reevaluates it, records improvement/no-improvement/budget exhaustion, and stops.

The graph is not yet wired to the public API and has no checkpointer or human interrupt lifecycle.

## Component ownership

| Component | Ownership |
|---|---|
| `contracts.py`, policies, critics, scorer and decider | deterministic chat domain truth |
| `graph_state.py` | versioned product-local state and replay-safe reducers |
| `graph_nodes.py` | interpretation and policy/constraint deltas |
| `evidence_nodes.py` | deterministic source-need and evidence routes |
| `candidate_provider.py`, `candidate_node.py` | provider boundary, budgets, immutable candidate history |
| `evaluation_nodes.py` | candidate-linked critics, scores and decisions |
| `repair_nodes.py` | bounded repair requests, candidate v2 and results |
| `audit_models.py` | ledger, evidence-integrity and Energy Card v2 contracts |
| `finalization_nodes.py` | ledger writer and user-safe projection |
| `graph_runtime.py` | LangGraph-only orchestration and conditional routes |

Domain policy remains independently testable outside LangGraph, FastAPI, and UI.

## Verified requirement map

| Requirement | Current evidence | Classification |
|---|---|---|
| Deterministic critics, score, decision and repair | evaluator and graph tests | verified L2 |
| Project retrieval baseline | deterministic committed-source retriever | verified L2 |
| Versioned graph state and reducers | v1 contract, fixture and focused tests | verified L2 |
| Interpretation, policy and evidence nodes | typed deltas and replay tests | verified L2 |
| Candidate provider abstraction | local/live adapters, budgets and replay protection | verified L2 deterministic |
| Sequential LangGraph orchestration | compiled graph and conditional routes | verified L2 wiring |
| Bounded graph repair | candidate v2, reevaluation and termination | verified L2 |
| Six disposition semantics | deterministic rules and transition tests | verified L2 |
| Append-only Decision Ledger | exact candidate/panel/score/decision links; conflict tests | verified L2 |
| Evidence reference integrity | SHA-256 reference hashes; body excluded | verified L2 |
| Energy Card v2 and final projection | graph finalization tests | verified L2 |
| Graph-backed API | specification only | missing implementation |
| Checkpoint resume and human gates | no runtime implementation | missing |
| PostgreSQL migration/retention | no product-local implementation | missing |
| Browser, live graph provider and benchmark evidence | claim gates remain blocked | missing evidence |

## Architectural invariants

1. Models may propose candidates and observations; deterministic Python owns energy, evidence sufficiency and disposition.
2. LangGraph orchestrates transitions but does not own domain truth.
3. Append-only records use immutable IDs. Identical retry is a no-op; conflicting ID reuse fails.
4. Singular authoritative values replace: active candidate, final answer, status, policy version and Energy Cards are not reducers.
5. Hidden chain-of-thought, credentials, prompts and sensitive evidence bodies are not audit fields.
6. Project retrieval cannot satisfy a current/external evidence requirement.
7. A retained candidate prevents a provider call from repeating during replay.
8. Provider output always passes critics, score, decision, ledger and projection.
9. Repair consumes an explicit retry and always reruns critics, score and decision.
10. Equal or higher post-repair energy terminates as `no_improvement`; exhausted repair budget terminates explicitly.
11. Request refusal is distinct from candidate rejection; human-authority and exhausted-budget cases escalate.
12. Unsafe rejected candidate text is not emitted as the final answer.
13. `reference_hash` covers the evidence reference string only; it is not a body-content claim.
14. Public API migration must not silently execute legacy and graph runtimes together.

## Current claim boundary

Allowed:

> EACHAT has a CI-validated deterministic LangGraph core with typed state, evidence routing, provider budgets, bounded repair, six dispositions, an append-only Decision Ledger, Energy Card v2, and safe final-answer projection.

Blocked:

- graph-backed public API;
- persistent LangGraph orchestration;
- human interrupt/resume;
- public deployment;
- quality improvement over plain DeepSeek;
- production readiness and telemetry.
