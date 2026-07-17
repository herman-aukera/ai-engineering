# Requirements: SQLite Persistence and Human Interrupts

## Operator problem

In-memory checkpoints prove graph semantics but cannot survive process restart. Static breakpoints also do not provide a typed reason or controlled human response for clarify and escalate routes.

## Functional requirements

- Persist graph checkpoints in a SQLite database behind the existing injected checkpointer interface.
- Create or migrate saver tables idempotently.
- Recover completed state after the graph and database connection restart.
- Interrupt with a JSON-safe payload for escalation and missing-evidence clarification.
- Resume on the same thread with a validated human action.
- Preserve the original domain decision and record the human response without executing anything.
- Provide run, inspect, and resume CLI commands backed by the same SQLite database.
- Keep Python 3 support within the dependency-compatible range `>=3.11,<3.14`.

## Hard constraints

- No shell/tool execution, provider calls, or automatic approval.
- No complex or unserializable interrupt payloads.
- No in-memory-only claim of restart durability.
- Human review cannot rewrite the deterministic decision silently.

## Non-goals

- Production Postgres persistence, multi-user authorization, or execution approval.
