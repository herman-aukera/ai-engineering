# Energy Aware Chat pull request body draft

## Current source of truth

```text
branch=EACHAT
head=0df0e8e
latest_ci=success
workflow=CI - Estimator CAG
run_id=27570100847
energy_chat_validation_gate=success
claim_status=measurement_only_no_quality_claim
```

## Summary

This branch keeps the Energy Aware Chat final project track inside `estimador-cag`.

The current scope is a browser-testable, production-oriented MVP candidate with deterministic answer evaluation, Energy Card output, source requirement detection, evidence bundles, deterministic project-source grounding, local agent orchestration, benchmark measurement artifacts, reviewer documentation, release snapshots, closeout proof, continuation guard, and exact CI proof.

## Fast reviewer entry point

Start here:

```text
docs/energy_aware_chat_reviewer_index.md
```

Useful reviewer docs:

1. `docs/energy_aware_chat_examiner_quickstart.md`
2. `docs/energy_aware_chat_evaluator_landing_page.md`
3. `docs/energy_aware_chat_final_project_acceptance_matrix.md`
4. `docs/energy_aware_chat_final_project_proof_packet.md`
5. `docs/energy_aware_chat_closeout_pack.md`
6. `docs/energy_aware_chat_unsupervised_continuation.md`
7. `docs/energy_aware_chat_fixed_benchmark_report.md`

## Validation commands

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch EACHAT
git pull --ff-only

git rev-parse --short HEAD
git status --short

cd estimador-cag
UV_HTTP_TIMEOUT=600 bash scripts/validate_energy_chat.sh
```

```bash
cd /workspaces/ai-engineering

bash estimador-cag/scripts/check_energy_chat_ci.sh
```

## Claim boundaries

Benchmark wording is measurement only:

```text
measurement_only_no_quality_claim
```

Allowed short description:

```text
Energy Aware Chat is a browser-testable, production-oriented MVP candidate on the EACHAT incubator branch.
```

Do not claim:

1. production readiness,
2. public deployment is live,
3. quality improvement over plain DeepSeek,
4. frontier-model superiority,
5. live provider fallback proof without the manual live-provider smoke workflow.
