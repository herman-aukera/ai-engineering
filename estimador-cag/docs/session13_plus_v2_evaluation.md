# Estimation Control Room V2 — evaluation

## Evidence layers

The V2 claim is split deliberately into deterministic contracts, local runtime
measurements, credentialed integration smoke, and production claims. Only the
first three have evidence; no provider-quality or production-scale superiority
claim is made.

## Automated contracts

- Canonical `/api/v2` lifecycle through both durable human gates.
- Rich module/task edits while Python retains ownership of arithmetic.
- Context reformulation is checkpointed and scope preserving.
- Critic findings are typed; Boss actions drive explicit graph transitions.
- Retry and fallback consume budgets; exhausted budgets route to a human.
- Provider circuit opens, blocks, half-opens after cooldown, and closes on success.
- Execution profiles change runtime budgets and provider metadata, not just labels.
- Scenario lineage, checkpoint history, sanitized audit and legacy shadow rollout remain additive.

## Required retrieval matrix

Command:

```bash
uv run python -m evals.session13_plus_parallel_retrieval_benchmark --grid --delay-ms 5 --repeats 5
```

Captured locally on 2026-07-17. Every one of the 16 cells preserved result,
provenance, error-gap and estimated-cost parity.

| Components | Concurrency | Sequential p50 ms | Parallel p50 ms | Parallel p95 ms | Speedup |
|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 6.243 | 6.576 | 6.635 | 0.949x |
| 4 | 2 | 25.984 | 13.258 | 13.446 | 1.960x |
| 4 | 4 | 25.244 | 7.156 | 7.351 | 3.527x |
| 8 | 4 | 51.341 | 13.446 | 13.517 | 3.818x |
| 8 | 8 | 52.214 | 6.775 | 6.779 | 7.707x |
| 16 | 4 | 104.340 | 26.138 | 27.364 | 3.992x |
| 16 | 8 | 104.390 | 13.471 | 13.560 | 7.749x |

This is controlled course-scale scheduling evidence. It excludes database-pool,
network, provider-rate-limit and production-load effects. The one-component
result also demonstrates why concurrency is bounded and profile controlled.

## Release gates

V2 remains additive and the pull request remains draft. Promotion requires green
CI, a PostgreSQL close/reopen proof for the reviewed V2 graph, a full browser
journey, and credentialed provider/Logfire smoke. Legacy remains available for
rollback; there is no silent fallback or double execution in the V2 route.
