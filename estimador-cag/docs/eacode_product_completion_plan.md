# EACODE Product Completion Plan

Updated: 2026-07-22  
Product: Energy Aware Code (EACODE)  
Canonical branch: `EACODE`  
Authoritative checkpoint: `docs/eacode_release_checkpoint_2026-07-22.md`

## Executive status

The deterministic alpha control plane is implemented on PR #15. The remaining gates are manual host/provider/browser evidence and later product extraction or production hardening.

“Deterministic complete” means the contracts, implementation, tests, CI gates, API surface, and documentation agree. It does not mean production-ready, arbitrary-code sandboxed, or proven superior across live language models.

## Product vision

```text
First build the judge.
Then give it controlled hands.
The hands never approve themselves.
```

EACODE sits between agentic coding tools, language models, repositories, and execution adapters. Models propose. Deterministic policy owns evidence sufficiency, hard constraints, budgets, authority, and final disposition.

## Capability matrix

| Capability | State | Evidence boundary |
|---|---|---|
| Kiro-like SDD packets | Implemented | requirements, design, tasks, policy, acceptance, decisions, evidence |
| Deterministic critics/scorer/boss | Implemented | unit, integration, smoke, and full-gate tests |
| Evidence and decision ledgers | Implemented | hashing, integrity, recovery, retention, manifests |
| Persistent LangGraph judge | Implemented | SQLite restart/resume and human interrupts |
| Controlled planning and fake evidence | Implemented | Specs 0007/0008 deterministic evidence |
| Secure one-time live-tool boundary | Implemented | typed intent, full snapshot, SQLite authority, process/evidence tests |
| Manual host execution proof | Pending | harmless command and Windows cleanup evidence |
| Provider-neutral selection | Implemented | verified registry and deterministic selector |
| Live provider adapters | Implemented, opt-in | deterministic payload/evidence tests; live success requires secrets |
| Context compaction acceptance | Implemented | freshness, loss, secrets, decay, rehydration tests |
| Bounded boss/critic governance | Implemented | fail-closed findings and full budget enforcement |
| Product API and minimal UI | Implemented | FastAPI/TestClient and HTML contract tests |
| Governance contract benchmark | Implemented | matched synthetic single-vs-governed fixtures |
| Live provider/multi-agent quality benchmark | Pending | matched secret-backed evaluations |
| EACORE extraction | Deferred | requires independently proven EACHAT equivalence |
| Production deployment | Deferred | threat model, isolation, identity, operations, observability |

## Completed phases

1. Trust, integrity, recovery, retention, and manifests.
2. Persistent deterministic judge and human intervention.
3. Controlled command planning and fake/dry-run evidence.
4. Logical authorization and persisted interrupt.
5. Typed live execution, complete repository snapshot, authoritative one-time authorization, secure process lifecycle, and normalized evidence.
6. Verified provider routing and hardened opt-in adapters.
7. Context-compaction acceptance and rehydration.
8. Fail-closed multi-agent boss and complete declared budgets.
9. FastAPI control-plane routes and same-origin selector UI.
10. Matched deterministic governance benchmark.
11. SDD, README, handoff, roadmap, evidence, and claim-boundary reconciliation.

## Remaining manual and future phases

### Manual evidence

- harmless live-tool smoke;
- Windows timeout, cancellation, child process, and cleanup proof;
- live provider smokes with current valid credentials;
- browser smoke of `/eacode/ui`.

### Future product work

- bounded autonomous repair quality evaluation;
- live matched provider and agent benchmarks;
- richer review console and decision timeline;
- packaging and extraction rehearsal;
- EACORE extraction gate after EACHAT equivalence;
- production-grade isolation, identity, deployment, and operations.

## Risk register

| Risk | Severity | Current mitigation |
|---|---|---|
| executor approves itself | critical | executor returns evidence only; deterministic boss decides |
| fake plan promoted to live | critical | typed live plan/intent and secure CLI; fake/dry-run rejected |
| stale/replayed approval | critical | full snapshot, integrity store, nonce, reservation, one-time completion |
| repository changes after approval | critical | complete snapshot recomputed immediately before process creation |
| secret leakage | high | minimal environment, cross-chunk/final redaction, sanitized errors |
| surviving child process | high | process groups/session, cancellation polling, verified cleanup, fail closed |
| provider fixture drift | high | source-versioned verified overlay and explicit freshness |
| planned route misreported as served | high | requested/planned/served contracts kept separate |
| empty consensus accepts | high | empty/invalid findings escalate |
| majority overrides hard constraint | critical | hard violation deterministically rejects |
| summary loses critical state | high | loss audit, hashes, freshness, contradiction and decay gates, rehydration |
| synthetic benchmark overclaimed | medium | explicit contract-only claim boundary |

## Acceptance gates

Deterministic integration requires:

- Ruff;
- Python compilation;
- full tests;
- Energy Core boundary;
- every smoke;
- canonical full gate;
- root smoke;
- clean repository status;
- no temporary diagnostics;
- synchronized SDD/status documents;
- reviewed PR claim boundary.

Manual evidence is recorded separately and never fabricated by deterministic CI.

## Current merge target

PR #15 targets `EACODE`. It must remain unmerged until its final clean CI passes. After merge, a fresh CI run on `EACODE` must pass before the deterministic alpha is declared integrated.

## Claim boundary

Allowed and blocked claims are defined in `docs/eacode_release_checkpoint_2026-07-22.md`.
