# Energy Aware Chat live-provider evidence

Status: one bounded DeepSeek smoke complete; reusable manual workflow repaired.
Canonical workflow: `EACHAT - Live Provider Smoke`.

## Purpose

This document defines the evidence contract for credentialed provider smoke tests. A smoke test proves that one configured provider path can execute a bounded graph call for an exact SHA. It does not prove answer-quality improvement, model superiority, fallback reliability, production readiness, or public deployment.

## Reusable manual workflow

```bash
gh workflow run "EACHAT - Live Provider Smoke" \
  --ref main \
  -f provider=deepseek \
  -f effort=balanced
```

Supported inputs:

```text
provider: deepseek | kimi | openai
effort: fast | balanced | max
```

The workflow:

- checks out the selected exact SHA;
- uses environment-scoped secrets;
- makes exactly one bounded provider call;
- rejects implicit fallback;
- records no prompt, answer, or credential body;
- validates the sanitized JSON schema;
- uploads only the sanitized artifact.

## Required secrets

Depending on the selected provider:

```text
DEEPSEEK_API_KEY
KIMI_API_KEY or MOONSHOT_API_KEY
OPENAI_API_KEY
```

Never place secret values in files, logs, screenshots, issues, pull requests, or committed evidence.

## Completed DeepSeek evidence — 2026-08-05

Canonical evidence file:

```text
evals/energy_chat/live_provider_smoke_deepseek_2026-08-05.json
```

Summary:

```json
{
  "runtime_base_main_sha": "6f92f5a1b42d054336ea83fe7520b6d85c340f5d",
  "tested_sha": "717d744f3e5ce315ef3bb7d1df641b80f995b4a3",
  "workflow_run_id": 31035837096,
  "status": "success",
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "effort": "balanced",
  "provider_call_count": 1,
  "input_tokens": 303,
  "output_tokens": 576,
  "estimated_cost_usd": 0.000715,
  "provider_latency_ms": 12325,
  "fallback_used": false,
  "final_disposition": "repair",
  "answer_body_recorded": false,
  "prompt_body_recorded": false,
  "credential_recorded": false
}
```

A preceding `fast`-profile attempt reached the provider but was correctly rejected by the deterministic policy because provider latency exceeded that profile's budget. The `balanced` profile completed successfully.

## Allowed claim

```text
A bounded DeepSeek V4 Flash live integration smoke passed for the tested runtime and balanced profile, with one provider call, no fallback, and sanitized evidence.
```

## Claims still blocked

```text
Energy Aware Chat improves quality over plain DeepSeek.
DeepSeek is superior to Kimi or OpenAI.
Kimi or OpenAI live integration has passed.
Cross-provider fallback has been proven.
Automatic routing improves quality.
Energy Aware Chat is production-ready.
Energy Aware Chat is publicly deployed.
```

## Evidence template for future runs

```json
{
  "schema_version": 1,
  "evidence_type": "single_provider_live_smoke",
  "tested_at_utc": "replace",
  "runtime_base_main_sha": "replace",
  "tested_sha": "replace",
  "workflow_run_id": 0,
  "artifact_id": 0,
  "artifact_digest": "sha256:replace",
  "status": "success | failure | cancelled",
  "requested_provider": "deepseek | kimi | openai",
  "provider": "replace",
  "model": "replace",
  "effort": "fast | balanced | max",
  "provider_call_count": 1,
  "input_tokens": 0,
  "output_tokens": 0,
  "estimated_cost_usd": 0.0,
  "provider_latency_ms": 0,
  "fallback_used": false,
  "answer_body_recorded": false,
  "prompt_body_recorded": false,
  "credential_recorded": false,
  "claims_blocked": []
}
```

## Failure handling

1. Preserve the failure classification honestly.
2. Confirm whether a provider call actually occurred before retrying.
3. Distinguish workflow configuration, credentials, provider failure, model compatibility, and deterministic budget rejection.
4. Apply the smallest repair.
5. Keep deterministic CI credential-free.
6. Never weaken budgets merely to make a smoke test green without product justification.
