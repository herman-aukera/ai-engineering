# Energy Aware Chat examiner quickstart

Status: one-page review path for the final-project branch.

## Scope

Use this guide only for the Energy Aware Chat branch:

```text
EACHAT
```

Do not use the unfiltered GitHub Actions page as the proof source. It mixes unrelated branches.

## Review order

1. `docs/energy_aware_chat_final_submission_handoff.md`
2. `docs/energy_aware_chat_final_project_proof_packet.md`
3. `docs/energy_aware_chat_actions_filtering.md`
4. `docs/energy_aware_chat_demo_script.md`
5. `docs/energy_aware_chat_pr_body_draft.md`

## Local proof

From `estimador-cag`:

```bash
bash scripts/validate_energy_chat.sh
```

Expected evidence shape:

- demo payload contracts pass,
- focused Energy Chat tests pass,
- full suite passes,
- root diff check passes,
- final status is clean.

## CI proof

From repository root:

```bash
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

The proof target must be:

```text
workflow = Energy Aware Chat CI
branch = EACHAT
sha = current HEAD
```

## Claim boundary

Allowed claim:

```text
measurement_only_no_quality_claim
```

Do not claim production readiness, deployment readiness, RAG grounding, autonomous agent orchestration, or quality improvement over the baseline provider.
