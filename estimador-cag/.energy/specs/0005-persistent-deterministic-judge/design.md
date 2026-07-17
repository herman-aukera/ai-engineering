# Design: Persistent Deterministic Judge

`JudgeState` is a `TypedDict`. Policy, evidence, proposal queue, identifiers, current candidate/decision, iteration budget, and terminal status are authoritative values. `trace` and `decisions` use explicit additive reducers.

The graph topology is:

```text
START -> initialize -> propose -> evaluate -> record
                                      ^          |
                                      | repair   | terminal or exhausted
                                      +----------+-> finalize -> END
```

The evaluate node reconstructs typed domain models and calls `evaluate_candidate`; LangGraph never reimplements decision rules. The fake actor selects the next predeclared proposal deterministically. Repair loops continue only while both proposal and iteration budgets remain.

An injected LangGraph checkpointer owns persistence. Phase 2A uses `InMemorySaver` in tests, keyed by `thread_id`. Compile-time interruption before `finalize` proves state can be inspected and resumed without repeating completed nodes.

## Failure recovery and rollback

Checkpoint resume is tested after a deliberate interrupt. Rollback removes the orchestration module and dependency; domain policy and persisted Phase 1 ledgers are unchanged.

## Security

State records `execution_performed: false`; orchestration imports no subprocess or shell API. The graph accepts model proposals only as untrusted candidate dictionaries.
