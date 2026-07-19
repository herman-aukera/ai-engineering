# Energy Aware Chat completion roadmap

## Verified baseline

- Branch: `EACHAT`.
- PR #5: open, base `main`, head `EACHAT`, mergeable, not merged.
- Milestone 9 code checkpoint: `dd79bf4befd625ce673242e843c14a023c0862d6`.
- Milestone 9 deterministic suite: 519 passed.
- Provider/context architecture checkpoint: `1b3157c50778d2f42f1a73886a400358a22f3369`.
- Exact-head CI runs `29689810921` and `29689811061`: success.
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
| 14. Observability | pending | graph spans, metrics, safe traces and dashboards |
| 15. Evidence and citation hardening | pending | body hashes where permitted, verification, freshness and citation validation |
| 16. Graph-backed UI | pending | browser-tested chat, Energy Card, thread history and safe controls |
| 17. Provider catalog and live adapters | architecture documented; implementation pending | DeepSeek profile adapter, verified Kimi K3 discovery/adapter, GPT-5.6 adapter, explicit fallback and live sanitized proof |
| 18. Context compaction and multi-agent profiles | architecture documented; implementation pending | minimal/balanced/max snapshots, drift tests, single/critic/committee/adaptive budgets and fixed benchmark |
| 19. Quality evaluation | pending | controlled cross-provider and orchestration benchmark; no unsupported “best” claim |
| 20–21. Deployment and release audit | pending | operational proof before claim changes |

## Next exact milestone

Implement the additive graph-backed API specified in:

```text
docs/energy_aware_chat_milestone_10_graph_api_spec.md
```

and constrained by:

```text
docs/energy_aware_chat_milestone_10_provider_context_addendum.md
```

The next slice must keep current routes as rollback surfaces, execute one graph only, expose stable IDs and Energy Card v2, represent `awaiting_evidence` without fabrication, and remain deterministic/keyless in CI.

Milestone 10 should use provider-neutral selector contracts when this can be done without scope inflation. It must not claim complete Kimi K3/GPT-5.6 integration, context compaction, UI selection, or committee/adaptive multi-agent behavior.

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
