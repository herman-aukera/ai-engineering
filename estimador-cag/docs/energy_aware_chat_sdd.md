# Energy Aware Chat software design description

## 1. Document control

| Field | Value |
|---|---|
| Product | EACHAT — Energy Aware Chat |
| Repository | `herman-aukera/ai-engineering` |
| Branch | `EACHAT` |
| PR | #5, open, unmerged |
| Milestone 9 code checkpoint | `dd79bf4befd625ce673242e843c14a023c0862d6` |
| Milestone 9 deterministic tests | 519 passed |
| Provider/context architecture checkpoint | `57438c5fa4068bf7d4fab1e9d10d5527128a45ca` |
| Latest exact-head CI | runs `29689906124` and `29689906247`, success |
| SDD version | 1.1.0 |
| Claim status | `release_claims_blocked_missing_evidence`; `measurement_only_no_quality_claim` |

This SDD is the canonical engineering control document for EACHAT. Detailed state, policy, provider/context and architecture documents remain supporting specifications.

## 2. Product definition and boundary

EACHAT is a general-purpose Energy Aware Chat application. It evaluates answer candidates against explicit hard and soft constraints before presenting a final answer. Deterministic Python owns evidence sufficiency, authoritative energy, budgets, and final disposition. Models may propose candidates or observations but cannot override hard constraints.

Supported dispositions:

```text
accept | repair | clarify | reject | refuse | escalate
```

EACHAT owns chat interpretation, grounding, candidate generation, critics, scoring, repair, clarification, refusal, escalation, provider orchestration, chat persistence, context-compaction roadmap, Energy Cards, API, UI, and chat evaluations.

EACHAT does not own shell execution, repository mutation, patch application, IDE adapters, EACODE rollback, estimation-specific Session 13 semantics, or speculative shared-core runtime contracts.

Portfolio relationship:

- EACODE is a separate local coding-governance layer for specifications, patches, tests and commands used by Claude Code, Cline, Aider and similar clients.
- Session 13 Plus is coursework and a source of graph, critic/boss, persistence, human-gate and observability patterns; its estimation arithmetic remains coursework-local.
- EACORE may remain documentation and shared architecture until two independently proven products justify runtime extraction.

## 3. Current architecture

### 3.1 Implemented internal graph

```text
START
→ interpret_request
→ load_policy_and_constraints
→ determine_evidence_need
    → skip_evidence
    → retrieve_project_evidence
    → await_external_evidence → END
→ generate_candidate
→ run_critic_panel
→ calculate_energy
→ decide_candidate
    → plan_repair → apply_repair → full reevaluation → finalize_repair
    → record_decision
→ build_final_projection
→ END
```

### 3.2 Current public runtime

The public deterministic and live chat routes still call the legacy sequential agents. The graph is internally executable and CI-validated but is not yet the public API source of execution truth.

### 3.3 Target provider/context front end

The provider-neutral routing contract is documented, not yet fully implemented:

```text
provider: auto | deepseek | kimi | openai
effort: fast | balanced | max
context: minimal | balanced | max
orchestration: single | critic | committee | adaptive
```

Current intended policy:

- DeepSeek is the cost-effective default.
- Kimi K3 is the user-preferred quality candidate after account-visible API capability verification; it is not benchmark-proven best.
- GPT-5.6 is the premium option.
- reasoning effort and context compaction are independent selectors;
- automatic routing, committee/adaptive orchestration and provider escalation require dedicated budgets, tests and fixed benchmarks.

Canonical provider/context documents:

```text
../ENERGY_AWARE_PROVIDER_ROUTING_README.md
docs/energy_aware_chat_provider_context_spec.md
docs/energy_aware_chat_milestone_10_provider_context_addendum.md
../docs/ENERGY_AWARE_PORTFOLIO_README.md
```

## 4. Implemented requirements

| Capability | Status | Evidence level |
|---|---|---|
| Strict product-local graph state v1 | implemented | L2 remote CI |
| Replay-safe reducers and canonical serialization | implemented | L2 |
| Interpretation and versioned request policy | implemented | L2 |
| Explicit evidence routing | implemented | L2 |
| Deterministic and provider-backed candidate adapter contracts | implemented | L2 deterministic; live graph not yet proven |
| Provider token/cost/latency/retry budgets | implemented | L2 |
| Candidate-linked critic panels | implemented | L2 |
| Candidate- and policy-linked energy scores | implemented | L2 |
| Six deterministic dispositions | implemented | L2 |
| One bounded repair with full reevaluation | implemented | L2 |
| Append-only Decision Ledger | implemented in graph | L2 |
| Evidence reference SHA-256, trust, freshness, and redaction metadata | implemented, reference-only | L2 |
| Energy Card v2 | implemented in graph | L2 |
| Safe final-answer projection | implemented in graph | L2 |
| Rejected candidate body suppression | implemented | L2 |
| No-external-provider and no-tool execution markers | implemented | L2 |
| Provider/context/multi-agent architecture | documented | L2 documentation CI; runtime pending |

## 5. Partial requirements

| Capability | Implemented portion | Missing proof or behavior |
|---|---|---|
| API migration | graph and projection contracts exist | graph-backed deterministic/live endpoints, feature flag, rollback and parity |
| Persistence | state is checkpoint-safe in shape | saver, resume, restart, migration and retention |
| Human control | clarify/escalate dispositions exist | interrupts, revision-guarded actions, trusted actor and resume |
| Evidence | references and project retrieval | evidence bodies, content hashes, verification, freshness enforcement and citation validation |
| Observability | typed domain events and provider metrics | node spans, operational metrics, checkpoint telemetry and dashboards |
| UI | legacy demo and Streamlit | graph-backed Control Room, provider/effort/context selectors, thread history, human controls and browser proof |
| Live providers | existing DeepSeek/Kimi seam and provider-neutral architecture | graph-backed DeepSeek proof, verified Kimi K3 model discovery/adapter, GPT-5.6 adapter and sanitized live evidence |
| Context management | profile and snapshot architecture | compaction implementation, persistence, drift tests, rollback and UI control |
| Multi-agent | generator/critic graph pattern and documented modes | distinct single/committee/adaptive execution, budgets, quorum and benchmark evidence |
| Evaluation | deterministic repair benchmark exists | quality rubric and controlled cross-provider/orchestration comparison |

## 6. Data and state contracts

The graph state uses schema and contract version `1.0.0`. Milestone 9 fields are additive:

- `decision_ledger_entries` — append by `ledger_entry_id`;
- `energy_card_v2` — singular replacement;
- `final_projection` — singular replacement.

Future routing/context contracts must be additive or versioned and should record:

- requested and served provider/model profiles;
- capability-catalog version;
- effort, context and orchestration profiles;
- fallback/escalation reason;
- safe provider metrics;
- context snapshot ID/revision when compaction actually runs;
- limitations and unverified-capability warnings.

### 6.1 Ledger integrity

Each ledger entry links:

- thread, request, and trace IDs;
- candidate ID;
- critic panel ID and version;
- score ID and policy version;
- decision ID, rule ID, disposition, and safe reason;
- energy before, after, and delta;
- evidence references and reference hashes;
- provider-call IDs;
- repair request/result IDs;
- limitations.

Identical replay is idempotent. Conflicting reuse of a ledger ID fails closed.

### 6.2 Evidence integrity boundary

`reference_hash` is the SHA-256 digest of the exact evidence reference string. It is not represented as a content hash for an evidence body. Evidence bodies are excluded from the ledger and Energy Card.

## 7. Constraint and energy policy

1. Hard constraints dominate soft energy.
2. Missing external evidence cannot be satisfied by project-only retrieval.
3. A repair creates a new immutable candidate and undergoes complete reevaluation.
4. Non-improving repair and exhausted repair budget terminate explicitly.
5. Provider output cannot bypass critics, score, decision, ledger, or projection.
6. Refusal is a request-policy disposition; rejection is a candidate disposition.
7. Unsafe rejected candidate text is not emitted as the final answer.
8. Model compatibility is filtered before cost/quality routing.
9. Cross-provider fallback is explicit, privacy-preserving and ledgered; silent fallback is forbidden.
10. Provider marketing does not establish product quality or routing superiority.
11. Multi-agent expansion is bounded and justified by energy, risk or uncertainty thresholds.
12. Context summaries cannot override pinned facts, hard constraints, exact identifiers, evidence or ledger records.

## 8. Human authority model

Current state: planned, not implemented.

Target modes:

```text
disabled | required | risk_based
```

Human actions must include expected revision, typed action, safe reason, trusted actor when productionized, and idempotent resume semantics. Clarify and escalate currently terminate without durable resume.

## 9. Persistence, replay and compaction model

Current replay proof is in-memory only. Completed states with a final projection short-circuit without duplicating provider calls, decisions, ledger entries, or trace events.

Target sequence:

1. in-memory checkpointer wiring proof;
2. thread isolation and resume tests;
3. revision-guarded human interrupts;
4. PostgreSQL saver;
5. additive migration and rollback;
6. retention and redaction enforcement;
7. restart proof;
8. revisioned context snapshots;
9. minimal/balanced/max compaction with pinned facts and exact references;
10. contradiction/drift rejection and snapshot rollback.

Context compaction must preserve exact constraints, identifiers, failures, evidence references, ledger links, accepted decisions and unresolved work. It never persists hidden chain-of-thought or secrets.

## 10. Evidence, trace, and audit model

- Logs are operational diagnostics.
- Metrics are aggregated measurements.
- Domain trace events describe safe actions and observations.
- Decision Ledger entries are authoritative decision history.
- Energy Card v2 is a user-facing projection.
- Context snapshots are revisioned memory projections, not authority over source records.
- A future audit packet will be an allow-listed reviewer artifact.

Hidden chain-of-thought, prompts, credentials, raw environment dumps, and raw provider transcripts are excluded from all user-facing audit surfaces.

## 11. Security and privacy

Current controls:

- evidence bodies excluded;
- exact reference hashes only;
- redaction status is explicit;
- hidden reasoning excluded;
- rejected unsafe candidate text suppressed;
- no-tool-execution marker recorded;
- provider credentials are not state fields.

Future routing/compaction controls:

- allow-listed model catalog;
- no arbitrary caller-supplied model IDs;
- provider privacy/data-handling compatibility filter;
- no silent cross-provider fallback;
- no secrets or raw environment dumps in summaries;
- version/hash/source-range metadata for context snapshots;
- rollback to the previous trusted snapshot.

Before persistence, EACHAT still requires a formal retention matrix, redaction tests, deletion/expiry behavior, and trusted actor model.

## 12. Test strategy and evidence levels

Milestone 9 tests cover:

- graph topology;
- ledger links;
- Energy Card v2 projection;
- energy before/after/delta;
- repair history;
- SHA-256 format and evidence-body exclusion;
- rejected-candidate suppression;
- conflicting ledger IDs;
- replay idempotency;
- external-evidence wait behavior.

Milestone 9 remote evidence: 519 tests passed.

The provider/context documentation checkpoint passed exact-head CI runs `29689906124` and `29689906247`. It does not prove provider adapters, compaction or multi-agent runtime behavior.

Future tests must cover selector validation, model catalog allow-listing, unsupported capability failure, no silent fallback, routing budgets, compaction invariants, pinned-fact preservation, summary drift rejection, multi-agent termination and ledger projection.

## 13. Migration and rollback

Milestone 9 is additive. Legacy `EnergyCard` and existing public routes remain unchanged.

Provider/context migration is staged:

1. provider-neutral selector/catalog contracts;
2. preserve current DeepSeek seam through an adapter;
3. safe requested/served metadata;
4. verified Kimi K3 discovery and adapter;
5. GPT-5.6 adapter with premium budget;
6. context snapshot contracts and persistence;
7. UI selectors;
8. adaptive/committee modes behind feature flags;
9. fixed benchmark before default/claim changes.

Rollback:

- return to existing DeepSeek seam;
- disable provider adapters independently;
- disable auto/adaptive/committee modes;
- retain previous trusted context snapshot;
- ignore additive fields in older readers;
- never rewrite ledger history.

## 14. Cross-project adoption

The immutable source and adoption matrix is maintained in `docs/energy_aware_chat_cross_project_learning_register.md`.

Adopted now:

- Session 13 sanitized audit projection principles;
- EACODE append-only ledger integrity;
- EACODE SHA-256 labels and trust/redaction metadata;
- provider-neutral profile vocabulary as documentation;
- context-compaction architecture as documentation;
- Session 13 multi-agent patterns as deferred product-local architecture;
- EACORE documentation-first extraction rule.

Deferred:

- Session 13 revision-guarded human gates;
- Session 13 durable PostgreSQL checkpoints;
- EACODE reviewer manifest and recovery packet;
- Kimi K3 and GPT-5.6 product adapters;
- persistent context compaction;
- committee/adaptive orchestration.

Rejected:

- shell/repository execution in chat;
- estimation-specific arithmetic and schemas;
- premature EACORE runtime extraction;
- guessed Kimi K3 identifiers;
- silent provider fallback;
- unbounded multi-agent execution.

## 15. Claim boundary

Allowed:

> EACHAT has a CI-validated deterministic LangGraph core with typed state, evidence routing, provider budgets, bounded repair, six deterministic dispositions, an append-only Decision Ledger, Energy Card v2, and safe final-answer projection. It also has a documented provider-neutral routing, context-compaction and bounded multi-agent architecture for DeepSeek, Kimi K3 and GPT-5.6.

Blocked:

- graph-backed public API;
- persistent orchestration;
- complete human-in-the-loop support;
- live graph provider proof;
- all three providers implemented in the product;
- Kimi K3 objectively best;
- automatic routing or multi-agent quality improvement;
- context compaction eliminating context rot;
- public deployment;
- production readiness or telemetry.

## 16. Prioritized roadmap

| Milestone | Status |
|---|---|
| 0–8 graph foundation and decision semantics | complete, L2 |
| 9 ledger, Energy Card v2, final projection | complete, L2 |
| 10 graph-backed API with provider-neutral contract boundary | next |
| 11 in-memory checkpoint proof | pending |
| 12 human gates | pending |
| 13 PostgreSQL persistence | pending |
| 14 observability | pending |
| 15 evidence/citation hardening | pending |
| 16 graph-backed UI | pending |
| 17 provider catalog, Kimi K3 and GPT-5.6 adapters | architecture documented; implementation pending |
| 18 context compaction and bounded multi-agent modes | architecture documented; implementation pending |
| 19 quality evaluation | pending |
| 20 deployment | pending |
| 21 release audit | pending |

## 17. Next exact slice acceptance

The next slice is defined in:

```text
docs/energy_aware_chat_milestone_10_graph_api_spec.md
docs/energy_aware_chat_milestone_10_provider_context_addendum.md
```

The graph-backed API may not become the default until deterministic parity, no-double-execution proof, feature-flag rollback, safe pending-evidence behavior, and remote CI are green.

Milestone 10 must remain truthful: provider-neutral contract readiness is allowed, but full Kimi K3/GPT-5.6 integration, context compaction and committee/adaptive execution remain later evidence-gated slices.
