# Energy Aware Chat graph-state contract

Schema version: `1.0.0`

Contract version: `1.0.0`

The contract is product-local and independently testable. It deliberately does not import LangGraph. Unsupported schema versions fail closed; migrations will be additive and explicit when a v2 schema is justified.

## Ownership and reducer matrix

| Field | Intended writer | Reader | Persistence/redaction | Update rule |
|---|---|---|---|---|
| identity and version fields | request initializer | every node | persisted; identifiers are opaque | immutable |
| `user_request`, `mode`, `constraints` | interpretation/policy nodes | retrieval, generation, decision | persisted; redact before construction | replace |
| `evidence_refs` | evidence node | generation, critics, card | references only; no sensitive bodies | append unique when wired |
| `candidate_versions` | generation/repair nodes | critics, score, decision | persisted; user-visible answer text | append by `candidate_id` |
| `active_candidate_id` | generation/repair nodes | critics, score, decision | persisted | replace; must reference history |
| `critic_findings` | critic panel | score, decision, repair | persisted; safe summaries only | append when IDs are added in a later contract |
| `energy_scores` | energy node | decision, card | persisted | append by `score_id` |
| `decision_outcomes` | deterministic decider | ledger, card, terminal routing | persisted | append by `decision_id` |
| `repair_requests` | deterministic decider | repair node | persisted | append by `repair_id` |
| `trace_events` | every node | audit/observability | safe payloads only; no hidden reasoning | append by `event_id` |
| `errors` | failing node boundary | retry/terminal routing | safe projection, no secrets | append by `error_id` |
| `final_answer`, `energy_card`, `status` | terminal projection nodes | API/UI | user-safe | replace |

## Reducer invariant

`append_unique_records` accepts a repeated record with identical content as an idempotent retry. It raises on the same ID with different content, preventing replay from rewriting history. Reducers are not applied to singular authoritative fields.

## Serialization and fixture

`serialize_graph_state` emits canonical sorted compact JSON. `deserialize_graph_state` accepts only schema `1.0.0`. The persisted compatibility fixture is `tests/fixtures/energy_chat_graph_state_v1.json`.

This milestone proves the contract only. Checkpoint storage, graph reducers, migrations, retention enforcement, and resume behavior remain future milestones.
