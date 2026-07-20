# Energy Aware Chat completion roadmap

## Verified baseline

- Branch: `EACHAT`.
- PR #5: open, base `main`, head `EACHAT`, mergeable, not merged.
- Milestone 9 code checkpoint: `dd79bf4befd625ce673242e843c14a023c0862d6`.
- Milestone 9 deterministic suite: 519 passed.
- Milestone 10 code checkpoint: `9aa1e09347734c3323436fea0c9bb2ef437fb209`.
- Provider/context architecture checkpoint: `1b3157c50778d2f42f1a73886a400358a22f3369`.
- Exact-head CI runs `29689810921` and `29689811061`: success (M9 baseline); M10 CI pending.
- Release claims remain `release_claims_blocked_missing_evidence` and `measurement_only_no_quality_claim`.

## Milestone status

| Milestone | Status | Exit evidence |
|---|---|---|
| 0. Recovery and baseline | complete | repository/PR/CI verified; architecture and gap map recorded |
| 1. Versioned product-local graph state | complete | typed v1 state, reducer discipline, canonical serializer, fixture, import-boundary tests |
| 2. Interpretation and policy nodes | complete | explicit state deltas, safe typed trace events, deterministic normalization, replay tests |
| 3. Evidence routing | complete | classifier/retriever parity, skip/project/external routes, attribution and replay tests |
| 4. Candidate provider abstraction | complete | deterministic and baseline adapters, typed metrics, budget gates, replay protection |
| 5. Critic, score, and decision nodes | complete | candidate/policy linkage, evaluator parity, stale-link and replay tests |
| 6. Sequential LangGraph | complete | compiled graph, conditional evidence routes, explicit deltas and replay short circuit |
| 7. Bounded repair | complete | explicit plans, candidate v2, retry/cost budgets, full reevaluation and termination tests |
| 8. Complete decision semantics | complete | six deterministic dispositions, versioned request rules, precedence, rule IDs and transitions |
| 9. Ledger and Energy Card v2 | complete | append-only ledger, reference integrity metadata, safe final answer, Energy Card v2, replay/conflict tests, remote CI green |
| 10. Graph-backed API | implemented | additive V2 routes at `/energy-chat/v2/chat` and `/energy-chat/v2/chat/live`, stable IDs, one canonical graph execution, provider-neutral selector contracts, no double execution, no silent legacy fallback, deterministic CI-safe route, live bounded route, awaiting-evidence representation, safe error mapping, legacy route regression tests |
| 11. In-memory checkpoint proof | complete | InMemoryCheckpointer wrapping LangGraph MemorySaver, thread isolation, replay idempotency, checkpoint retrieval, no-duplicate-provider-call proof, 6 focused tests |
| 12. Human gates | implemented | HumanActionRequest with revision guard, interrupt on clarify/escalate via LangGraph interrupt(), Command(resume=) support, StaleHumanActionError for stale actions, 6 focused tests, green CI |
| 13. PostgreSQL | partial | PostgresCheckpointer wrapping LangGraph PostgresSaver, versioned schema DDL with migration tracking, CheckpointRetentionPolicy — interface tests only; live-DB integration (connection, write, restart, reopen, retention, redaction, rollback) deferred to manual credentialed smoke |
| 14. Observability | implemented | NodeSpan per-node timing, GraphExecutionMetrics aggregation, CheckpointTelemetry, safe trace projections without payloads/secrets/transcripts, compute_graph_execution_metrics from authoritative state, 7 tests, green CI |
| 15. Evidence and citation hardening | implemented | EvidenceBodyMetadata with conditional body hashing, EvidenceVerificationResult, CitationValidationResult with fabricated-citation detection, check_evidence_freshness with age-based staleness, 12 tests, green CI |
| 16. Graph-backed UI | implemented | V2 browser demo at /energy-chat/v2/demo with provider/effort/context selectors, Energy Card v2 display, provider metrics summary, ledger/trace projection, thread history with replay, awaiting-evidence handling; legacy demo unchanged |
| 17. Provider catalog and live adapters | implemented | ProviderModelCapability typed records with source refs and verification dates; DeepSeek V4 Flash/Pro verified, Kimi K3 and GPT-5.6 Luna/Terra/Sol documented; resolve_effort_profile() finds cheapest verified model; catalog wired into live provider selection; fails closed on unverified combinations; 8 tests, green CI |
| 18. Context compaction and multi-agent profiles | implemented | ContextCompactionPolicy per profile (minimal 4K/2 turns, balanced 16K/8 turns, max 64K/24 turns), ContextSnapshot with revision/hash drift detection, MultiAgentBudget per mode (single/critic/committee/adaptive with agent counts and token/cost/deadline ceilings), profile resolution functions, 10 tests, green CI |
| 19. Quality evaluation | implemented | QualityRubric (8 weighted dimensions), QualityBenchmarkCase with gold expectations, evaluate_quality_case() per-case scoring, build_quality_benchmark_run() aggregation; measurement_only_no_quality_claim; 8 tests; cross-provider comparison requires credentialed adapters (M17) |
| 20–21. Deployment and release audit | implemented | ReleaseAudit with 8 evidence-gated claim boundaries (3 allowed, 5 blocked_missing_evidence), deployment readiness check (CI/test/secret/docker gates), deterministic and CI-safe; 8 tests, green CI |

## Next exact milestone

Milestone 10 is implemented. The next slice is Milestone 11 — in-memory checkpoint proof.

Implement thread isolation, replay, and resume contracts as specified in:

```text
docs/energy_aware_chat_sdd.md  (section 9)
```

The checkpoint slice must prove safe replay/resume without persistence, test thread isolation, and add checkpoint wiring to the graph runtime before PostgreSQL saver work in M13.

## Provider and context architecture

Canonical documents:

```text
../ENERGY_AWARE_PROVIDER_ROUTING_README.md
docs/energy_aware_chat_provider_context_spec.md
../docs/ENERGY_AWARE_PORTFOLIO_README.md
```

Stable intended selectors:

```text
provider: auto | deepseek | kimi | openai
effort: fast | balanced | max
context: minimal | balanced | max
orchestration: single | critic | committee | adaptive
```

Current product policy:

- DeepSeek is the cost-effective default.
- Kimi K3 is the user-preferred quality candidate after API capability verification; it is not benchmark-proven best.
- GPT-5.6 is the premium option.
- Reasoning effort and context compaction are independent.
- Automatic routing and multi-agent expansion remain feature-flagged until fixed evaluations prove their trade-offs.

## Cross-project provenance

Adoption decisions and immutable source SHAs are recorded in:

```text
docs/energy_aware_chat_cross_project_learning_register.md
```

## Claim discipline

Completing a code milestone does not upgrade release claims. Public deployment, persistent orchestration, human-gate completeness, live-provider quality, provider superiority, automatic-routing improvement, context-rot prevention, production readiness, and telemetry remain blocked until their dedicated evidence gates pass.
