# Requirements: Persistent Deterministic Judge

## Operator problem

The deterministic judge can evaluate one candidate, but it lacks an explicit graph topology, durable thread semantics, bounded routing, checkpoint resume, and a domain trace.

## Functional requirements

- Use LangGraph `StateGraph` with typed JSON-compatible shared state.
- Separate authoritative fields from reducer-backed accumulator fields.
- Preserve graph, policy, spec, run, and thread identifiers.
- Use a deterministic proposal queue; no provider or shell execution.
- Route through initialize, propose, evaluate, record, and finalize nodes.
- Delegate all candidate authorization to the existing Python decider.
- Bound repair iterations and surface budget exhaustion.
- Persist every step through an injected checkpointer.
- Support interruption before a node and resume on the same thread.
- Keep checkpoint threads isolated and produce a deterministic domain trace.

## Hard constraints

- No shell command, tool execution, provider call, or duplicated decision policy.
- At least one proposal and one maximum iteration are required.
- In-memory persistence is for deterministic CI and development only.

## Non-goals

- Production database persistence, controlled execution, live actors, and human approval UI.
