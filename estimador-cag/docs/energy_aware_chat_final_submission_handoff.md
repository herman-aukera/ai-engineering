# Energy Aware Chat final submission handoff

Status: final reviewer handoff for the current Energy Aware Chat branch.

## Certified branch

```text
gg-finalproject-energy-aware-chat
```

## Latest accepted checkpoint before this handoff

```text
b7c9244
```

## Required proof commands

Run from the repository root unless noted otherwise.

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch gg-finalproject-energy-aware-chat
git pull --ff-only

cd estimador-cag

bash scripts/validate_energy_chat.sh
```

Then run the exact workflow proof from repository root.

```bash
cd /workspaces/ai-engineering

bash estimador-cag/scripts/check_energy_chat_ci.sh
```

## Expected proof shape

The accepted proof must include:

1. Energy Chat demo payload contracts passed.
2. Focused Energy Chat tests passed.
3. Full test suite passed.
4. Root diff check passed.
5. Status clean.
6. Workflow `Energy Aware Chat CI` succeeded for the exact current SHA.

## What to open first

1. `docs/energy_aware_chat_reviewer_index.md`
2. `docs/energy_aware_chat_final_project_proof_packet.md`
3. `docs/energy_aware_chat_actions_filtering.md`
4. `docs/energy_aware_chat_live_demo_readiness.md`
5. `docs/energy_aware_chat_api_smoke_guide.md`

## Claim boundaries

Do not claim production readiness, deployment readiness, RAG grounding, autonomous agent orchestration, or model quality improvement. The benchmark claim remains measurement only.

Required token:

```text
measurement_only_no_quality_claim
```
