# Energy Aware Chat final product-path completion

## Current source of truth

```text
branch=EACHAT
head=resolve from current PR head SHA
audit_baseline=c08d35ec25f1dc666c52633b9a9abe94207a63ba
exact_head_ci=required
claim_status=release_claims_blocked_missing_evidence
benchmark_claim=measurement_only_no_quality_claim
```

## Summary

EACHAT has a deterministic graph-backed chat path plus a bounded live route; deterministic critics and energy decisions; bounded repair and six dispositions; Decision Ledger and Energy Card; honest pending responses; application and PostgreSQL checkpoint replay; isolated conversations; revision-guarded human resume; durable encrypted memory; integrated observability/evidence integrity; a safe browser UI; bounded provider/context/orchestration runtimes; fixed-corpus measurement; security/dependency gates; and a container restart canary.

The consolidated reviewer source is `docs/energy_aware_chat_current_audit.md`. Historical milestone and direct-repair documents are background, not current defect lists.

## Validation

```bash
cd /workspaces/ai-engineering/estimador-cag
UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh

cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh EACHAT "$(git rev-parse HEAD)"
```

Required exact-head workflows: `CI - Estimador CAG`, `Energy Aware Chat CI`, `EACHAT - Durable Memory`, `EACHAT - Fixed Quality`, and `EACHAT - Container Canary`.

## Claim boundary

Allowed: CI-validated deterministic graph/API behavior, bounded provider routing, authoritative replay/resume, PostgreSQL and encrypted-memory integration evidence, browser journey, fixed-corpus measurement, security/dependency audit, and container restart proof.

Do not claim production readiness, public deployment, real-user telemetry, provider/model superiority, automatic-routing improvement, committee/adaptive superiority, context-rot prevention, live quality improvement, or vector database RAG grounding beyond committed evidence.

PR #5 remains open and unmerged. Its conflict with `main` requires a separate human-authorized integration decision.
