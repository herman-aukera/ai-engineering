# Energy Aware Chat current-head audit

## Source of truth

Audit baseline: `EACHAT` at `c08d35ec25f1dc666c52633b9a9abe94207a63ba`. Resolve the final head with `git rev-parse HEAD`; the audit repair commit follows that baseline. PR #5 remains open and unmerged. GitHub reports it as conflicting with `main`; conflict resolution is an integration decision, not a product defect.

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
| Security and dependencies | implemented at CI evidence level | secret/history scan, contracts, isolated lock audit and service smoke |
| Deployment/release collection | partial | claim gate exists; no public URL, incident response, or user telemetry |

## Historical findings

Resolved in production code and tests: caller-controlled profiles, implicit cross-provider fallback, missing V2 flag, false no-generation metadata, per-request checkpointer, regenerative replay, out-of-band revision validation, placeholder PostgreSQL retention/redaction, standalone observability/evidence hardening, conflated provider facts, unsafe browser rendering, and missing restart proof.

The old description of context and committee/adaptive orchestration as contracts only is historical: both now have bounded runtime implementations. Their benefit is not proven, so improvement and superiority claims remain blocked.

## Verification

The Linux gates bind checkout to the event SHA and fail closed: `CI - Estimador CAG`, `Energy Aware Chat CI`, `EACHAT - Durable Memory`, `EACHAT - Fixed Quality`, and `EACHAT - Container Canary`. Deterministic jobs use test credentials and fake/local-safe providers.

```bash
cd /workspaces/ai-engineering/estimador-cag
UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh

cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh EACHAT "$(git rev-parse HEAD)"
```

Allowed claims: CI-validated deterministic graph/API behavior, bounded routing, authoritative replay/resume, PostgreSQL and encrypted-memory integration evidence, safe browser journey, fixed-corpus measurement, security/dependency audit, and container restart proof.

Blocked claims: production readiness, public deployment, real-user telemetry, provider/model superiority, automatic-routing improvement, orchestration superiority, context-rot prevention, and live quality improvement.

## External runbooks and human decision

1. Run the manual credentialed provider smoke and retain sanitized output.
2. Run a versioned same-task benchmark with an explicit rubric before changing `measurement_only_no_quality_claim`.
3. Deploy to an approved target and record URL, health, demo, incident, and monitoring evidence.
4. Decide whether to authorize deliberate conflict resolution with `main`; do not merge PR #5 as part of this audit.
