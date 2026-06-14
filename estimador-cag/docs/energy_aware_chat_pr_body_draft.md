# Energy Aware Chat pull request body draft

## Summary

This branch adds the Energy Aware Chat final project track inside `estimador-cag`.

The current scope is a deterministic proof layer for answer evaluation, repair decisions, source requirement detection, evidence bundles, demo payloads, reviewer artifacts, release snapshots, and exact CI proof.

## Certified branch

```text
EACHAT
```

## Validation commands

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch EACHAT
git pull --ff-only

cd estimador-cag

bash scripts/validate_energy_chat.sh
```

```bash
cd /workspaces/ai-engineering

bash estimador-cag/scripts/check_energy_chat_ci.sh
```

## Reviewer entry points

1. `docs/energy_aware_chat_final_submission_handoff.md`
2. `docs/energy_aware_chat_reviewer_index.md`
3. `docs/energy_aware_chat_final_project_proof_packet.md`
4. `docs/energy_aware_chat_actions_filtering.md`
5. `docs/energy_aware_chat_live_demo_readiness.md`

## Claim boundaries

This branch does not claim production readiness, deployment readiness, RAG grounding, autonomous agent orchestration, or model quality improvement.

Benchmark wording is measurement only:

```text
measurement_only_no_quality_claim
```
