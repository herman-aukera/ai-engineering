# EACODE Project Memory

Claude Code and other coding agents must load this file when operating from `estimador-cag/` or a descendant.

## Mandatory sources

Read completely:

- @README_EACODE.md
- @docs/eacode_release_checkpoint_2026-07-22.md
- @docs/eacode_handoff_status.md
- @docs/eacode_threat_model.md
- @.energy/specs/0007-controlled-execution-evidence/requirements.md
- @.energy/specs/0008-execution-authorization/requirements.md
- @.energy/specs/0009-sandboxed-tool-adapter/requirements.md
- @.energy/specs/0009-sandboxed-tool-adapter/acceptance.md
- @.energy/specs/0010-provider-routing-context-compaction/requirements.md
- @.energy/specs/0010-provider-routing-context-compaction/design.md
- @.energy/specs/0011-demo-ready-beta/requirements.md
- @.energy/specs/0011-demo-ready-beta/design.md
- @.energy/specs/0012-production-hardening/requirements.md
- @.energy/specs/0012-production-hardening/design.md
- @.energy/specs/0012-production-hardening/acceptance.md
- @.energy/specs/0012-production-hardening/decisions.md

Current repository state, tests, diffs, and current-head CI are stronger evidence than documentation.

## Product objective

```text
SDD specification + policy + candidate + evidence
-> independent critics
-> constraint-energy evaluation
-> deterministic boss/decider
-> accept | repair | reject | clarify | escalate
-> bounded authorized action
-> normalized evidence
-> reevaluation
-> append-only decision ledger
```

Models propose. Deterministic Python owns hard constraints, evidence sufficiency, budgets, repository verification, authority, and final disposition.

## Current implementation status

```text
Spec 0007 — controlled planning and fake/dry-run evidence: deterministic complete
Spec 0008 — logical-revision authorization and persistent interrupt: deterministic complete
Spec 0009 — secure live-tool implementation: deterministic complete; manual host proof pending
Spec 0010 — verified routing, compaction guard, boss budgets, API/UI: deterministic complete
Spec 0011 — inspectable simulated beta journey: deterministic complete
Spec 0012 — tenant authority, durable beta state, minimal product image: implementation complete; current-head CI evidence required
```

### Spec 0009

Implemented:

- typed live plan and intent;
- complete repository snapshot binding;
- authoritative SQLite authorization with integrity, replay rejection, atomic reservation, and one-time completion;
- fail-closed pre-start verification;
- `shell=False`, argument-list execution, process group/session handling, cancellation, timeout, verified cleanup;
- cross-chunk plus final redaction and bounded output;
- normalized evidence returned for critic/decider reevaluation;
- secure CLI with explicit `--live-tool`;
- legacy real adapter permanently disabled;
- deterministic CI uses injected processes/fake tools only.

Blocked claims:

- arbitrary untrusted-code safety;
- VM/container/kernel isolation;
- complete Windows host cleanup proof until manual evidence exists.

### Specs 0010–0011

Implemented:

- provider-neutral request and deterministic route resolution;
- verified capability overlay with source/version/freshness and consistent units;
- DeepSeek, Kimi Platform, Kimi Code, and OpenAI surfaces separated;
- hardened opt-in provider adapters with timeouts, reasoning controls, cost evidence, and sanitized failures;
- requested/planned/served facts separated;
- deterministic context-compaction acceptance, loss audit, freshness, secret/hidden-reasoning exclusion, decay detection, and rehydration;
- fail-closed deterministic boss with declared budgets enforced;
- provider-neutral coding proposal, typed hard gates, semantic jury, deterministic action governor;
- inspectable repair, authorization, simulated execution, rollback, and reevaluation timeline;
- signed local session and provider-identity contracts;
- deterministic multi-mode beta benchmark.

### Spec 0012 non-negotiable boundary

Implemented:

- proposal preparation and inspection require signed sessions;
- viewer/reviewer/operator/admin may prepare and inspect their own inert proposals;
- only operator/admin may authorize and execute;
- non-admin access is tenant-scoped by verified backend user ID; admin cross-tenant access is explicit;
- client-controlled `human_authorization` is forbidden;
- automated repair creates an explicit `effective_proposal` revision;
- SQLite WAL persists typed runs and receipts with integrity hashes;
- receipts bind proposal, actor, exact scope, issuance, and expiry;
- receipt consumption and the single execution reservation are atomic and replay-safe;
- execution remains explicitly simulated;
- benchmark actual decisions are evidence-derived and independent of expected labels;
- wildcard CORS is forbidden;
- `app.eacode_main` is the dedicated EACODE product composition root;
- the minimal EACODE image excludes estimator routes, tests, Torch, Jupyter, and development dependencies;
- container CI must prove startup, UID, signed tenant access, restart persistence, vulnerability scan, SPDX SBOM, and runner isolation;
- GHCR publication is allowed only from canonical `EACODE`, by immutable SHA, with SBOM and provenance.

Do not regress these rules by reintroducing an in-memory global store, anonymous proposal routes, client authority flags, expected-label benchmark shortcuts, the full estimator app in the EACODE product image, or non-canonical image publication.

Blocked claims:

- live provider success without a current secret-backed smoke;
- exact served effort unless the provider echoes it;
- real coding-agent integration;
- real process execution from the beta API;
- horizontal or multi-region durability;
- live OIDC;
- external deployment;
- provider or multi-agent superiority without matched live evaluations;
- production readiness.

## Provider policy

Public profiles:

```text
provider: auto | deepseek | kimi | openai
profile: minimal | medium | max
context_profile: minimal | medium | max
```

Policy intent:

- DeepSeek is the cost-sensitive default.
- Kimi is the user-preferred frontier/open route.
- OpenAI is a budget-gated premium escalation.
- Unsupported, stale, unavailable, or unentitled combinations fail closed.
- A planned route is never described as the model actually served.

## Context policy

Always preserve:

```text
immutable raw events and artifacts
+ typed canonical state
+ versioned summaries
+ bounded recent window
+ evidence rehydration
```

Never persist secrets, credentials, hidden chain of thought, or unverified assumptions as facts. A summary cannot replace raw evidence.

## Multi-agent policy

Use multiple agents only for independent work such as critics, proposals, benchmarks, or evidence collection.

Required:

- typed shared state;
- independent ownership;
- bounded fan-out;
- disagreement records;
- cost, latency, tool, and concurrency budgets;
- no concurrent edits to one worktree;
- no majority override of hard constraints;
- no self-approval;
- deterministic boss owns final disposition.

## Product family boundary

- EACODE owns coding/repository/tool supervision.
- EACHAT owns conversational-answer supervision.
- LIDR task branches own mandatory coursework.
- EACORE extraction remains blocked until equivalent semantics are independently proven in at least two products.

Do not import estimation-specific or chat-specific semantics into EACODE core contracts.

## Git, CI, and terminal rules

- Inspect current branch, HEAD, upstream, and complete status before editing.
- Do not overwrite unknown or interrupted work.
- Do not merge, force-push, reset, clean, restore, switch, rebase, amend, or delete branches without explicit user authorization.
- Do not claim a gate from an earlier SHA as current-head evidence.
- Do not weaken a failing gate to obtain green status.
- Never print or persist API keys, signing keys, bearer tokens, or authorization receipt capabilities.
- Deterministic CI remains provider-free and real-process-free.
- Live provider/process evidence is opt-in and manual.
- Do not use `set -e` or `set -euo pipefail` in user-pasteable commands.
- Never place Markdown fences inside shell heredocs.

## Required response footer

```text
Decider verdict:
Evidence used:
Current branch and SHA:
Working-tree state:
Execution mode proven:
Provider mode proven:
Energy delta summary:
Claim boundary:
Next exact slice:
User approval required:
```
