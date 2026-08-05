# Energy Aware Chat examiner quickstart

Status: one-page review path for the final-project branch.

## Scope

Use this guide only for the Energy Aware Chat branch:

```text
EACHAT
```

Do not use the unfiltered GitHub Actions page as the proof source. It mixes unrelated branches.

## Review order

1. `docs/energy_aware_chat_mvp_upgrade.md`
2. `docs/energy_aware_chat_final_submission_handoff.md`
3. `docs/energy_aware_chat_final_project_proof_packet.md`
4. `docs/energy_aware_chat_actions_filtering.md`
5. `docs/energy_aware_chat_demo_script.md`
6. `docs/energy_aware_chat_pr_body_draft.md`

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

## Manual live provider smoke

Only after real GitHub secrets exist:

```bash
gh workflow run "Energy Aware Chat Live Provider Smoke" --ref EACHAT
```

This proves live DeepSeek visibility and live Kimi backup-tier visibility. It is separate from deterministic CI.

## Claim boundary

Allowed claim:

```text
measurement_only_no_quality_claim
```

Allowed after local and CI proof:

```text
production-oriented MVP candidate with deterministic RAG grounding baseline, deterministic agent orchestration, fallback seam, and deployment skeleton
```

Do not claim production readiness, a live public deployment, quality improvement over DeepSeek, live fallback proof without the manual smoke workflow, or vector database RAG grounding for Energy Aware Chat.
