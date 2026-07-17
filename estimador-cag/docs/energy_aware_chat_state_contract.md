# Energy Aware Chat graph-state contract

Schema version: `1.0.0`

Contract version: `1.0.0`

The contract is product-local and independently testable. It deliberately does not import LangGraph. Unsupported schema versions fail closed; migrations will be additive and explicit when a v2 schema is justified.

## Ownership and reducer matrix

| Field | Intended writer | Reader | Persistence/redaction | Update rule |
|---|---|---|---|---|
| identity and version fields | request initializer | every node | persisted; identifiers are opaque | immutable |
| `user_request`, `mode` | `interpret_request` | retrieval, generation, decision | persisted; redact before construction | replace |
| `constraints`, `policy_version` | `load_policy_and_constraints` | critics, score, decision | persisted; redact before construction | replace |
| `source_need` | `determine_evidence_need` | evidence routing, decision | safe classification only | replace |
| `project_rag` | `route_evidence` | generation, attribution | project corpus content only | replace |
| `evidence_refs` | `route_evidence` | generation, critics, card | references only; no sensitive bodies | append unique |
| `candidate_versions` | `generate_candidate`, later repair | critics, score, decision | persisted; user-visible answer text | append by `candidate_id` |
| `active_candidate_id` | generation/repair nodes | critics, score, decision | persisted | replace; must reference history |
| `provider_metrics` | `generate_candidate` | budgets, observability, audit | persisted; no prompts or secrets | append by `provider_call_id` |
| `critic_panels` | `run_critic_panel` | score, repair, audit | persisted; candidate-linked safe findings | append by `panel_id` |
| `critic_findings` | `run_critic_panel` | current score/UI projection | persisted; safe summaries only | replace with active panel |
| `energy_scores` | `calculate_energy` | decision, card | persisted; candidate and policy linked | append by `score_id` |
| `decision_outcomes` | `decide_candidate` | ledger, card, terminal routing | persisted; candidate and score linked | append by `decision_id` |
| `repair_requests` | deterministic decider | repair node | persisted | append by `repair_id` |
| `trace_events` | every node | audit/observability | safe payloads only; no hidden reasoning | append by `event_id` |
| `errors` | failing node boundary | retry/terminal routing | safe projection, no secrets | append by `error_id` |
| `final_answer`, `energy_card`, `status` | terminal projection nodes | API/UI | user-safe | replace |

## Reducer invariant

`append_unique_records` accepts a repeated record with identical content as an idempotent retry. It raises on the same ID with different content, preventing replay from rewriting history. Reducers are not applied to singular authoritative fields.

## Serialization and fixture

`serialize_graph_state` emits canonical sorted compact JSON. `deserialize_graph_state` accepts only schema `1.0.0`. The persisted compatibility fixture is `tests/fixtures/energy_chat_graph_state_v1.json`.

New optional v1 fields are additive. Canonical serialization uses the fields that were explicitly present, so loading and saving the original v1 fixture does not silently inject later optional fields. A breaking field or invariant change requires a new schema version and explicit migration.

This milestone proves the contract only. Checkpoint storage, graph reducers, migrations, retention enforcement, and resume behavior remain future milestones.

## Provider-free node deltas

`InterpretationDelta` owns only normalized request text, explicit mode, status, and one safe trace event. `PolicyConstraintsDelta` owns only policy version, normalized constraints, status, and one safe trace event. Identity fields cannot be supplied through either strict delta contract.

The application functions validate the complete resulting state. A replay against an already-applied state returns the same trace event ID and content, so the append-only reducer treats it as an idempotent retry.

## Evidence routing

`EvidenceNeedDelta` reuses the current deterministic source classifier. `EvidenceRoutingDelta` has three explicit routes:

- `skip` when sources are unnecessary or trusted evidence already exists;
- `retrieve_project` for missing project evidence using the deterministic committed-source retriever;
- `external_required` for missing current/external evidence, leaving status `awaiting_evidence` without fabricating references.

## Candidate providers and budgets

`CandidateProviderRequest` carries the normalized request, mode, constraints, evidence references, optional project retrieval result, and maximum output tokens. It contains no credentials. Providers return `CandidateGenerationResult` with a visible answer, attributable references, and `ProviderMetrics`.

The deterministic adapter preserves the existing local draft behavior. The baseline adapter wraps the existing DeepSeek/Kimi fallback-capable seam and measures elapsed latency. Before a delta is applied, the candidate node enforces output-token, cost, latency, and retry limits. Each candidate stores its `provider_call_id`, linking it to exactly one metrics record.

Candidate and provider-call IDs are deterministic for request/version. When both records already exist, replay returns them without invoking the provider again.

## Critic, score, and decision linkage

`run_critic_panel` reconstructs the existing `EnergyChatRequest` from the active immutable candidate and delegates to the current deterministic critics and source guard. `calculate_energy` accepts only a panel for the active candidate and records the policy version. `decide_candidate` accepts only a score for the active candidate and active policy, then delegates to the existing deterministic decider.

Panel, score, and decision IDs are deterministic. Identical replay reuses retained records; conflicting content is rejected by append-only reducers. Trace payloads include IDs, counts, energy, and disposition, not hidden reasoning or full candidate text.
