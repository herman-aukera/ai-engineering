# Session 13 Plus P7 — bounded parallel retrieval

## Contract

The mandatory Session 13 graph and its sequential `search_budgets` node remain
unchanged. The reviewed Plus graph can opt into a LangGraph 1.2.9 `Send`
fan-out with one checkpoint-safe packet per component.

Workers are bounded by an injected semaphore, emit sanitized domain events,
and return JSON-safe result envelopes. The fan-in reducer is replay-idempotent,
deduplicates stable provenance keys, and sorts evidence by original component
order followed by stable evidence identity. A missing, invalid, or failed
component records a gap without discarding successful siblings.

Rollback is configuration-only:

```text
GRAPH_RETRIEVAL_MODE=sequential
GRAPH_RETRIEVAL_MAX_CONCURRENCY=4
```

Parallel mode remains opt-in until wider persistence and production benchmarks
are complete.

## Deterministic benchmark

Run:

```bash
uv run python -m evals.session13_plus_parallel_retrieval_benchmark
```

Evidence captured on 2026-07-16 using eight components, concurrency four,
five repetitions, and a deterministic 20 ms synthetic retrieval delay:

| Metric | Result |
|---|---:|
| Sequential median | 249.115 ms |
| Parallel median | 67.022 ms |
| Speedup | 3.717× |
| Result parity | true |
| Provenance parity | true |
| Error/gap parity | true |
| Estimated retrieval cost parity | true |
| Calls across both modes | 80 |

This is course-scale wiring evidence. It proves bounded scheduling and parity
under a controlled asynchronous fake; it is not a production throughput,
database-pool, provider-rate-limit, or network benchmark. Small workloads may
not benefit once graph scheduling overhead dominates.

## Evidence

Focused contracts cover fan-out cardinality, completion-order independence,
sequential parity, stable deduplication, partial failure isolation, concurrency
bounds, worker/merge trace events, deterministic estimate parity, replay
idempotency, rollback configuration, and benchmark fields.
