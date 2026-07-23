# Session 14 multi-agent architecture

## Purpose

Session 14 reorganizes the inherited estimation workflow as a supervised
LangGraph without replacing the business contract or the Session 13
PostgreSQL checkpointer.

## Control flow

```text
START
  -> supervisor
     -> requirements_extractor -> supervisor
     -> budget_searcher        -> supervisor
     -> estimate_generator     -> supervisor
     -> coherence_validator    -> supervisor
     -> human_review_gate
          -> interrupt
          -> approve / adjust / reject
     -> finalize
  -> END
```

The supervisor is implemented directly with `StateGraph` and typed
`Command` returns. Python owns prerequisites, route allow-lists, hop limits,
reliability policy, authoritative arithmetic, and human-review enforcement.
The graph does not use `create_supervisor` or a hidden routing abstraction.

### Hybrid routing boundary

The composition root injects a provider-neutral `SupervisorRouteProposer`.
The production adapter asks the configured structured LiteLLM tier for a
`SupervisorRouteProposal`; deterministic tests inject a fake or omit the port.
The model receives only:

- a bounded `SupervisorStateDigest`;
- the destinations Python has declared legal for that state.

It never receives the transcript, business tools, provider credentials, raw
graph state, or execution authority. Python validates the typed proposal again
before returning `Command(goto=...)`. An illegal proposal, provider failure, or
missing proposer falls back to the deterministic dependency policy. The hop
budget preempts the model entirely.

Each replay-safe route event and node span records:

- `route_source`: `model`, `deterministic_fallback`,
  `deterministic_policy`, or `budget_limit`;
- the proposed destination, when one exists;
- the closed set of valid candidates;
- a bounded fallback reason code, never provider error text.

Most dependency stages intentionally expose one safe candidate. A clean,
validated terminal state exposes two safe graph paths—direct finalization or
the deterministic review gate, which rechecks the policy and falls through
without pausing. This gives the router a real runtime path choice without
allowing it to skip prerequisites or mandatory review.

## Shared-state contract

`Session14EstimationGraphState` extends the Session 13 state with:

- supervisor identity and route metadata;
- replay-safe `route_events` and `agent_contributions` reducers;
- reliability signals and human-review state;
- revision and idempotency metadata;
- partial specialist contributions.

Runtime clients, database connections, checkpointers, secrets, prompts, and
hidden reasoning are excluded from graph state.

### Level 3 action audit

Each specialist contribution is also a structured action-audit envelope. It
records:

- the stable contribution ID, agent, sequence, and action;
- the authorized business tool, or `null` for tool-free model work;
- `allowed`, `not_applicable`, or `denied` privilege provenance;
- `succeeded`, `denied`, or `failed` execution status;
- validated input **shape** as key-to-type metadata, never values;
- a stable checkpoint result reference and measured duration;
- the sanitized summary and state-delta keys already used by Session 14.

The authorization check runs before the operation. A denial emits the same
sanitized schema to structured logs and never reaches the worker operation. A
failed action reveals only the exception class, not its message. Successful
records persist through the replay-safe reducer and appear in the public
response. An identical replay may have a different measured duration; the
reducer preserves the first observation while still rejecting conflicts in
every semantic field.

Legacy checkpoints that predate Level 3 receive conservative defaults at the
public contract boundary. Raw arguments are forbidden by the strict response
schema.

## Agents and authority

| Agent | Business-tool privilege | Responsibility |
| --- | --- | --- |
| `requirements_extractor` | none | Extract and classify requirements |
| `budget_searcher` | `search_budgets` | Retrieve historical evidence |
| `estimate_generator` | `calculate_estimate` | Derive component hours |
| `coherence_validator` | `validate_estimate` | Validate reliability |
| `supervisor` | none | Route only |

The privilege registry is static and server-owned. A transcript cannot grant
an agent another tool.

## Human-in-the-loop boundary

The graph pauses when confidence is below the configured threshold, the
estimate is outside its historical range, or no historical precedent exists.
The interrupt payload exposes identifiers, revision, reason codes, a compact
estimate summary, confidence, range status, evidence count, findings, and
allowed actions. It excludes the transcript and infrastructure secrets.

`approve`, `adjust`, and `reject` resume the original thread. Adjustments are
recalculated in Python. Revision checks prevent stale decisions; idempotency
keys make exact retries safe and reject conflicting reuse.

## Persistence and observability

`AsyncPostgresSaver` persists the pause. A stable thread ID derived from the
estimation ID reconnects a later request to the same checkpoint. Root graph
spans and node spans use sanitized attributes; the domain trace separately
records route decisions, specialist contributions, pause, and resume. Worker
node spans project the safe action, tool, privilege decision, execution status,
validated input keys, result reference, and duration without summaries or
input values.

## Claim boundary

This architecture proves a cooperative hybrid supervisor/workers graph with
guarded model proposals, replay-visible deterministic fallbacks, and durable
human control. It also proves the local Level 3 privilege/action-audit contract.
Hosted evidence must still show the production adapter and these action fields
in the ORBITA lifecycle. It does not claim that multi-agent orchestration is
universally better than a linear graph, that provider routing is calibrated,
or that this coursework system is production-ready.
