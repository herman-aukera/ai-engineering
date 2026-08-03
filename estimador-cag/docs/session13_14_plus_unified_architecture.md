# Session 13 + 14 Plus — Unified Architecture

## Status

```text
Working mode: LIDR coursework continuity + semantic consolidation
Writable branch: gg-session-14/plus-consolidated
Draft PR: #21
Session 13 Plus source: f87605cb8a8ee5ff2606c51e5490b6beb2ca7f7a
Session 14 Plus source: 34011bcd9442130e09ab776d9072c0d53a2d93c2
Common ancestor: d9caf76d013d18cf6235f29d21f7a73f8133bce8
Controlled ancestry merge: 6e0289cb1006fd3980fd59ceaf37e78f6a77bb5a
```

The source branches remain unchanged. The consolidated branch contains the complete Session 13 Plus ancestry and the Session 14 Plus implementation, followed by explicit semantic reconciliation.

## Objective

Provide one canonical, versioned orchestration path that combines:

- Session 13 Plus reviewed lifecycle, structure review, parallel retrieval, recovery, Critic/Boss policy, provider readiness, scenario/audit foundations, API and Control Room patterns;
- Session 14 manual supervision, typed `Command` routing, least privilege, persistent `interrupt()`, same-thread human review, action auditing;
- Session 14 Plus capability authorization, compact context integrity, candidate competition, V3 constraint Energy and PostgreSQL lifecycle proof.

The consolidation is additive. Existing mandatory, reviewed and supervised graphs remain available as rollback paths.

## Canonical graph

```text
START
→ policy_bootstrap
→ supervisor
→ structure_phase
   → reformulate_request
   → semantic_classify
   → extract_requirements
   → classify_components
   → structure_review_gate when configured
→ supervisor
→ estimation_phase
   → bounded parallel retrieval or sequential rollback
   → deterministic estimate generation
   → validation
   → selective recovery when justified
→ supervisor
→ candidate_competition
   ├─ baseline
   ├─ aggressive
   ├─ conservative
   └─ deterministic synthesis
→ supervisor
→ reliability_analyst
→ supervisor
→ review_policy_phase
   → typed Critic
   → deterministic Boss recommendation
→ supervisor
→ boss_action
→ supervisor
→ bounded recovery_phase when recommended and budget remains
→ supervisor
→ coherence_validator
→ supervisor
→ persistent human_review_gate when policy requires authority
→ proposal
→ supervisor
→ finalize
→ END
```

Graph identity:

```text
session13_14_plus_unified_graph
session13_14_plus.unified.v1
```

## Authority model

There is one orchestration authority:

```text
Critics recommend.
Boss policy recommends a bounded action.
The deterministic unified supervisor owns graph routing.
Python owns arithmetic, constraints, Energy, privileges and budgets.
Only the persisted human gate can approve, adjust or reject.
```

This prevents the Session 13 Boss and Session 14 supervisor from becoming competing orchestrators.

### Structure authority

The structure review contract may approve, edit, reject or request regeneration of requirements/components. It cannot approve the final estimate.

### Safety and final authority

The Session 14 `interrupt()` gate owns final approve/adjust/reject decisions with:

- expected revision;
- idempotency key;
- actor;
- reason;
- typed adjustments;
- same-thread continuation;
- PostgreSQL persistence.

## Reused Session 13 Plus components

The unified graph composes rather than copies:

- `build_structure_subgraph`;
- `build_estimation_subgraph`;
- `build_review_policy_subgraph`;
- `build_final_recovery_subgraph`;
- semantic classification and V3 complexity;
- bounded parallel retrieval and sequential rollback;
- reliability analyst;
- typed Critic and Boss policy;
- selective recovery;
- proposal projection;
- provider-readiness benchmark contracts;
- reviewed API and Control Room rollback path.

## Reused Session 14 Plus components

- replay-safe supervised state and reducers;
- least-privilege specialist audit;
- persistent Session 14 human gate;
- context-aware post-resume refresh;
- strict capability registry;
- compacted context fingerprint and freshness semantics;
- four-candidate competition;
- V3 constraint-Energy snapshot;
- PostgreSQL lifecycle tooling.

## Provider policy

A model is not enabled because configuration or documentation names it.

The unified runtime loads a sanitized immutable `BenchmarkSnapshot` produced by Session 13 Plus production CI and converts only passing routes into enabled capabilities.

Enablement gate:

```text
status = benchmark_calibrated
sample_count > 0
failure_count = 0
schema_pass_rate >= 0.95
tool_pass_rate >= 0.95
exact provider/model identifier has capability metadata
```

Primary and fallback routes are both checked for:

- enabled lifecycle;
- exact model identity;
- supported effort;
- output-token ceiling;
- tool support;
- stage identity.

The unified policy uses the verified Moonshot identifier `kimi-k3`; it does not alias the older `kimi-k2.6` documentation route.

## Context integrity

Compact context is a derived control-plane projection. It is never source of truth.

Authoritative records remain:

- PostgreSQL checkpoints;
- evidence references;
- route ledgers;
- Critic findings;
- Boss decisions;
- immutable competition candidates;
- Energy snapshots;
- human actions;
- proposal and validation state.

The context projection preserves identity, objective, constraints, accepted/rejected decisions, evidence references, budgets, route, repository/validation/checkpoint state, next action, rollback and claim boundary.

It rejects transcript, prompts, hidden reasoning, raw provider output, credentials, tokens, passwords and DSNs.

## Recovery policy

Recovery is bounded by both inherited Session 13 execution budgets and unified graph cycles.

```text
unified_max_recovery_cycles = 2
```

A Boss recommendation cannot create an unbounded loop. When the recovery budget is exhausted, the supervisor sends the retained candidate through coherence validation and forces human authority.

## Competition policy

Python creates four immutable candidates:

- baseline: deterministic estimator result;
- aggressive: bounded discount without crossing known lower evidence bounds;
- conservative: bounded risk buffer respecting upper evidence bounds;
- synthesized: confidence-weighted deterministic combination.

Missing hours and material divergence are hard Energy constraints. Low confidence contributes a soft penalty. Hard failure retains baseline arithmetic and requires human review.

Competition does not claim that model personas improve accuracy. Model-generated competition remains disabled pending matched evaluation.

## Composition roots and rollback

| Path | Graph | Status |
|---|---|---|
| `/api/v1/estimate/graph` | Session 14 supervised graph | preserved rollback |
| `/api/v1/estimate/graph/reviewed/start` | Session 13 Plus reviewed graph | preserved rollback |
| `/api/v1/estimate/graph/unified` | canonical consolidated graph | additive candidate |

FastAPI owns each runtime independently. Failure to initialize the unified runtime does not prevent the older runtimes from being registered.

## Observability

Unified root and node spans:

```text
session13_14_plus.graph.run
session13_14_plus.graph.node
```

Allowlisted telemetry may include graph/policy version, route destination, reason code, capability record IDs, candidate IDs, Energy snapshot ID, Critic/Boss disposition, review status/revision and state-delta keys.

It must not include transcript, prompts, raw model responses, hidden reasoning, credentials or connection strings.

## Claim boundary

Supported only after exact-head CI and PostgreSQL evidence are green:

> The repository contains a separately versioned unified graph that semantically consolidates Session 13 Plus reviewed orchestration with Session 14 Plus supervised HITL, capability-authorized routing, compact-context integrity and deterministic Energy-Aware competition while preserving rollback paths.

Not established by this architecture alone:

- production superiority over the reviewed or supervised paths;
- lossless context compaction;
- current live availability of every calibrated provider route;
- improved estimate accuracy from candidate competition;
- authorization to merge into `main` or a protected coursework branch.
