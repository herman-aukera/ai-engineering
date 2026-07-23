# Session 13 Plus credentialed runtime evidence

On 2026-07-16, GitHub Actions run
[`29526996872`](https://github.com/herman-aukera/ai-engineering/actions/runs/29526996872)
completed successfully at commit `80588ea4ec479b687374fbc6c21dc02795434253`.
The manually dispatched workflow used repository secrets without printing or
persisting their values.

## Proven gate

The workflow completed one bounded `LiteLLMAgentModel` turn for each configured
Plus provider and requested a remote Logfire flush:

| Tier | Provider | Model | Result | Latency | Tokens in/out | Recorded cost |
| --- | --- | --- | --- | ---: | ---: | ---: |
| flash | DeepSeek | `deepseek-v4-flash` | completed, visible output | 2,019 ms | 16 / 80 | $0.000092 |
| backup | Kimi | `moonshot/kimi-k2.5` | completed, visible output | 5,649 ms | 23 / 227 | $0.000581 |

The sanitized workflow artifact reports:

- `all_providers_completed: true`;
- `telemetry.backend: logfire`;
- `telemetry.remote_send_requested: true`;
- span name `session13.plus.live_provider`;
- no prompt, model content, credentials, token values, or secret names in the
  artifact.

The artifact remains attached to the workflow run as `live-smoke-results`.
It is not committed because it is run-specific evidence retained by GitHub.

## Hosted telemetry confirmation

The Logfire project was inspected through the authenticated Brave session on
2026-07-16. Its 15-minute live view displayed two hosted
`session13.plus.live_provider` spans from service `estimador-cag`:

- 21:11:58 local time, 2.02 seconds;
- 21:12:00 local time, 5.65 seconds.

Those durations match the sanitized provider artifact closely enough to tie
the hosted spans to this workflow execution without exposing span payloads.

## Gate isolation

The inherited Session 06 HTTP stress smoke remains available through the
manual `run_legacy_stress` workflow input. It defaults to `false`, so its
historical latency thresholds cannot obscure the Plus provider and telemetry
gate. Enabling it still produces a real failure if its own checks fail.

## Claim boundary

This proves authenticated connectivity, provider routing, normalized response
metadata, bounded live turns, a successful Logfire export request, and hosted
span ingestion. It does not prove retrieval quality, provider failover under
load, browser-to-provider integration, or production-scale latency. Those
claims require their own evidence.
