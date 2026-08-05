# Energy Aware Chat completion roadmap

## Current status

Milestones 0-21 are implemented and integrated into `main` through merged PR #5.

Final product branch head:

```text
EACHAT = 2028074ad9826f987595fb9b9a2fed8e5d097231
```

Integrated `main` checkpoint:

```text
main = 0ca76f52b708dacf79007f4c914e2940ee1e878a
```

There is no remaining repository-controlled implementation or integration milestone in this roadmap. The current evidence matrix, historical defect disposition, claim boundary, and external runbooks are consolidated in `docs/energy_aware_chat_current_audit.md`.

Implemented product layers include typed graph state and reducers, evidence routing, provider boundaries, deterministic critics and decisions, bounded repair, six dispositions, Decision Ledger, Energy Card, graph-backed APIs, explicit fallback authorization, V2 rollback, honest pending responses, authoritative replay, thread isolation, human revision guards, PostgreSQL persistence, encrypted conversation memory, observability, evidence integrity, safe browser UI, bounded provider/context/orchestration runtimes, fixed-corpus evaluation, security/dependency audit, isolated production smoke, and container restart proof.

## Integration completion

PR #5 was reconciled with `main` using a tree-preserving history merge and then merged on 2026-08-05.

A rollback checkpoint remains available at:

```text
backup/EACHAT-pre-main-integration-20260805
149c9922cdc2afea3e537b5c17f1722fefcb23d2
```

Post-merge `main` CI run `31034999430` passed broad regression, Energy Chat validation, browser, PostgreSQL, security/dependency, isolated production installation, and service smoke.

## External completion boundary

The following are not repository implementation milestones and remain evidence-gated:

1. credentialed live-provider smoke;
2. matched same-task live quality benchmark;
3. private staging deployment and smoke evidence;
4. authentication, rate limiting, deployed monitoring, incident response, and data-retention operations;
5. monitored canary and real-user telemetry;
6. human public-release decision.

Release claims remain `release_claims_blocked_missing_evidence` and `measurement_only_no_quality_claim`. Do not claim provider superiority, routing/orchestration improvement, context-rot prevention, public deployment, production readiness, or production telemetry.
