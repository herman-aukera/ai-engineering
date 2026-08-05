# Energy Aware Chat final product-path integration record

## Current source of truth

```text
final_product_branch=EACHAT
final_product_head=2028074ad9826f987595fb9b9a2fed8e5d097231
integrated_main_head=0ca76f52b708dacf79007f4c914e2940ee1e878a
pull_request=5
pull_request_state=merged
merged_at=2026-08-05
claim_status=release_claims_blocked_missing_evidence
benchmark_claim=measurement_only_no_quality_claim
```

## Summary

EACHAT has a deterministic graph-backed chat path plus a bounded live route; deterministic critics and energy decisions; bounded repair and six dispositions; Decision Ledger and Energy Card; honest pending responses; application and PostgreSQL checkpoint replay; isolated conversations; revision-guarded human resume; durable encrypted memory; integrated observability/evidence integrity; a safe browser UI; bounded provider/context/orchestration runtimes; fixed-corpus measurement; security/dependency gates; isolated production smoke; and a container restart canary.

The consolidated reviewer source is `docs/energy_aware_chat_current_audit.md`. Historical milestone and direct-repair documents are background, not current defect lists.

## Integration record

PR #5 was reconciled with `main` through tree-preserving commit:

```text
8b4ab9ad4d91e21636e051dced9937344952ce66
```

The release candidate then received a focused production dependency repair for `cryptography==50.0.0`, including regenerated `uv.lock` and `uv.lock.sha256`.

PR #5 merged into `main` at:

```text
0ca76f52b708dacf79007f4c914e2940ee1e878a
```

No squash, history rewrite, or force-push was used.

## Validation

Final product-head evidence:

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

```bash
cd /workspaces/ai-engineering/estimador-cag
UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh

cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh main "$(git rev-parse HEAD)"
```

## Claim boundary

Allowed: CI-validated deterministic graph/API behavior, bounded provider routing, authoritative replay/resume, PostgreSQL and encrypted-memory integration evidence, browser journey, fixed-corpus measurement, secret-history and dependency audit, isolated production smoke, container restart proof, and successful integration into `main`.

Do not claim production readiness, public deployment, real-user telemetry, provider/model superiority, automatic-routing improvement, committee/adaptive superiority, context-rot prevention, live quality improvement, or vector database RAG grounding beyond committed evidence.

## Remaining external gates

1. Credentialed bounded live-provider smoke.
2. Matched same-task live quality benchmark.
3. Approved private staging deployment.
4. Authentication, rate limiting, deployed monitoring, incident response, and data-retention controls.
5. Monitored canary and public-release decision.
