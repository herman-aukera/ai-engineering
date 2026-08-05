# Energy Aware Chat live provider evidence template

Status: manual smoke evidence template.
Branch: `EACHAT`.
Workflow: `Energy Aware Chat Live Provider Smoke`.

## Purpose

This template records whether the live provider path works with real secrets.
It is required before claiming live DeepSeek-to-Kimi fallback proof.

## Manual workflow command

```bash
gh workflow run "Energy Aware Chat Live Provider Smoke" --ref EACHAT
```

## Required secrets

```text
DEEPSEEK_API_KEY
KIMI_API_KEY
```

Do not paste actual secret values into this template.

## Evidence record

Fill this after the manual workflow runs.

```json
{
  "branch": "EACHAT",
  "sha": "replace-with-tested-sha",
  "workflow": "Energy Aware Chat Live Provider Smoke",
  "run_id": "replace-with-run-id",
  "status": "completed | failed | skipped",
  "conclusion": "success | failure | cancelled",
  "deepseek_primary_result": "pass | fail | skipped",
  "kimi_backup_result": "pass | fail | skipped",
  "fallback_observed": "yes | no | not-tested",
  "secrets_exposed": false,
  "claim_allowed": false
}
```

## Claim decision rule

Set `claim_allowed` to `true` only when:

1. the workflow conclusion is success,
2. no secret is exposed,
3. DeepSeek primary path was exercised,
4. Kimi backup path was either exercised directly or fallback was intentionally triggered and observed,
5. the exact SHA matches the branch head being submitted.

## Allowed claim after successful live smoke

```text
Live provider smoke passed for the tested SHA, including the configured DeepSeek and Kimi provider paths.
```

## Still forbidden after successful live smoke

```text
Energy Aware Chat is production-ready.
Energy Aware Chat improves quality over DeepSeek.
Fallback is universally reliable under all outage modes.
```

## Failure handling

If the workflow fails:

1. Do not change claim wording to hide the failure.
2. Inspect workflow logs.
3. Classify failure as configuration, provider, code, timeout, or secret setup.
4. Patch the smallest failing layer.
5. Rerun deterministic local validation before another live smoke.

## Reviewer note

Normal deterministic CI must stay green without real provider keys.
Live provider smoke is optional for the deterministic MVP, but required for live provider claims.
