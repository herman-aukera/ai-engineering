# Energy Aware Chat completion roadmap

## Current status

Milestones 0-21 are implemented and integrated into `main` through merged PR #5.

Final product branch head:

```text
EACHAT = 2028074ad9826f987595fb9b9a2fed8e5d097231
```

Product integration checkpoint:

```text
main = 0ca76f52b708dacf79007f4c914e2940ee1e878a
```

Resolve the current `main` head before making an exact-head release claim.

There is no remaining core product implementation or integration milestone in this roadmap. The current evidence matrix, historical defect disposition, claim boundary, and external runbooks are consolidated in `docs/energy_aware_chat_current_audit.md`.

Implemented product layers include typed graph state and reducers, evidence routing, provider boundaries, deterministic critics and decisions, bounded repair, six dispositions, Decision Ledger, Energy Card, graph-backed APIs, explicit fallback authorization, V2 rollback, honest pending responses, authoritative replay, thread isolation, human revision guards, PostgreSQL persistence, encrypted conversation memory, observability, evidence integrity, safe browser UI, bounded provider/context/orchestration runtimes, fixed-corpus evaluation, security/dependency audit, isolated production smoke, container restart proof, and bounded DeepSeek live-integration evidence.

## Integration completion

PR #5 was reconciled with `main` using a tree-preserving history merge and then merged on 2026-08-05.

A rollback checkpoint remains available at:

```text
backup/EACHAT-pre-main-integration-20260805
149c9922cdc2afea3e537b5c17f1722fefcb23d2
```

Post-integration `main` CI runs `31034999430` and `31035460047` passed broad regression, Energy Chat validation, browser, PostgreSQL, security/dependency, isolated production installation, and service smoke.

## Live-provider completion

A bounded DeepSeek V4 Flash live smoke completed successfully on 2026-08-05:

```text
run = 31035837096
provider = deepseek
model = deepseek-v4-flash
effort = balanced
provider_calls = 1
fallback = false
sanitized_evidence = evals/energy_chat/live_provider_smoke_deepseek_2026-08-05.json
```

This proves the tested DeepSeek integration path can execute one bounded live graph call. It does not prove quality improvement, provider superiority, fallback reliability, Kimi/OpenAI integration, or production readiness.

## External completion boundary

The following remain evidence-gated:

1. Kimi/OpenAI live smokes only if those providers are in the intended release scope;
2. an intentional cross-provider fallback scenario before fallback claims;
3. a matched same-task live quality benchmark;
4. private staging deployment and smoke evidence;
5. authentication, rate limiting, deployed monitoring, incident response, and data-retention operations;
6. monitored canary and real-user telemetry;
7. human public-release decision.

Release claims remain `release_claims_blocked_missing_evidence` and `measurement_only_no_quality_claim`. Do not claim provider superiority, routing/orchestration improvement, context-rot prevention, public deployment, production readiness, or production telemetry.
