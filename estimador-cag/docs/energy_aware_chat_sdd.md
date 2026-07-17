# Energy Aware Chat software design description

## 1. Document control

| Field | Value |
|---|---|
| Product | EACHAT — Energy Aware Chat |
| Repository | `herman-aukera/ai-engineering` |
| Branch | `EACHAT` |
| PR | #5, open, unmerged |
| Milestone 9 code checkpoint | `dd79bf4befd625ce673242e843c14a023c0862d6` |
| Latest Milestone 9 CI | run `29608614284`, success |
| Deterministic tests | 519 passed |
| SDD version | 1.0.0 |
| Claim status | `release_claims_blocked_missing_evidence`; `measurement_only_no_quality_claim` |

This SDD is the canonical engineering control document for EACHAT. Detailed state, policy, and architecture documents remain supporting specifications.

## 2. Product definition and boundary

EACHAT evaluates answer candidates against explicit hard and soft constraints before presenting a final answer. Deterministic Python owns evidence sufficiency, authoritative energy, budgets, and final disposition. Models may propose candidates or observations but cannot override hard constraints.

Supported dispositions:

```text
accept | repair | clarify | reject | refuse | escalate
```

EACHAT owns chat interpretation, grounding, candidate generation, critics, scoring, repair, clarification, refusal, escalation, provider orchestration, chat persistence, Energy Cards, API, UI, and chat evaluations.

EACHAT does not own shell execution, repository mutation, patch application, IDE adapters, EACODE rollback, or speculative shared-core runtime contracts.

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

## 4. Implemented requirements

| Capability | Status | Evidence level |
|---|---|---|
| Strict product-local graph state v1 | implemented | L2 remote CI |
| Replay-safe reducers and canonical serialization | implemented | L2 |
| Interpretation and versioned request policy | implemented | L2 |
| Explicit evidence routing | implemented | L2 |
| Deterministic and live-provider adapter contracts | implemented | L2 deterministic; live graph not yet proven |
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

## 5. Partial requirements

| Capability | Implemented portion | Missing proof or behavior |
|---|---|---|
| API migration | graph and projection contracts exist | graph-backed deterministic/live endpoints, feature flag, rollback and parity |
| Persistence | state is checkpoint-safe in shape | saver, resume, restart, migration and retention |
| Human control | clarify/escalate dispositions exist | interrupts, revision-guarded actions, trusted actor and resume |
| Evidence | references and project retrieval | evidence bodies, content hashes, verification, freshness enforcement and citation validation |
| Observability | typed domain events and provider metrics | node spans, operational metrics, checkpoint telemetry and dashboards |
| UI | legacy demo and Streamlit | graph-backed Control Room, thread history, human controls and browser proof |
| Live providers | adapter seam exists | bounded graph-backed DeepSeek/Kimi evidence |
| Evaluation | deterministic repair benchmark exists | quality rubric and controlled live comparison |

## 6. Data and state contracts

The graph state uses schema and contract version `1.0.0`. New Milestone 9 fields are additive:

- `decision_ledger_entries` — append by `ledger_entry_id`;
- `energy_card_v2` — singular replacement;
- `final_projection` — singular replacement.

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

## 8. Human authority model

Current state: planned, not implemented.

Target modes:

```text
disabled | required | risk_based
```

Human actions must include expected revision, typed action, safe reason, trusted actor when productionized, and idempotent resume semantics. Clarify and escalate currently terminate without durable resume.

## 9. Persistence and replay model

Current replay proof is in-memory only. Completed states with a final projection short-circuit without duplicating provider calls, decisions, ledger entries, or trace events.

Target sequence:

1. in-memory checkpointer wiring proof;
2. thread isolation and resume tests;
3. revision-guarded human interrupts;
4. PostgreSQL saver;
5. additive migration and rollback;
6. retention and redaction enforcement;
7. restart proof.

## 10. Evidence, trace, and audit model

- Logs are operational diagnostics.
- Metrics are aggregated measurements.
- Domain trace events describe safe actions and observations.
- Decision Ledger entries are authoritative decision history.
- Energy Card v2 is a user-facing projection.
- A future audit packet will be an allow-listed reviewer artifact.

Hidden chain-of-thought, prompts, credentials, raw environment dumps, and raw provider transcripts are excluded from all user-facing audit surfaces.

## 11. Security and privacy

Current Milestone 9 controls:

- evidence bodies excluded;
- exact reference hashes only;
- redaction status is explicit;
- hidden reasoning excluded;
- rejected unsafe candidate text suppressed;
- no-tool-execution marker recorded;
- provider credentials are not state fields.

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

Remote evidence: 519 tests passed in GitHub Actions run `29608614284`.

## 13. Migration and rollback

Milestone 9 is additive. Legacy `EnergyCard` and existing public routes remain unchanged.

Rollback boundary:

1. revert graph finalization routing;
2. retain existing state fixture compatibility;
3. ignore additive Milestone 9 fields in older readers;
4. return to the pre-Milestone 9 graph checkpoint if required.

No persisted records exist yet, so no data migration is required for this milestone.

## 14. Cross-project adoption

The immutable source and adoption matrix is maintained in `docs/energy_aware_chat_cross_project_learning_register.md`.

Adopted now:

- Session 13 sanitized audit projection principles;
- EACODE append-only ledger integrity;
- EACODE SHA-256 labels and trust/redaction metadata.

Deferred:

- Session 13 revision-guarded human gates;
- Session 13 durable PostgreSQL checkpoints;
- EACODE reviewer manifest and recovery packet.

Rejected:

- shell/repository execution in chat;
- estimation-specific arithmetic and schemas;
- premature EACORE extraction.

## 15. Claim boundary

Allowed:

> EACHAT has a CI-validated deterministic LangGraph core with typed state, evidence routing, provider budgets, bounded repair, six deterministic dispositions, an append-only Decision Ledger, Energy Card v2, and safe final-answer projection.

Blocked:

- graph-backed public API;
- persistent orchestration;
- complete human-in-the-loop support;
- live graph provider proof;
- quality improvement over plain DeepSeek;
- public deployment;
- production readiness or telemetry.

## 16. Prioritized roadmap

| Milestone | Status |
|---|---|
| 0–8 graph foundation and decision semantics | complete, L2 |
| 9 ledger, Energy Card v2, final projection | complete, L2 |
| 10 graph-backed API | next |
| 11 in-memory checkpoint proof | pending |
| 12 human gates | pending |
| 13 PostgreSQL persistence | pending |
| 14 observability | pending |
| 15 evidence/citation hardening | pending |
| 16 graph-backed UI | pending |
| 17 live providers | pending |
| 18 quality evaluation | pending |
| 19 deployment | pending |
| 20 release audit | pending |

## 17. Next exact slice acceptance

The next slice is defined in `docs/energy_aware_chat_milestone_10_graph_api_spec.md`.

The graph-backed API may not become the default until deterministic parity, no-double-execution proof, feature-flag rollback, safe pending-evidence behavior, and remote CI are green.
