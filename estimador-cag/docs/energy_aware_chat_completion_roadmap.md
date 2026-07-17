# Energy Aware Chat completion roadmap

## Verified baseline

- Branch: `EACHAT`.
- PR #5: open, base `main`, head `EACHAT`, mergeable, not merged.
- Milestone 9 code checkpoint: `dd79bf4befd625ce673242e843c14a023c0862d6`.
- Remote CI run `29608614284`: success.
- Deterministic suite: 519 passed.
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
| 10. Graph-backed API | specified; implementation pending | additive V2 routes, stable IDs, no double execution, compatibility and rollback tests |
| 11. In-memory checkpoint proof | pending | thread isolation, replay and resume contracts |
| 12. Human gates | pending | revision-guarded clarify/escalate interrupt and resume |
| 13. PostgreSQL | pending | migrations, rollback, retention, redaction and restart proof |
| 14–18. Observability, retrieval, UI, providers, evaluation | pending | dedicated integration evidence and fixed quality metrics |
| 19–20. Deployment and release audit | pending | operational proof before claim changes |

## Next exact milestone

Implement the additive graph-backed API specified in:

```text
docs/energy_aware_chat_milestone_10_graph_api_spec.md
```

The next slice must keep current routes as rollback surfaces, execute one graph only, expose stable IDs and Energy Card v2, represent `awaiting_evidence` without fabrication, and remain deterministic/keyless in CI.

## Cross-project provenance

Adoption decisions and immutable source SHAs are recorded in:

```text
docs/energy_aware_chat_cross_project_learning_register.md
```

## Claim discipline

Completing a code milestone does not upgrade release claims. Public deployment, persistent orchestration, human-gate completeness, live-provider quality, production readiness, and telemetry remain blocked until their dedicated evidence gates pass.
