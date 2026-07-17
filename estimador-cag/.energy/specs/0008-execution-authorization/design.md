# Design: Revision-Guarded Human Execution Authorization

## Architecture

```text
human-required ExecutionPlan
  -> execution_authorization interrupt
  -> strict ExecutionAuthorization
  -> deterministic verifier
       -> deny with typed reasons
       -> consume exact one-time authority
  -> AuthorizationReceipt
  -> normalized authorization evidence
  -> existing deterministic decider reevaluation
  -> finalize without execution
```

Clarification/escalation review and execution authorization are different graph nodes and different contracts. A prior acknowledgement cannot authorize a command.

## Authority model

An authorization is valid only when all of these match current authoritative state:

- actor is explicitly trusted;
- plan hash is exact;
- expected and accepted revision equal the current revision;
- executable, working directory, mode, timeout, and output budget match exactly;
- creation time is not in the future;
- expiry is still valid;
- nonce has not been consumed;
- authorization has not already been consumed;
- rollback acknowledgement is true;
- the plan is actually classified `human_required`;
- the plan has not been executed.

No soft score can compensate for a failed authority invariant.

## Persistence and replay

The graph interrupt contains JSON-safe plan identity, exact scope, revision, and allowed actions. The graph receives `authorization_now` as explicit state so replay does not depend on a new wall-clock read. SQLite persists the interrupt and resumes on the same thread.

On successful consumption:

- the authorization is marked consumed;
- the raw nonce is replaced with `[CONSUMED]` in graph state;
- only the nonce hash is retained for replay protection;
- an immutable receipt is stored;
- a trusted authorization evidence record is appended;
- `execution_authorized=true` and `execution_performed=false` remain distinct facts.

## CLI

The verifier CLI accepts existing plan, authorization, and context JSON. `verify` is non-mutating. `consume` writes consumed authorization, updated replay context, and receipt to a caller-selected output directory. It never invokes a tool.

## Migration and compatibility

The change is additive. Existing graph invocations without human-required command plans do not enter the new interrupt. Existing clarification/escalation interrupts remain unchanged. Existing SQLite saver tables require no schema migration because LangGraph state fields are additive JSON-compatible values.

## Rollback

Revert the authorization module, CLI, graph node, tests, and Spec 0008 packet. Spec 0007 planning and fake/dry-run evidence remain usable. No real execution or external side effect needs reversal.

## Future boundary

A real tool adapter may consume only a previously verified authorization receipt and must revalidate plan hash, revision, scope, expiry, nonce consumption, root boundaries, and execution state immediately before process start. That adapter is not part of this spec.
