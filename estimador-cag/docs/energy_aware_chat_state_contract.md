# Energy Aware Chat graph-state contract

Schema version: `1.0.0`

Contract version: `1.0.0`

The contract is product-local and independently testable. It deliberately does not import LangGraph. Unsupported schema versions fail closed. New Milestone 9 fields are additive v1 fields; a breaking invariant requires a new schema and explicit migration.

## Ownership and reducer matrix

| Field | Intended writer | Reader | Persistence/redaction | Update rule |
|---|---|---|---|---|
| identity and version fields | request initializer | every node | persisted; opaque IDs | immutable |
| `user_request`, `mode` | `interpret_request` | retrieval, generation, decision | persisted later; redact before construction | replace |
| `constraints`, `policy_version`, `request_policy` | policy node | critics, score, decision | safe rules/constraints only | replace |
| `source_need`, `project_rag` | evidence nodes | routing, generation, attribution | no external body fabrication | replace |
| `evidence_refs` | evidence/generation nodes | critics, ledger, cards | references only | append unique |
| `candidate_versions` | generation/repair | critics, score, decision, finalization | visible answer text | append by `candidate_id` |
| `active_candidate_id` | generation/repair | evaluation and finalization | must reference retained history | replace |
| `provider_metrics` | generation | budgets and audit | no prompts or secrets | append by `provider_call_id` |
| `critic_panels` | critic node | score, repair and ledger | safe findings | append by `panel_id` |
| `critic_findings` | critic node | current UI projection | safe active findings | replace |
| `energy_scores` | score node | decision, ledger and cards | numeric and typed findings | append by `score_id` |
| `decision_outcomes` | decision node | routing, ledger and projection | safe reasons | append by `decision_id` |
| `repair_requests` | repair planner | repair and ledger | no hidden reasoning | append by `repair_id` |
| `repair_results` | repair finalizer | ledger and cards | energy before/after/outcome | append by `result_id` |
| `retry_budget`, `cost_budget` | repair/generation | routing and audit | numeric totals | replace |
| `trace_events` | every node | audit/observability | allow-listed payloads | append by `event_id` |
| `decision_ledger_entries` | `record_decision` | projection, future audit/API | authoritative links; no evidence bodies | append by `ledger_entry_id` |
| `errors` | failing boundaries | routing/API | sanitized | append by `error_id` |
| `final_answer` | final projection | API/UI | user-safe | replace |
| `energy_card` | final projection | legacy compatibility | user-safe | replace |
| `energy_card_v2` | final projection | API/UI | user-safe authoritative projection | replace |
| `final_projection` | final projection | API/UI | no secrets or hidden reasoning | replace |
| `status` | current node | graph router/API | safe enum | replace |

## Reducer invariant

`append_unique_records` accepts a repeated record with identical content as an idempotent retry. It raises on the same ID with different content. Reducers are not applied to singular authoritative fields.

The new Decision Ledger reuses the same invariant through `ledger_entry_id`.

## Serialization and fixture

`serialize_graph_state` emits canonical sorted compact JSON. `deserialize_graph_state` accepts only schema `1.0.0`.

The compatibility fixture remains:

```text
tests/fixtures/energy_chat_graph_state_v1.json
```

Canonical serialization uses fields explicitly present in the loaded fixture, so new optional v1 fields do not silently rewrite the original fixture.

## Node-delta discipline

Each node validates the complete state through `EnergyChatGraphState`, delegates to product-local deterministic logic, and returns only fields it owns.

Identity fields cannot be rewritten by node deltas.

## Evidence routing

Three routes remain authoritative:

- `skip`;
- `retrieve_project`;
- `external_required`.

The external route stops with `awaiting_evidence`; it does not fabricate candidate, ledger, Energy Card, or final answer records.

## Candidate providers and budgets

Providers receive normalized request, mode, constraints, references, optional project retrieval result, and output limit. They receive no credential fields through graph state.

Provider metrics record safe facts: provider, model, tier, tokens, cost, latency, retries, fallback and finish reason.

Retained candidates and provider-call IDs make replay idempotent.

## Evaluation linkage

Critic panels, energy scores and decisions must reference the active candidate. Scores also reference the active policy version.

Stale or missing linkage fails closed.

## Bounded repair

A repair request links source decision and source/target candidate IDs. The applied repair creates a new candidate and consumes one retry. The complete evaluation sequence reruns.

Repair results record:

- energy before;
- energy after;
- `improved`, `no_improvement`, `budget_exhausted`, or `not_repairable`.

## Decision Ledger

Each `DecisionLedgerEntry` contains:

- schema version and stable ledger ID;
- deterministic sequence;
- thread/request/trace IDs;
- candidate, panel, score and decision IDs;
- policy version and rule ID;
- disposition and user-safe reason;
- energy before/after/delta;
- categorized violations;
- evidence references and integrity metadata;
- provider-call IDs;
- repair request/result IDs;
- limitations.

Every retained authoritative decision is recorded, including the initial repair decision and the final post-repair decision.

## Evidence integrity metadata

The metadata contains:

- exact evidence reference;
- `sha256:` hash of that reference string;
- trust status;
- freshness status;
- redaction status;
- `body_included=false`.

It must not be described as a content hash for an evidence body.

## Energy Card v2 and final projection

Energy Card v2 is derived from the final ledger entry and exposes:

- decision and policy rule;
- hard and soft findings;
- energy before/after/delta;
- repair attempts/outcomes;
- evidence references;
- limitations.

The final projection includes the safe answer and execution markers.

For rejected candidates, the unsafe candidate body is not emitted. Refuse, clarify and escalate use the deterministic policy reason.

## Persistence boundary

The compiled graph still has no checkpointer. Replay safety is in-memory wiring proof only.

Before real persistence:

1. freeze fixtures;
2. add checkpointer tests;
3. define retention and redaction enforcement;
4. add migration and rollback;
5. prove restart and human-resume behavior.
