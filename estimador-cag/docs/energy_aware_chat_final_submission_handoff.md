# Energy Aware Chat final submission handoff

Status: final reviewer handoff for the current Energy Aware Chat branch.

## Certified branch

```text
EACHAT
```

## Latest accepted checkpoint before this handoff

```text
ef2a865
```

The branch has since moved into a production-oriented MVP candidate with deterministic RAG grounding, deterministic agent orchestration, a DeepSeek-to-Kimi fallback seam, and deployment skeleton. Re-certify the current SHA before final submission.

## Required proof commands

Run from the repository root unless noted otherwise.

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch EACHAT
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
2. `docs/energy_aware_chat_mvp_upgrade.md`
3. `docs/energy_aware_chat_final_project_proof_packet.md`
4. `docs/energy_aware_chat_actions_filtering.md`
5. `docs/energy_aware_chat_live_demo_readiness.md`
6. `docs/energy_aware_chat_api_smoke_guide.md`

## Claim boundaries

Do not claim production readiness, live public deployment, live fallback proof without the manual live smoke workflow, vector database RAG grounding, or model quality improvement. The benchmark claim remains measurement only.

Allowed after current local and CI proof:

```text
production-oriented MVP candidate with deterministic RAG grounding baseline, deterministic agent orchestration, fallback seam, and deployment skeleton
```

Required token:

```text
measurement_only_no_quality_claim
```
