# Energy Aware Chat current-head audit

## Source of truth

The final `EACHAT` release-candidate head is `2028074ad9826f987595fb9b9a2fed8e5d097231`.

PR #5 was deliberately reconciled with `main` and merged on 2026-08-05. The resulting `main` merge commit is `0ca76f52b708dacf79007f4c914e2940ee1e878a`.

A rollback checkpoint remains available at:

```text
backup/EACHAT-pre-main-integration-20260805
149c9922cdc2afea3e537b5c17f1722fefcb23d2
```

Claim status remains `release_claims_blocked_missing_evidence` and `measurement_only_no_quality_claim`.

## Capability and evidence matrix

| Capability | Status | Production and proof |
|---|---|---|
| Graph state/reducers, evidence routing, candidate boundary | implemented | graph state/nodes/adapters plus focused and full deterministic suites |
| Critics, deterministic energy/decision, bounded repair, six dispositions | implemented | evaluator/graph decisions, immutable history, ledger and repair tests |
| Decision Ledger and Energy Card | implemented | authoritative graph projection and API/UI contract tests |
| Deterministic/live graph API and route-owned profiles | implemented | V2 runtime tests enforce mode/provider boundaries |
| Explicit allow-listed fallback and V2 rollback flag | implemented | provider policy, feature-flag, and compatibility tests |
| Awaiting-evidence honesty | implemented | pending projection omits generated and provider metadata |
| Application replay, isolation, human resume guards | implemented | HTTP replay and stale/wrong-thread/duplicate action tests |
| PostgreSQL migration, restart, retention, redaction, expiry | implemented | PostgreSQL runtime/conversation suites and durable-memory workflow |
| Durable encrypted conversation memory | implemented | encrypted PostgreSQL restart proof |
| Observability and evidence/citation integrity | implemented | integrated metrics and decision-linked hardening tests |
| Browser UI and XSS-safe rendering | implemented | DOM-safe contracts and Chromium journey artifact |
| Provider catalog and bounded adapters | implemented | verified catalog and fail-closed unsupported-combination tests |
| Context compaction runtime | implemented | snapshot/revision/hash and turn-isolation tests |
| Committee/adaptive runtime | implemented, bounded | runtime budgets and isolation tests |
| Fixed-corpus evaluation | implemented | deterministic fixed-quality workflow; measurement only |
| Live-provider evidence | blocked externally | manual credentialed workflow exists; no matched live proof |
| Container restart | implemented | PostgreSQL canary and authoritative replay |
| Security and dependencies | implemented at CI evidence level | secret/history scan, production contracts, isolated lock audit and service smoke |
| Main integration | complete | PR #5 merged after exact-head validation and tree-preserving history reconciliation |
| Deployment/release collection | partial | claim gate exists; no public URL, incident response, or user telemetry |

## Historical findings

Resolved in production code and tests: caller-controlled profiles, implicit cross-provider fallback, missing V2 flag, false no-generation metadata, per-request checkpointer, regenerative replay, out-of-band revision validation, placeholder PostgreSQL retention/redaction, standalone observability/evidence hardening, conflated provider facts, unsafe browser rendering, and missing restart proof.

The old description of context and committee/adaptive orchestration as contracts only is historical: both now have bounded runtime implementations. Their benefit is not proven, so improvement and superiority claims remain blocked.

The former PR conflict is also historical. `main` history was joined through tree-preserving commit `8b4ab9ad4d91e21636e051dced9937344952ce66`, and PR #5 was merged without squashing or rewriting the audited product history.

## Dependency security repair

Fresh integration CI detected three newly published advisories affecting `cryptography 48.0.1`. The isolated production runtime now pins:

```text
cryptography==50.0.0
```

The production `uv.lock` and its SHA-256 digest were regenerated in a temporary branch-scoped Linux workflow. Strict `pip-audit`, isolated installation, and production-service health smoke passed. The temporary write-enabled workflow was deleted before the repair was integrated.

## Verification

The Linux gates bind checkout to the event SHA and fail closed. Deterministic jobs use test credentials and fake/local-safe providers.

Final `EACHAT` exact-head evidence:

| Workflow | Run | Result |
|---|---:|---|
| CI - Estimador CAG | 31034792306 | successful |
| Energy Aware Chat CI | 31034789929 | successful |
| EACHAT - Durable Memory | 31034794097 | successful |
| EACHAT - Fixed Quality | 31034793085 | successful |
| EACHAT - Container Canary | 31034792439 | successful |
| Production lock repair verification | 31034693205 | successful |

Post-merge `main` evidence:

| Workflow | Run | Result |
|---|---:|---|
| CI - Estimador CAG | 31034999430 | successful |

The post-merge run passed broad regression, Energy Chat validation, PostgreSQL integration, Chromium browser journey, secret/history scanning, strict dependency audit, isolated production installation, and production-service health smoke.

```bash
cd /workspaces/ai-engineering/estimador-cag
UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh

cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh main "$(git rev-parse HEAD)"
```

Allowed claims: CI-validated deterministic graph/API behavior, bounded routing, authoritative replay/resume, PostgreSQL and encrypted-memory integration evidence, safe browser journey, fixed-corpus measurement, security/dependency audit, isolated production smoke, container restart proof, and successful integration into `main`.

Blocked claims: production readiness, public deployment, real-user telemetry, provider/model superiority, automatic-routing improvement, orchestration superiority, context-rot prevention, and live quality improvement.

## External completion boundary

1. Run the manual credentialed provider smoke and retain sanitized output.
2. Run a versioned same-task benchmark with an explicit rubric before changing `measurement_only_no_quality_claim`.
3. Deploy to an approved private staging target and record URL, health, demo, persistence, restart, rollback, incident, and monitoring evidence.
4. Add and verify authentication, rate limiting, deployed monitoring, alerting, incident response, and data-retention procedures.
5. Conduct a monitored canary before any public production claim.

## Current product label

> EACHAT is integrated into `main` as a production-oriented, demo-ready Energy Aware Chat release candidate. It is not yet production-ready for unrestricted public users.
