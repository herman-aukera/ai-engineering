# Energy Aware Chat release-claim gate

Status: deterministic evidence gate for high-risk release claims.

This report controls whether the project may use any of these phrases:

1. production-ready
2. public deployment is live
3. quality improvement over plain DeepSeek
4. frontier-model superiority

These claims are blocked unless the matching evidence exists.

## Current result

- overall_ready: `false`
- claim_status: `release_claims_blocked_missing_evidence`

## Claim gates

| Claim | Decision | Missing evidence | Next action |
|---|---|---|---|
| `public deployment is live` | `blocked` | public_url, healthcheck_passed, demo_route_passed, timestamp_utc | Deploy the Docker/FastAPI app to a public host and record URL plus smoke output. |
| `quality improvement over plain DeepSeek` | `blocked` | live_provider_run, run_id, cases_total_at_least_3, plain_deepseek_score, energy_aware_score, metric_name, report_path | Run a fixed live DeepSeek benchmark and commit the result plus report. |
| `frontier-model superiority` | `blocked` | benchmark_run_id, at_least_two_frontier_models_tested, benchmark_report_path, independent_rubric, same_task_set, cost_and_latency_reported, human_review_notes_present | Do not use this claim for the final project unless a fair frontier benchmark is actually run. |
| `production-ready` | `blocked` | public_deployment_live, incident_response_documented, real_user_monitoring_documented | Treat the project as production-oriented until deployment and operations evidence exists. |

## Correct current wording

Allowed now:

```text
Energy Aware Chat is a browser-testable, production-oriented MVP candidate on the EACHAT incubator branch.
```

Blocked until evidence exists:

```text
production-ready
public deployment is live
quality improvement over plain DeepSeek
frontier-model superiority
```

## Evidence policy

The project may upgrade a claim only by updating `evals/energy_chat/release_claim_evidence_current.json`, rerendering this report, and passing the full Energy Chat validation gate plus CI.
