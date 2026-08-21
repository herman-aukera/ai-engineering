# Energy-Aware Protocol V1

**Status:** portfolio convergence contract  
**Version:** `energy-aware.protocol.v1`  
**Products:** Energy-Aware Estimator, EACHAT, EACODE

This protocol defines the neutral vocabulary shared by the three Energy-Aware products. It does **not** prescribe one graph, one policy, one UI, or one domain model. Product semantics remain authoritative inside each product.

## Core decision loop

```text
INGEST
-> UNDERSTAND
-> GATHER_EVIDENCE
-> PROPOSE
-> CRITIQUE
-> SCORE
-> DECIDE
-> REPAIR when justified
-> AUTHORIZE when protected
-> EXECUTE when the product owns execution
-> VERIFY
-> RECORD
```

A product may omit stages that are not semantically applicable, but it must not silently move authority from deterministic policy or an authorized human to an LLM/provider/tool.

## Neutral concepts

| Concept | Contract |
| --- | --- |
| `RequestContext` | Stable request/thread/tenant context and contract versions. |
| `TraceContext` | Safe correlation identifiers; never hidden reasoning. |
| `EvidenceRef` | Stable reference to evidence without requiring raw private body disclosure. |
| `EvidenceMetadata` | Provenance, integrity, freshness and permission metadata. |
| `CandidateRef` | Stable identity for an estimate, answer, patch or other proposal. |
| `CriticFinding` | Typed finding with owner, reason code, severity/disposition and evidence refs. |
| `ConstraintViolation` | Deterministic hard/soft constraint failure. Hard violations cannot be waived by a model. |
| `EnergyScore` | Deterministically computed policy score or equivalent bounded decision signal. |
| `Disposition` | One of `accept`, `repair`, `clarify`, `reject`, `escalate` where semantically applicable. |
| `RepairInstruction` | Bounded, explicit instruction producing a new candidate revision. |
| `HumanActionRequest` | Protected action request bound to expected state/revision and actor authority. |
| `DecisionRecord` | Immutable/safely persistent projection of inputs, evidence, findings, policy version and final disposition. |
| `ExecutionEvidence` | What actually executed, not what a provider/model planned or claimed. |
| `ProviderEvidence` | Requested, planned and served provider identities kept distinct. |
| `Budget` | Explicit cost/latency/retry/hop/resource bound owned by deterministic code. |
| `ReasonCode` | Stable machine-readable explanation token; prose is secondary. |
| `PolicyVersion` | Version of deterministic policy that produced the decision. |
| `ContractVersion` | Version of the externally meaningful schema/behavior contract. |

## Authority invariants

1. Models, providers and tools may propose, classify, retrieve, transform or return evidence.
2. Models, providers and tools may **not** authorize themselves, waive hard constraints, create process authority, or mutate authoritative state outside explicit product policy.
3. Deterministic code owns arithmetic, hard constraints, budgets, idempotency, replay protection, privilege checks and final machine disposition.
4. Human authority is explicit, typed, revision/scope bound and replay safe when a protected transition requires it.
5. `planned` provider/tool behavior is never evidence that it was `served` or executed.
6. Repair creates a new explicit candidate/effective revision and is reevaluated.
7. Final evidence is recordable without exposing secrets, hidden chain of thought or unrestricted raw private content.

## Identity and integrity

Stable IDs should be deterministic or server-generated according to product semantics. Reuse of the same semantic ID with conflicting content must fail closed. Where durable integrity matters, canonical JSON plus SHA-256 or an equivalent deterministic fingerprint is preferred.

Suggested reason-code format:

```text
<domain>_<condition>[_<outcome>]
```

Examples: `provider_execution_missing`, `cost_budget_exceeded`, `stale_human_action`, `receipt_already_consumed`.

## Serialization and compatibility

- External schemas are explicitly major-versioned.
- Additive optional fields are preferred inside one major version.
- Removing/renaming required fields or changing semantics requires a new major contract or an explicit migration/compatibility layer.
- Canonical records must avoid timestamps/random identifiers in equality comparisons unless those fields are intentionally part of identity.
- Persisted records carry enough schema/policy version information to support replay and migration decisions.

## Product mappings

### Energy-Aware Estimator (`main`)

`CandidateRef` = estimate candidate/proposal. `CRITIQUE` includes reliability, review policy and coherence. `DECIDE` is owned by deterministic supervisor/Boss policy. `REPAIR` is selective recovery. `AUTHORIZE` is persistent human review. Authoritative graph/HITL state lives in PostgreSQL.

### EACHAT

`CandidateRef` = answer candidate. `GATHER_EVIDENCE` includes source need, project evidence and citation validation. `CRITIQUE` is the critic panel. `SCORE` is Energy calculation. `REPAIR` is bounded answer repair. `AUTHORIZE` is durable human interrupt/resume. Decision Ledger and Energy Card are product projections of `DecisionRecord`.

### EACODE

`CandidateRef` = coding proposal/effective proposal. `GATHER_EVIDENCE` includes repository/provider/tool evidence. Deterministic critics and Boss own disposition. `AUTHORIZE` uses signed actor authority plus exact-scope one-use receipts. `EXECUTE` remains simulated unless a separately proven sandboxed runner is explicitly enabled. Production authority records live in PostgreSQL.

## Extraction rule

This document is the shared contract before it is shared code. A concept may move into a neutral EACORE package only when at least two products implement genuinely identical semantics, the remaining product can conform or declare N/A, conformance tests prove equivalence, and dependency direction remains `product -> eacore` with no FastAPI/LangGraph/provider/product leakage into the core.

The archived EACORE branch is research input, not automatically authoritative implementation.
