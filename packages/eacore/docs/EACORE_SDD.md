# EACORE — Shared Energy-Aware Core Software Design Document

**Document type:** Software Design Document (SDD) and extraction plan
**Product:** EACORE — Energy-Aware Core
**Repository incubation target:** `herman-aukera/ai-engineering`
**Recommended branch:** `EACORE`
**Recommended future repository:** `herman-aukera/eacore` or `herman-aukera/energy-aware-core`
**Distribution name:** `energy-aware-core`
**Python import name:** `eacore`
**Document version:** 1.0
**Audit date:** 2026-07-17
**Status:** Approved for a standalone-ready neutral-kernel pilot; broad product migration remains evidence-gated
**Evidence boundary:** This document defines the design and implementation sequence. It does not claim that the EACORE branch or package already exists.

---

## 1. Executive decision

EACORE should be created as a separate, LangGraph-neutral Python package that can be used by:

1. Session 13 Plus / Estimation Control Room V2;
2. EACHAT;
3. EACODE.

The package should provide common contracts and deterministic infrastructure for:

- versioned records;
- candidate identity;
- constraint observations;
- critic findings;
- evidence references;
- energy components and snapshots;
- neutral decision envelopes;
- repair references;
- safe trace events;
- canonical serialization;
- hashing and integrity;
- append-only decision records;
- compatibility and migration;
- retention classification;
- cross-product evaluation hooks.

EACORE must **not** own:

- product graph topology;
- LangGraph nodes or checkpoint configuration;
- FastAPI or Streamlit;
- provider prompts or provider SDK clients;
- retrieval implementations;
- project-estimation arithmetic;
- chat answer semantics;
- refusal policy;
- shell execution;
- repository mutation;
- command authorization;
- IDE, Aider, or Cline adapters;
- product-specific decision enums;
- product-specific policy weights;
- product UI.

### Extraction verdict

| Decision | Status |
|---|---|
| Create an `EACORE` incubator branch | **Approved** |
| Create a standalone-ready `eacore` package | **Approved** |
| Extract the current EACODE `energy_core` package wholesale | **Rejected** |
| Make all three products import EACORE immediately | **Rejected as premature** |
| Pilot neutral contracts behind adapters | **Approved** |
| Migrate one product at a time after compatibility proof | **Approved** |
| Move product scorers and decision policies into EACORE | **Rejected** |
| Extract to a dedicated repository after the neutral kernel is green | **Approved** |

---

## 2. Background and source-of-truth audit

### 2.1 Canonical Energy Core direction

The existing Energy-Aware Core specification defines the product-independent principle:

```text
Every answer, retrieval, patch, agent step, or decision must reduce
verified constraint energy or be rejected, repaired, clarified,
refused, or escalated.
```

It assigns shared responsibility for policy parsing, constraints, critic interfaces, scoring, evidence and decision records, repair contracts, reporting, and benchmark hooks. It also warns against premature extraction.

That direction remains valid, but the scope must now include Session 13 Plus as a third product and must distinguish:

```text
neutral reusable kernel
```

from:

```text
one universal product policy or runtime
```

### 2.2 Current branch state

At the time of this audit:

- `gg-session-13/plus` exists and contains the durable reviewed estimation product.
- `EACHAT` exists and contains a typed Energy-Aware Chat graph core.
- `EACODE` exists and contains a persistent deterministic coding judge and an `energy_core` package.
- No remote branch named `EACORE` was found.

### 2.3 Why the existing EACODE package cannot become EACORE unchanged

The existing EACODE `energy_core` package contains reusable ideas, but several contracts are coding-specific:

- `CandidateState` contains changed files, artifacts, validation claims, and scope claims.
- `EvidenceRecord` includes command, path, artifact hash, and exit code.
- The decision enum is limited to:
  - `accept`
  - `repair`
  - `reject`
  - `escalate`
- Its thresholds and constraint policy are shaped around the EACODE judge.

EACHAT requires additional chat dispositions such as clarification and refusal. Session 13 uses Boss actions such as retry-selected, fallback-provider, human-review, and reject. A direct rename or import would create invalid cross-product states.

### 2.4 Proven overlap

The three projects independently demonstrate enough overlap to justify a **neutral-kernel pilot**:

| Capability | Session 13 Plus | EACHAT | EACODE |
|---|---|---|---|
| Strict typed records | Yes | Yes | Yes |
| Stable candidate identity | Partial | Yes | Yes |
| Evidence references | Yes | Yes | Yes |
| Typed critic findings | Yes | Yes | Yes |
| Deterministic policy | Yes | Yes | Yes |
| Energy before/after/delta | Proposed | Yes | Yes |
| Append-only record behavior | Partial | Yes in state reducers | Yes in ledger |
| Human decisions | Yes | Planned | Yes for clarification/escalation |
| Trace events | Yes | Yes | Yes |
| Version metadata | Partial | Yes | Yes |
| Integrity/hashing | Limited | Limited | Yes |
| Retention/manifest | Missing | Missing | Yes |
| Framework-neutral domain layer | Partial | Strong | Strong |

The overlap is sufficient to define neutral contracts and test fixtures. It is not sufficient to move all domain policies into one package.

---

## 3. Product definition

EACORE is a deterministic, framework-neutral library for representing and validating energy-aware decisions.

It provides the common substrate:

```text
candidate reference
+ constraints and observations
+ critic findings
+ evidence references
+ energy snapshot
+ decision envelope
+ repair references
+ trace
+ integrity
+ ledger
```

Each product remains responsible for:

```text
interpreting its domain
→ producing domain candidates
→ evaluating domain-specific constraints
→ choosing product-specific decisions
→ rendering product-specific UI
→ executing product-specific actions
```

### 3.1 Product-independent loop

```text
Product candidate
→ product adapter
→ EACORE candidate/evidence references
→ product constraint evaluators
→ EACORE energy calculation
→ product decision policy
→ EACORE decision envelope and invariant validation
→ EACORE ledger/integrity
→ product-specific graph, API, UI, and action
```

### 3.2 Singular authority

EACORE owns:

- record shape and compatibility;
- canonical serialization;
- deterministic hashing;
- common energy arithmetic over supplied observations;
- universal transition invariants;
- append-only record integrity;
- neutral reporting envelopes.

The product owns:

- the meaning of the candidate;
- the constraint taxonomy;
- critic implementation;
- weights and thresholds;
- product decision code;
- human action semantics;
- execution;
- final user projection.

---

## 4. Goals

### G-001 — Reusable neutral contracts

Provide strict, versioned records that can represent common facts without importing any product.

### G-002 — Deterministic energy arithmetic

Calculate an energy snapshot from normalized constraint observations supplied by product evaluators.

### G-003 — Universal transition safety

Validate invariants shared by all three products:

- hard blockers cannot produce accepted outcomes;
- required evidence cannot be silently omitted;
- accepted transitions must improve energy or contain an explicit bounded setup-work justification;
- conflicting record reuse fails closed;
- repeated, non-improving candidates are detectable.

### G-004 — Evidence and decision integrity

Provide canonical JSON, SHA-256 hashing, append-only record checks, recovery reports, and retention classification.

### G-005 — Product independence

Allow Session 13, EACHAT, and EACODE to remain independently deployable and independently reversible.

### G-006 — Standalone extraction

Organize the package so it can be extracted to a dedicated repository without carrying coursework, product UI, graph runtime, or provider code.

---

## 5. Non-goals

EACORE will not:

- estimate project hours directly;
- generate chat answers;
- generate code or patches;
- run commands;
- authorize shell execution;
- retrieve documents;
- call providers;
- define LangGraph graphs;
- manage PostgreSQL, SQLite, or Redis;
- own human-review UI;
- define one universal product decision enum;
- own product-specific policies, thresholds, or weights;
- become a generic dictionary dumping ground.

---

## 6. Critical clarification: EACORE and project-hour calculation

Session 13 must continue to own authoritative project-estimation arithmetic:

- task low/expected/high hours;
- task-to-module aggregation;
- module-to-project aggregation;
- hourly rates and cost;
- allocation of component totals across tasks;
- estimate-specific range invariants.

EACORE can be used to **govern, validate, compare, and improve** those hour calculations.

### 6.1 Session 13 adapter responsibilities

The Session 13 adapter calculates or receives the domain estimate, then emits observations such as:

- `hour_range_valid`;
- `task_totals_reconcile`;
- `module_totals_reconcile`;
- `project_total_reconciles`;
- `required_scope_covered`;
- `mandatory_evidence_present`;
- `evidence_fresh`;
- `confidence_threshold_met`;
- `cost_budget_respected`;
- `latency_budget_respected`;
- `human_revision_current`.

EACORE then calculates constraint energy and verifies whether the new estimate is acceptable, repairable, blocked, or requires human authority.

### 6.2 Why this separation matters

Putting hour formulas in EACORE would make the core estimation-specific and useless to EACHAT and EACODE.

The correct reusable boundary is:

```text
Task 13 computes domain values.
EACORE evaluates constraint satisfaction and transition quality.
```

---

## 7. Architectural principles

### 7.1 Framework neutrality

The `eacore` runtime package must not import:

- LangGraph;
- FastAPI;
- Streamlit;
- OpenAI, Anthropic, LiteLLM, or provider SDKs;
- PostgreSQL, Redis, pgvector, or checkpointer packages;
- subprocess or shell-execution helpers;
- product packages.

### 7.2 Product adapters point inward

Allowed:

```text
Session 13 adapter → EACORE
EACHAT adapter     → EACORE
EACODE adapter     → EACORE
```

Forbidden:

```text
EACORE → Session 13
EACORE → EACHAT
EACORE → EACODE
EACHAT → EACODE
EACODE → EACHAT
```

### 7.3 Data contracts before runtime reuse

Extract stable records first. Extract algorithms only when semantics are independently proven equivalent.

### 7.4 Strict contracts

All persisted or cross-boundary models use strict validation:

```python
ConfigDict(extra="forbid")
```

Unknown fields fail unless a versioned compatibility reader explicitly handles them.

### 7.5 Product bodies remain outside the core

EACORE stores references and neutral facts, not arbitrary product payloads.

Use:

- `payload_ref`;
- `source_ref`;
- `affected_ref`;
- `artifact_ref`;

rather than an unbounded `dict[str, Any]`.

### 7.6 Append-only history

Identical replay is idempotent. Reusing the same identifier with different content fails closed.

### 7.7 No hidden reasoning

Traces and ledgers store concise, user-safe reasons and references. They never contain hidden chain-of-thought.

---

## 8. Proposed package structure

```text
packages/
  eacore/
    pyproject.toml
    README.md
    CHANGELOG.md
    LICENSE
    src/
      eacore/
        __init__.py
        py.typed

        contracts/
          __init__.py
          versions.py
          identity.py
          candidate.py
          constraints.py
          critics.py
          evidence.py
          energy.py
          decisions.py
          repairs.py
          traces.py
          retention.py
          ledger.py

        engine/
          __init__.py
          calculator.py
          transition.py
          canonical.py
          hashing.py
          integrity.py
          migration.py
          fingerprints.py

        ports/
          __init__.py
          constraint_evaluator.py
          decision_policy.py
          ledger_store.py
          clock.py

        adapters/
          __init__.py
          jsonl_ledger.py
          in_memory_ledger.py

        testing/
          __init__.py
          fixtures.py
          contract_suite.py

    tests/
      fixtures/
        session13/
        eachat/
        eacode/
      test_contracts.py
      test_energy_calculator.py
      test_transition_invariants.py
      test_canonical_hashing.py
      test_append_only_ledger.py
      test_migrations.py
      test_dependency_boundaries.py
      test_product_fixture_adapters.py

    docs/
      EACORE_SDD.md
      EXTRACTION_DECISIONS.md
      COMPATIBILITY_MATRIX.md
      MIGRATION_AND_ROLLBACK.md
      SECURITY_MODEL.md
      RELEASE_CHECKLIST.md

    specs/
      0001-neutral-kernel/
        requirements.md
        design.md
        tasks.md
        acceptance.md
        decisions.jsonl
        evidence.jsonl
```

### 8.1 Distribution

```text
Distribution: energy-aware-core
Import:       eacore
Version:      0.1.0
Python:       >=3.11,<3.14
```

### 8.2 Runtime dependencies

Initial runtime dependency:

```text
pydantic >=2.6,<3
```

Use the Python standard library for:

- JSON;
- hashing;
- paths;
- timestamps;
- protocols;
- JSONL reference storage.

No orchestration dependency is allowed in Phase 1.

---

## 9. Core contracts

### 9.1 VersionIdentity

```text
contract_name
contract_version
schema_version
```

Optional:

```text
policy_version
```

Rules:

- semantic version syntax;
- unsupported major versions fail explicitly;
- migrations never mutate source input;
- persisted records identify their contract.

### 9.2 RecordIdentity

```text
record_id
run_id
product
recorded_at
producer
```

`product` is a namespace such as:

```text
session13
eachat
eacode
```

### 9.3 CandidateRef

```text
candidate_id
candidate_version
candidate_kind
fingerprint
payload_ref
parent_candidate_id
```

The product owns the candidate body.

### 9.4 ConstraintRef

```text
constraint_id
constraint_class: hard | soft
policy_ref
description_ref
```

Product-specific constraint categories remain outside EACORE.

### 9.5 ConstraintObservation

```text
observation_id
constraint_id
status: pass | fail | missing | conflict | not_applicable
penalty
hard_blocking
affected_refs
evidence_refs
repair_ref
summary
```

Rules:

- penalty is non-negative;
- hard blockers are explicit;
- missing required evidence is not equivalent to pass;
- conflict remains distinguishable from fail.

### 9.6 CriticFindingEnvelope

```text
finding_id
critic_id
critic_version
constraint_id
severity
status
affected_refs
evidence_refs
repair_ref
summary
```

Core severity should remain a small reporting scale:

```text
info | minor | major | critical
```

Product adapters map their local severity explicitly. The core does not assign routing authority to critics.

### 9.7 EvidenceRef

```text
evidence_id
evidence_kind
source_ref
producer
recorded_at
content_hash
hash_algorithm
trust_classification
verification_status
sensitivity
redaction_status
fresh_until
```

Evidence bodies remain outside the core.

### 9.8 EnergyComponent

```text
component_id
constraint_id
penalty
hard_blocking
observation_refs
evidence_refs
```

### 9.9 EnergySnapshot

```text
energy_snapshot_id
candidate_id
policy_ref
energy_before
energy_after
energy_delta
hard_failure_refs
missing_evidence_refs
conflict_refs
components
setup_work
setup_work_justification
```

Sign convention:

```text
energy_delta = energy_after - energy_before
```

Therefore:

```text
negative delta = improvement
zero delta     = no measured improvement
positive delta = degradation
```

### 9.10 OutcomeClass

EACORE shall not replace product decision enums.

It may provide a neutral reporting class:

```text
accepted
change_required
blocked
human_required
in_progress
```

Examples:

| Product decision | Outcome class |
|---|---|
| EACHAT `accept` | `accepted` |
| EACHAT `repair` | `change_required` |
| EACHAT `clarify` | `human_required` |
| EACHAT `refuse` | `blocked` |
| EACODE `repair` | `change_required` |
| EACODE `escalate` | `human_required` |
| Session 13 `retry_selected` | `change_required` |
| Session 13 `fallback_provider` | `in_progress` |
| Session 13 `human_review` | `human_required` |
| Session 13 `reject` | `blocked` |

The product decision code remains mandatory and authoritative.

### 9.11 DecisionEnvelope

```text
decision_id
candidate_id
product_decision_code
outcome_class
policy_ref
energy_snapshot_ref
finding_refs
evidence_refs
repair_refs
human_decision_refs
reason_summary
limitations
```

### 9.12 RepairRef

```text
repair_id
source_candidate_id
target_candidate_id
repair_kind
instruction_ref
result:
  improved | no_improvement | budget_exhausted |
  not_repairable | human_required
energy_before_ref
energy_after_ref
```

### 9.13 TraceEventEnvelope

```text
event_id
trace_id
sequence
recorded_at
actor
phase
action
candidate_ref
evidence_refs
decision_ref
state_delta_refs
summary
```

Product-specific trace payloads remain outside EACORE.

### 9.14 RetentionClass

```text
release
audit
transient
sensitive_reference
```

Initial behavior is reporting only. Automated deletion is out of scope.

### 9.15 LedgerRecord

The ledger record wraps a `DecisionEnvelope` with:

```text
record identity
contract identity
canonical hash
previous_record_hash (optional experimental hash chain)
retention class
```

A full cryptographic authenticity system is out of scope for 0.1.0.

---

## 10. Ports

### 10.1 ConstraintEvaluator

Product-provided protocol:

```python
class ConstraintEvaluator(Protocol[CandidateT]):
    def evaluate(
        self,
        candidate: CandidateT,
        evidence: Sequence[EvidenceRef],
    ) -> Sequence[ConstraintObservation]: ...
```

EACORE never imports product candidate types.

### 10.2 DecisionPolicy

Product-provided protocol:

```python
class DecisionPolicy(Protocol):
    def decide(
        self,
        *,
        candidate: CandidateRef,
        energy: EnergySnapshot,
        findings: Sequence[CriticFindingEnvelope],
        evidence: Sequence[EvidenceRef],
    ) -> DecisionEnvelope: ...
```

### 10.3 LedgerStore

```python
class LedgerStore(Protocol):
    def append(self, record: LedgerRecord) -> None: ...
    def read_all(self) -> Sequence[LedgerRecord]: ...
```

Reference adapters:

- in-memory;
- append-only JSONL.

Products remain free to persist decisions in PostgreSQL or another backend.

### 10.4 Clock

Inject time for deterministic tests.

---

## 11. Deterministic engine

### 11.1 Energy calculation

The calculator:

1. validates observation identities;
2. rejects duplicate conflicting observations;
3. builds one component per evaluated constraint;
4. sums penalties;
5. separates hard blockers, missing evidence, and conflicts;
6. calculates before, after, and delta;
7. emits a strict `EnergySnapshot`.

It does not choose a product decision.

### 11.2 Transition verification

The transition verifier applies universal rules:

#### INV-001 — Hard constraint dominance

An `accepted` outcome is invalid when any hard blocker remains.

#### INV-002 — Evidence sufficiency

An `accepted` outcome is invalid when required evidence is missing or materially conflicting.

#### INV-003 — Improvement rule

An `accepted` outcome requires:

```text
energy_delta < 0
```

or:

```text
setup_work = true
+ bounded justification
+ no hard failure
+ product policy permits setup work
```

#### INV-004 — Repeated candidate detection

The same candidate fingerprint cannot be presented as a new repair result.

#### INV-005 — Non-improving repair

A repair with zero or positive energy delta must not be classified as improved.

#### INV-006 — Record identity

Identical replay is idempotent. Conflicting reuse of an ID fails closed.

#### INV-007 — No self-authorization

A producer cannot use its own candidate or tool output as proof that the action was authorized unless an independent policy record exists.

### 11.3 Canonical serialization

Canonical JSON:

- UTF-8;
- sorted keys;
- compact separators;
- explicit version fields;
- stable datetime format;
- no NaN or Infinity;
- no arbitrary object serialization.

### 11.4 Hashing

Use SHA-256 for:

- candidate fingerprints;
- record content hashes;
- artifact manifests.

Hashing proves integrity against a trusted reference. It does not prove authorship.

---

## 12. Product adapters

Adapters live in product repositories or product branches, not inside EACORE.

### 12.1 Session 13 Plus adapter

Recommended path:

```text
estimador-cag/app/integrations/eacore/estimation.py
```

Responsibilities:

- map estimation, structure, and human revisions to `CandidateRef`;
- map budget evidence to `EvidenceRef`;
- map Critic findings to `CriticFindingEnvelope`;
- emit estimate constraint observations;
- calculate an EACORE energy snapshot;
- map Boss decisions to `DecisionEnvelope`;
- append references to the existing audit packet;
- build the Estimate Energy Card.

Must not move:

- task/module/project hour arithmetic;
- V2 request/response schemas;
- LangGraph topology;
- PostgreSQL saver;
- human gate actions;
- provider profiles.

### 12.2 EACHAT adapter

Recommended path:

```text
estimador-cag/app/energy_chat/eacore_adapter.py
```

Responsibilities:

- map candidate versions and provider metrics;
- map critic panels;
- map local energy scores;
- map six chat dispositions to neutral outcome classes;
- map evidence references and repair results;
- generate EACORE-compatible ledger records;
- preserve Energy Card v2 as a chat-owned projection.

Must not move:

- chat modes;
- refusal semantics;
- answer text;
- source retrieval;
- prompts;
- chat UI;
- graph topology.

### 12.3 EACODE adapter

Recommended path:

```text
estimador-cag/energy_core/eacore_adapter.py
```

Responsibilities:

- adapt current EACODE candidates, violations, evidence, and decisions;
- preserve old JSONL readability;
- dual-serialize local and EACORE envelopes during migration;
- keep the current `energy_core` package as a compatibility facade;
- use EACORE canonical hashing and integrity where parity is proven.

Must not move:

- command policy;
- repository state;
- shell/tool adapters;
- execution authorization;
- rollback semantics;
- Aider/Cline integration;
- coding-specific decision details.

---

## 13. Extraction eligibility decisions

| Candidate | Decision for EACORE 0.1 | Reason |
|---|---|---|
| Contract/schema version | Extract now | Neutral and already needed by all products |
| Record identity | Extract now | Neutral audit primitive |
| Canonical JSON | Extract now | Deterministic and domain-independent |
| SHA-256 helpers | Extract now | Domain-independent integrity primitive |
| Candidate reference | Extract neutral reference only | Candidate bodies remain product-specific |
| Constraint reference | Extract neutral reference only | Taxonomies and evaluators remain local |
| Constraint observation | Pilot extraction | Common structure with explicit adapters |
| Critic finding | Extract envelope only | Categories and routing remain local |
| Evidence reference | Extract now | Strongest common contract |
| Evidence body | Keep product-specific | Privacy and payload semantics differ |
| Energy component | Pilot extraction | Reusable arithmetic input |
| Energy snapshot | Pilot extraction | Shared sign/invariant model, local weights |
| Product scorer | Keep product-specific | Semantics and weights differ |
| Product decision enum | Keep product-specific | Invalid universal states |
| Neutral outcome class | Extract now for reporting | Does not replace local decision |
| Decision envelope | Pilot extraction | Common audit envelope |
| Product decider | Keep product-specific | Authority and actions differ |
| Repair reference | Pilot extraction | Bodies and execution differ |
| Trace envelope | Extract now | Product payload remains referenced |
| Human gate mode/action | Duplicate temporarily | Operational semantics not yet equivalent |
| Retry/cost budget | Duplicate temporarily | Units and lifecycle differ |
| Provider metrics | Duplicate temporarily | Aggregation differs |
| Tool metrics | Keep product-specific | Chat, retrieval, and shell tools differ |
| Append-only ledger protocol | Extract interface now | Backend remains product-owned |
| In-memory/JSONL ledger | Reference adapters | Useful for core testing and small deployments |
| Hash-chain ledger | Experimental | Integrity, not authenticity |
| Retention classification | Extract now | Reporting-only common policy |
| Manifest | Extract generic artifact manifest | Product artifact selection remains local |
| LangGraph state/reducers | Keep product-specific | Framework and topology boundary |
| Checkpointer configuration | Keep product-specific | Runtime concern |
| UI cards | Keep product-specific | EACORE exposes data only |

---

## 14. Branch and repository strategy

### 14.1 Initial branch

Create:

```text
EACORE
```

from the current `main` branch.

Do not create it from `EACODE`, because that would inherit coding-product implementation and history as if they were neutral core.

### 14.2 Draft PR

Open a draft incubator PR:

```text
Title: incubator: EACORE neutral contracts and deterministic kernel
Base: main
Head: EACORE
```

The PR must state:

- do not merge as normal coursework;
- EACORE is a standalone-package incubator;
- no product migration is claimed;
- no LangGraph/runtime/provider/UI ownership;
- eventual extraction to a dedicated repository.

### 14.3 Standalone repository extraction

After EACORE 0.1 passes its own CI:

1. freeze the package path;
2. extract `packages/eacore` with preserved history;
3. create the standalone repository;
4. tag `v0.1.0`;
5. make product integrations consume a pinned tag or commit;
6. preserve a monorepo compatibility path during transition.

Recommended future dependency:

```toml
energy-aware-core = { git = ".../eacore.git", tag = "v0.1.0" }
```

Later, publish a package only after API stability and release governance are established.

---

## 15. Implementation phases

### Phase 0 — Audit and branch bootstrap

Deliver:

- current branch/PR/CI audit for all three products;
- current main SHA;
- `EACORE` branch;
- draft PR;
- canonical SDD;
- extraction decision table;
- compatibility matrix;
- package scaffold;
- standalone dependency boundary.

No product imports.

### Phase 1 — Neutral kernel 0.1

Implement:

- version identity;
- record identity;
- candidate reference;
- constraint reference and observation;
- critic envelope;
- evidence reference;
- energy component and snapshot;
- neutral outcome class;
- decision envelope;
- repair reference;
- trace envelope;
- retention class;
- canonical JSON;
- SHA-256 hashing;
- candidate fingerprinting;
- transition invariants;
- append-only ledger protocol;
- in-memory and JSONL reference stores;
- strict migrations;
- dependency-boundary tests.

### Phase 2 — Frozen compatibility fixtures

Capture sanitized fixtures from exact source SHAs:

- Session 13 estimate, evidence, Critic/Boss, human review, audit.
- EACHAT candidate, panel, score, decision, repair, trace.
- EACODE candidate, evidence, violation, decision, ledger.

Add product-to-core mapping tests without changing product branches.

### Phase 3 — First product pilot: Session 13 Plus

Recommended first pilot because it already has:

- durable checkpoints;
- two human gates;
- rich API/UI;
- browser proof;
- audit export;
- typed Critic/Boss decisions.

Implement additively:

- estimation adapter;
- energy snapshot;
- decision envelope;
- Estimate Energy Card;
- audit links;
- feature flag;
- parity tests;
- rollback.

Do not replace existing arithmetic or Boss policy.

### Phase 4 — EACHAT pilot

After its canonical Decision Ledger and Energy Card v2 exist:

- map candidate histories;
- map evidence;
- map energy and repairs;
- map six dispositions;
- dual-write ledger;
- prove graph behavior parity.

### Phase 5 — EACODE pilot

After controlled execution evidence is green:

- map current records;
- preserve historical JSONL;
- dual-write local and EACORE envelopes;
- adopt canonical integrity utilities;
- retain the local `energy_core` compatibility API.

### Phase 6 — Standalone repository

Extract and tag EACORE only after:

- EACORE CI is green;
- at least two adapters pass parity;
- old product fixtures remain readable;
- rollback has been exercised;
- no prohibited dependency is present.

---

## 16. Testing strategy

### 16.1 Core unit tests

- strict model validation;
- unknown fields;
- missing required fields;
- semantic version validation;
- canonical JSON stability;
- hash stability;
- candidate fingerprint stability;
- energy summation;
- hard blocker extraction;
- missing/conflicting evidence;
- sign convention;
- setup-work validation;
- repeated candidate detection;
- idempotent replay;
- conflicting ID rejection;
- JSONL append/read;
- corrupted record reporting;
- migration non-mutation;
- retention classification.

### 16.2 Contract fixture tests

For every product:

- local fixture round trip;
- adapter mapping;
- EACORE round trip;
- lossless reference preservation;
- decision-code preservation;
- evidence-reference preservation;
- trace order preservation;
- energy semantic preservation;
- old schema behavior.

### 16.3 Parity tests

The product must produce the same authoritative product decision before and after adopting EACORE.

EACORE may add:

- integrity metadata;
- neutral outcome class;
- energy snapshot;
- ledger envelope.

It must not silently alter product behavior.

### 16.4 Dependency-boundary tests

Fail when `eacore` imports:

- `langgraph`;
- `fastapi`;
- `streamlit`;
- provider SDKs;
- database/checkpointer packages;
- subprocess/shell helpers;
- product packages.

### 16.5 Security tests

- secret-like content excluded from references;
- evidence bodies not serialized accidentally;
- hidden reasoning fields rejected;
- malicious paths not followed by manifest utilities;
- path traversal rejected;
- corrupted ledger quarantined or reported;
- hash mismatch detected;
- unknown major version fails closed.

---

## 17. Evidence levels

| Level | Meaning |
|---|---|
| L0 | SDD or hypothesis only |
| L1 | deterministic local tests |
| L2 | remote deterministic CI |
| L3 | product adapter integration proof |
| L4 | two-product parity and rollback proof |
| L5 | standalone tagged package used by all three products |

Target progression:

```text
EACORE 0.1 package: L2
Session 13 adapter: L3
Second adapter: L4
All three pinned to standalone release: L5
```

---

## 18. Security and privacy

EACORE must:

- store references rather than sensitive bodies;
- support redaction status;
- validate hashes without exposing content;
- reject hidden-reasoning fields;
- avoid raw provider prompts/transcripts;
- avoid environment data;
- avoid command output;
- allow product-controlled retention;
- never perform execution.

The core is not a security boundary by itself. Product adapters must enforce domain security.

---

## 19. Migration and rollback

### 19.1 Additive sequence

1. Freeze local fixtures.
2. Add EACORE models.
3. Add product-local adapter.
4. Dual-serialize local and EACORE records.
5. Compare normalized semantics.
6. Keep local policy authoritative.
7. Run full product regression.
8. Record compatibility evidence.
9. Preserve a feature flag.
10. Remove duplication only after a later green checkpoint.

### 19.2 Rollback

Rollback must require only:

- disabling the adapter flag;
- removing the EACORE dependency or reverting one integration commit;
- continuing to read existing local records;
- leaving historical EACORE records inspectable.

Never rewrite historical product ledgers in place.

---

## 20. Release gates

### EACORE 0.1 gate

- [ ] `EACORE` branch exists from current main.
- [ ] Draft PR exists.
- [ ] Package is independently installable.
- [ ] Ruff passes.
- [ ] Python compilation passes.
- [ ] Full EACORE tests pass.
- [ ] Dependency-boundary test passes.
- [ ] Secret scan passes.
- [ ] Canonical fixtures are committed.
- [ ] SDD and migration docs are current.
- [ ] Remote CI is green.
- [ ] No product imports EACORE yet.

### First product-adapter gate

- [ ] Adapter is product-local.
- [ ] Existing product contract remains valid.
- [ ] Decision parity passes.
- [ ] Old fixtures remain readable.
- [ ] Dual-write output is deterministic.
- [ ] Feature flag rollback passes.
- [ ] Product full regression passes.
- [ ] Product remote CI passes.
- [ ] UI smoke passes when a UI projection is added.
- [ ] Claim boundary is updated.

### Standalone extraction gate

- [ ] At least two product adapters are L3 or stronger.
- [ ] Compatibility and rollback are proven.
- [ ] Package API is stable enough for `v0.1.0`.
- [ ] Standalone CI exists.
- [ ] Installation and migration guides exist.
- [ ] Pinned dependency strategy is tested.
- [ ] No product-specific code remains in the package.

---

## 21. Risks

| Risk | Mitigation |
|---|---|
| Renaming EACODE `energy_core` as shared core | Create new `eacore`; retain compatibility facade |
| Universal decision enum | Keep product code plus neutral outcome class |
| Generic untyped payloads | Store typed references, not arbitrary bodies |
| Shared policy weakens product semantics | Product policies stay local |
| Mega migration across three branches | Migrate one product at a time |
| Branch divergence | Extract standalone package early after L2 |
| Persisted records become unreadable | Freeze fixtures and add compatibility readers |
| Core imports runtime frameworks | Enforce dependency-boundary tests |
| EACORE starts calculating Task 13 hours | Keep hour arithmetic in estimation adapter |
| Integrity mistaken for authenticity | Document hash trust boundary |
| Premature 1.0 stability claim | Start at 0.1 and keep experimental labels |
| UI coupling | Core emits data; product renders it |

---

## 22. Next exact slice

### Spec 0001 — Neutral Kernel

Implement only:

```text
version identity
+ record identity
+ candidate reference
+ constraint observation
+ critic envelope
+ evidence reference
+ energy component/snapshot
+ neutral outcome class
+ decision envelope
+ trace envelope
+ canonical JSON/hash
+ transition invariants
+ append-only in-memory/JSONL reference ledger
+ dependency-boundary tests
```

Do not:

- migrate product branches;
- copy EACODE candidate models wholesale;
- add LangGraph;
- add FastAPI or UI;
- calculate project hours;
- call providers;
- execute commands;
- publish a package;
- merge the draft PR.

---

## 23. Acceptance criteria for Spec 0001

Spec 0001 is complete only when:

- package installs independently;
- all models are strict and versioned;
- canonical serialization is stable;
- hashes are deterministic;
- hard blockers prevent accepted outcomes;
- missing required evidence prevents accepted outcomes;
- positive or zero delta cannot be labeled improved;
- setup work requires an explicit bounded justification;
- repeated fingerprints are detected;
- identical record replay is idempotent;
- conflicting ID reuse fails closed;
- JSONL corruption produces an explicit recovery report;
- product fixtures map without losing identity or decision code;
- no prohibited dependency is imported;
- local and remote deterministic CI are green;
- SDD, decisions, tasks, acceptance, evidence, and PR metadata are current.

---

## 24. Claim boundary

After Spec 0001:

> EACORE is a CI-validated, framework-neutral 0.1 kernel containing versioned energy-aware contracts, deterministic energy and transition invariants, canonical integrity utilities, and reference ledger adapters. It has not yet replaced any product-local policy or runtime.

Blocked claims:

- all three products use EACORE;
- EACORE calculates project estimates;
- EACORE is production-ready;
- EACORE policies are universally equivalent;
- EACORE provides secure execution;
- EACORE is a stable 1.0 API.

---

## 25. Final SDD verdict

The original shared-core idea is now mature enough to justify a **carefully bounded EACORE package**, but not a broad code merge.

The correct implementation is:

```text
new neutral package
→ frozen cross-product fixtures
→ product-local adapters
→ one product pilot
→ second product pilot
→ standalone repository
→ third product migration
```

The incorrect implementation is:

```text
rename EACODE energy_core
→ import it everywhere
→ force one scorer, decision enum, graph, or policy
```

**Decider verdict:** Approve EACORE Spec 0001 neutral-kernel implementation on a new `EACORE` incubator branch. Keep all product policies, graphs, arithmetic, tools, providers, persistence backends, and UIs product-specific.
