# EACODE Release Checkpoint — 2026-07-22

## Status

Product: Energy Aware Code (EACODE)  
Target branch: `EACODE`  
Integration PR: #15  
Maturity: deterministic alpha control plane  
Production readiness: **not claimed**

This document is the authoritative status and claim boundary for the 2026-07-22 repair. Repository state, tests, current CI, and accepted specifications remain stronger evidence than this summary.

## Product architecture

```text
SDD specification + policy + candidate + evidence
    -> independent critics
    -> constraint-energy evaluation
    -> deterministic boss/decider
    -> accept | repair | reject | clarify | escalate
    -> optional provider proposal
    -> bounded one-time authorization
    -> secure tool/process adapter
    -> normalized sanitized evidence
    -> critic and boss reevaluation
    -> append-only decision ledger
```

Language models and coding agents propose. Deterministic Python owns hard constraints, evidence sufficiency, budgets, repository-state verification, authority, and final disposition.

## Implemented deterministic boundary

### SDD layer

- versioned requirements, design, tasks, policy, acceptance, decisions, and evidence under `.energy/specs/`;
- repository-level project instructions in `CLAUDE.md`;
- red-green tests and CI claim gates;
- explicit source-of-truth and evidence-level hierarchy.

This is Kiro-like specification-driven development methodology. It is not a claim of feature parity with the Kiro IDE product.

### Spec 0009 — governed live-tool boundary

Implemented on PR #15:

- explicit typed live-execution plan and intent;
- fake and dry-run plans cannot become real execution;
- authorization bound to plan hash and immutable repository snapshot;
- snapshot includes HEAD, tree, staged diff, unstaged diff, and untracked-state digest;
- authoritative SQLite receipt store with integrity checking, restart persistence, replay rejection, atomic reservation, and one-time completion;
- pre-start actor, receipt, intent, plan, executable, argument, environment, root, and snapshot verification;
- `shell=False` and argument-list process creation;
- dedicated process-group/session options;
- prompt cancellation polling, timeout handling, verified cleanup, and fail-closed cleanup uncertainty;
- bounded stdout/stderr, cross-chunk plus final redaction, accurate truncation, and sanitized normalized evidence;
- secure CLI requiring typed live artifacts, persistent authority, receipt identity, and explicit `--live-tool`;
- historical real-process adapter permanently disabled; deterministic failure injection retained for CI.

Deterministic implementation is accepted. A harmless host-level process smoke and Windows process-tree cleanup demonstration remain manual evidence gates.

### Provider-neutral routing

Implemented:

- `auto | deepseek | kimi | openai` provider request;
- `minimal | medium | max` profiles;
- requested, planned, configured, and served evidence kept distinct;
- verified capability overlay with source/version/freshness metadata and consistent per-1K price fields;
- DeepSeek, Kimi Platform, Kimi Code, and OpenAI surfaces kept distinct;
- correct Kimi Code endpoint and conservative entitlement-aware K3/K2.7 contracts;
- timeout milliseconds converted to HTTP seconds;
- provider-specific reasoning controls;
- served reasoning effort recorded only when provider evidence echoes it;
- sanitized provider failures and token-aware cost evidence;
- deterministic CI remains network-free and keyless.

Live-provider success is not implied by deterministic tests. DeepSeek, Kimi, and OpenAI require separate opt-in secret-backed smoke evidence.

### Context compaction

Implemented:

- immutable source references, event ranges, source hashes, decisions, evidence, constraints, current state, and rehydration references;
- minimal, medium, and max deterministic profiles;
- loss auditing;
- repository snapshot, policy, schema, source-hash, and age freshness gates;
- secret and hidden-reasoning exclusion;
- failing-gate and contradiction rejection;
- summary-of-summary decay detection;
- failed audits block acceptance and trigger supplied rehydration callbacks.

This proves deterministic compaction contracts, not model-generated summary quality.

### Energy-Aware boss and critics

Implemented:

- typed proposer, critic, reviewer, and boss roles;
- independent ownership and disagreement records;
- per-agent and global cost, latency, tool-call, agent-count, and concurrency budgets;
- empty or invalid findings escalate instead of accepting;
- hard-constraint violations cannot be outvoted;
- budget overruns escalate;
- deterministic boss is the sole final authority.

### Product API and UI

Implemented:

- `GET /eacode/status`;
- `GET /eacode/capabilities`;
- `POST /eacode/select`;
- `GET /eacode/ui` same-origin selector interface;
- explicit requested/planned/served display contract;
- live process execution reported disabled on the public control-plane status.

HTTP and HTML contracts are CI-tested. A manual browser smoke remains separate evidence.

### Matched deterministic governance benchmark

The versioned synthetic benchmark applies identical findings to:

1. a single unchecked proposal baseline; and
2. the deterministic Energy-Aware boss.

The default fixture result is:

```text
single unchecked: 1/4 expected dispositions
governed boss:    4/4 expected dispositions
delta:            +3 contract cases
```

This proves the encoded governance invariants catch hard violations, missing evidence, and disagreement in those fixtures. It does **not** prove that multiple LLM agents improve real-world coding quality, cost, or latency.

## Current claim boundary

Allowed:

- EACODE has a Kiro-like SDD layer.
- EACODE has a provider-neutral Energy-Aware boss/critic decision layer.
- EACODE has deterministic routing contracts for DeepSeek, Kimi, and OpenAI.
- EACODE has a secure, disabled-by-default, one-time-authorized local process boundary implemented and CI-tested without real process execution in CI.
- EACODE has deterministic compaction acceptance and rehydration contracts.
- EACODE exposes a tested FastAPI selector/control-plane surface and minimal same-origin UI.
- EACODE has a matched deterministic governance contract benchmark.

Blocked:

- safe execution of arbitrary untrusted code;
- VM, container, kernel, or hosted sandbox isolation;
- complete Windows host cleanup proof until manual smoke evidence exists;
- current live success for all providers without secret-backed smoke runs;
- exact served effort when the provider does not echo it;
- provider or multi-agent superiority without live matched evaluations;
- autonomous coding-repair quality;
- complete browser UX proof without manual browser smoke;
- EACORE extraction before equivalent EACHAT contracts are independently proven;
- production readiness.

## Merge gate

PR #15 may merge into `EACODE` only after:

- Ruff passes;
- Python compilation passes;
- full tests pass;
- Energy Core boundary and every smoke pass;
- canonical full gate passes;
- root smoke passes;
- repository remains clean;
- temporary diagnostic workflows are absent;
- this checkpoint, README, CLAUDE memory, handoff, product plan, Specs 0009/0010 acceptance, decisions, evidence, and PR body agree.

After merge, verify a fresh CI run on `EACODE` before declaring the deterministic alpha integrated.
