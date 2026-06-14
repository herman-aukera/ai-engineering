# Energy Aware Chat overnight work log

Status: overnight safety and morning-validation handoff
Branch: `EACHAT`
Pre-overnight safepoint: `3e797790501e7920ffd245cca718a4eed1cc3803`
Rollback branch: `backup/EACHAT-pre-overnight-extra-20260614`

## Why this file exists

Gonzalo closed the Codespace before sleeping and explicitly asked to keep the work safe enough to test tomorrow and revert if needed.

This document records the safe checkpoint, the morning validation path, the rollback path, and the claim boundaries for the Energy Aware Chat final-project MVP candidate.

## Current MVP candidate scope

The branch is intended to be evaluated as a production-oriented MVP candidate, not as a production-ready service.

Implemented MVP candidate layers:

1. deterministic Energy Aware Chat evaluator,
2. Energy Card response metadata,
3. deterministic one-pass repair seam,
4. source-needed classifier,
5. evidence bundle normalizer,
6. deterministic project-source RAG baseline,
7. deterministic local agent path through `/energy-chat/chat`,
8. DeepSeek baseline seam with DeepSeek-to-Kimi fallback ladder,
9. manual live-provider smoke workflow,
10. Docker and compose deployment skeleton,
11. reviewer docs and demo payloads.

## What still requires proof

Do not claim these until the evidence exists:

1. live DeepSeek-to-Kimi fallback proof,
2. deployed public URL,
3. deployment smoke result,
4. measured quality improvement over plain DeepSeek,
5. vector database RAG for Energy Aware Chat,
6. production readiness.

## Morning validation commands

Run from a fresh Codespace terminal:

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch EACHAT
git pull --ff-only

git rev-parse --short HEAD
git status --short

cd estimador-cag
bash scripts/validate_energy_chat.sh

cd /workspaces/ai-engineering
bash estimador-cag/scripts/check_energy_chat_ci.sh
```

Accept the branch only if:

1. focused Energy Chat tests pass,
2. full pytest passes,
3. root diff check passes,
4. status is clean,
5. dedicated Energy Chat CI proof returns success for `EACHAT` and the current SHA.

## Optional live-provider proof

Only run this after repository secrets are configured in GitHub Actions:

```bash
gh workflow run "Energy Aware Chat Live Provider Smoke" --ref EACHAT
```

Required secrets:

1. `DEEPSEEK_API_KEY`,
2. `KIMI_API_KEY`.

The live-provider smoke must stay separate from deterministic CI.

## Rollback path

Use this only if tomorrow's branch head is noisy, broken, or not worth keeping.

```bash
cd /workspaces/ai-engineering

git fetch origin
git switch EACHAT
git reset --hard origin/backup/EACHAT-pre-overnight-extra-20260614
```

After rollback, run validation before any push.

Do not force-push unless the rollback is an explicit decision and the replacement branch is locally green.

## Claim boundary

Allowed wording after local and CI proof:

```text
Energy Aware Chat is a production-oriented final-project MVP candidate with deterministic RAG grounding baseline, deterministic agent orchestration, DeepSeek-to-Kimi fallback seam, and deployment skeleton.
```

Forbidden wording until further proof:

```text
production-ready
live deployed
proves quality improvement
fully benchmarked
vector database RAG complete
live fallback verified
```

## Next work order

Recommended order after morning validation:

1. certify the current `EACHAT` head locally and through dedicated CI,
2. run or configure live-provider smoke,
3. perform deployment smoke locally or through a low-friction host,
4. create the final-project eval dataset and regression report,
5. cut a final delivery branch only after the MVP candidate is stable.
