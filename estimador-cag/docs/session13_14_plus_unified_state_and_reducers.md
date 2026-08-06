# Session 13 + 14 Plus — Unified State and Reducers

## State hierarchy

```text
EstimationGraphState
└─ ReviewedEstimationGraphState
   └─ Session14EstimationGraphState
      └─ Session14PlusEstimationGraphState
         └─ UnifiedEstimationGraphState
```

The hierarchy is an implementation reuse mechanism. It does not imply that checkpoints from an older graph version can be loaded into a newer graph.

## Field ownership

| Field family | Owner | Authority |
|---|---|---|
| transcript/requirements/components | structure nodes | source request and typed extraction |
| budget matches/evidence refs | retrieval nodes | retrieved evidence |
| component estimates/estimate | Python estimator | authoritative arithmetic |
| validation/status | deterministic validators | coherence state |
| structure review | structure human gate | structure edits only |
| parallel retrieval envelopes | retrieval coordinator | worker results |
| Critic report | typed Critic | advisory findings |
| Boss decision/route | deterministic Boss policy | bounded recommendation |
| recovery fields | recovery service | attempt/results under budgets |
| provider circuits/execution budgets | reviewed runtime | operational limits |
| stage route events | Session 13 routing runtime | provider route evidence |
| supervisor route events | Session 14 supervisor | supervised specialist audit |
| unified route events | unified supervisor | canonical route authority |
| agent contributions | least-privilege specialists | action/privilege audit |
| competition candidates | competition service | immutable alternatives |
| Energy snapshot | Python Energy policy | hard/soft constraint result |
| compacted context | context service | derived handoff only |
| human review actions | Session 14 human gate | final approve/adjust/reject authority |
| proposal | proposal node | final product projection |

## Reducer rules

### Delta-only rule

A node writing to an accumulator returns only newly generated entries. It must not return the previously accumulated list.

### Stable identity and order rule

Every replay-sensitive reducer uses either an explicit record ID or a deterministic semantic identity. Identical replay is idempotent and conflicting reuse fails closed. Reducers retain first-seen order so evidence ranking, diagnostic order and graph chronology remain stable across checkpoint replay.

### `budget_matches`

Reducer:

```text
merge_budget_matches
```

Identity:

- explicit `match_id` when supplied;
- otherwise a deterministic identity derived from component, budget, reference component, source document, source chunk and retrieval method.

A replay with the same evidence is deduplicated. Reusing the same identity with different hours, distance, score or other semantics raises a conflict. First-seen retrieval rank is retained.

### `errors`

Reducer:

```text
merge_graph_issues
```

Identity:

- explicit `issue_id` when supplied;
- otherwise deterministic `node + code` identity.

The same issue may replay once. A changed message or severity under the same identity fails closed. First-seen diagnostic order is retained.

### `trace_events`

Reducer:

```text
merge_trace_events
```

Identity:

- explicit `event_id` when supplied;
- otherwise deterministic identity from node, event type, evidence references and state-delta keys.

This replaces the former blind append behavior. Trace deltas remain sanitized and preserve first-seen execution chronology.

### `stage_route_events`

The inherited provider-route accumulator remains delta-only and is generated from strict `StageRouteDecision` payloads. It is not the canonical graph-transition ledger; `route_events` and `unified_route_events` own transition authority. A dedicated semantic-ID reducer remains bounded follow-up debt because repeated identical provider-stage decisions are currently prevented by completed-node terminal guards rather than reducer-level identity.

### `parallel_retrieval_results`

Reducer:

```text
merge_parallel_retrieval_results
```

Identity: `component_id`.

Behavior:

- deduplicates replayed worker results;
- sorts by component index and ID;
- later identical replay does not multiply evidence.

### `route_events`

Reducer:

```text
merge_supervisor_route_events
```

Identity: `route_event_id`.

Behavior:

- identical replay deduplicates;
- conflicting reuse fails closed;
- ordering uses sequence and ID.

### `unified_route_events`

Reducer:

```text
merge_unified_route_events
```

Identity: `event_id`.

Each event records only destination, reason code and sanitized summary. `routing_steps` is synchronized with the unified route sequence so inherited Session 14 action auditing remains valid.

### `agent_contributions`

Reducer:

```text
merge_agent_contributions
```

Identity: `contribution_id`.

Duration differences do not turn an otherwise identical replay into a semantic conflict. Different action, privilege, state delta or result identity fails closed.

### `human_review_actions`

Reducer:

```text
merge_session14_human_review_actions
```

Identity: `idempotency_key`.

- identical duplicate is idempotent;
- different action under the same key raises conflict;
- expected revision protects stale decisions.

### `plus_context_compaction_events`

Identity: `event_id` derived from estimation ID and source revision.

- identical replay deduplicates;
- conflicting event identity fails closed;
- compact context itself is replacement state, not an accumulator.

## Unified phase flags

The unified supervisor routes from explicit completion flags:

```text
unified_structure_completed
unified_estimation_completed
plus_competition_completed
unified_reliability_completed
unified_review_policy_completed
unified_boss_action_completed
unified_coherence_completed
unified_proposal_completed
```

Recovery invalidates only the downstream derived phases that must be recalculated:

- competition;
- reliability;
- Critic/Boss review;
- coherence.

It preserves structure, evidence and the authoritative estimate/recovery record.

## Recovery budgets

```text
unified_recovery_cycles
unified_max_recovery_cycles
```

The default maximum is two. Exhaustion forces human review after coherence validation.

## Checkpoint contract

Unified threads use:

```text
graph_name: session13_14_plus_unified_graph
graph_version: session13_14_plus.unified.v1
thread_id: estimate:<estimation_id>
```

Resume uses the same thread and `Command(resume=...)`. Completed duplicate execution returns stored terminal state rather than appending historical reducer values.

## Context source of truth

`plus_compacted_context` is replaced with a newly derived projection when its authoritative source revision changes. The fingerprint does not include creation time, so equivalent source state yields stable identity.

Stale compacted context must be rejected before provider switching or resume-sensitive operations.

## Compatibility boundary

No automatic state converter exists between reviewed, supervised, Plus and unified graph checkpoints. Existing threads remain on their originating graph. A future converter would require:

1. explicit source/target versions;
2. field-level compatibility mapping;
3. reducer replay tests;
4. rollback;
5. PostgreSQL migration evidence;
6. explicit authorization.
