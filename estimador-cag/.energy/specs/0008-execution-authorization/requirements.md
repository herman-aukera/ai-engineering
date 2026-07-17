# Requirements: Revision-Guarded Human Execution Authorization

## Operator problem

A command plan classified as `human_required` must not become executable because a user previously acknowledged a clarification or because an adapter claims approval. Authorization must be explicit, exact, scoped, time-bounded, revision-guarded, one-time, replay-safe, and independently verified.

## Functional requirements

- Define strict typed contracts for authorization scope, authorization input, verification context, decision, and consumption receipt.
- Bind authorization to the exact execution-plan SHA-256 hash.
- Require expected and accepted revisions to equal the current authoritative revision.
- Require the actor to be present in an explicit trusted-actor set.
- Require timezone-aware creation and expiry timestamps.
- Reject future-dated or expired authorization.
- Require a unique nonce and persist only its hash in replay state and receipts.
- Reject an already consumed authorization or previously consumed nonce.
- Require exact executable, working-directory, mode, timeout, and output-budget scope equality.
- Require a non-empty reason and rollback acknowledgement.
- Verify and consume authorization without executing a command.
- Produce a replay-safe receipt with `execution_performed=false`.
- Expose a CLI for verify and consume operations.
- Add a dedicated LangGraph interrupt for execution authorization, separate from clarification/escalation review.
- Persist the interrupt and resume across SQLite process restart.
- Sanitize the raw nonce before storing authorization state.
- Add normalized authorization evidence and reevaluate through the existing deterministic decider.

## Hard constraints

- Human acknowledgement is not execution authorization.
- Authorization never changes the candidate decision silently.
- Authorization never executes a command.
- Wrong plan hash, stale revision, wrong actor, expiry, replay, scope mismatch, or missing rollback acknowledgement must fail closed.
- A non-human-gated plan cannot consume execution authorization.
- No model, tool adapter, UI, or executor may create trusted authority for itself.
- No raw secret, environment mapping, hidden chain of thought, or provider transcript may enter authorization state.
- No auto-commit, auto-push, force-push, merge, reset, clean, or checkout execution path is added.

## Non-functional requirements

- All records are strict JSON-serializable Pydantic models.
- Verification is deterministic for the supplied plan, context, authorization, and clock.
- The graph receives an explicit replay-safe authorization clock rather than calling wall-clock time during replay.
- Tests cover valid consumption, wrong hash, stale revision, untrusted actor, expiry, replay, scope mismatch, missing authorization, timestamp validation, CLI behavior, SQLite restart, cancellation, and no-execution invariants.
- Deterministic CI remains keyless, network-free, and subprocess-free for EACODE authorization logic.

## Non-goals

- Real shell or tool execution.
- OS sandboxing.
- Production identity provider integration.
- Multi-user authorization service.
- Provider-backed actor generation.
- Automatic repository mutation.
