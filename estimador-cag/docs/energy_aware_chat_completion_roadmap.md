# Energy Aware Chat completion roadmap

## Verified baseline

- Branch/head at audit: `EACHAT` / `a207d7114d386c8009fe43d5d3a54dc274c71c15`.
- PR #5: open, base `main`, head `EACHAT`, mergeable, not merged.
- Remote CI on audited head: successful runs `27685885752` and `27686051033`.
- Local Windows baseline: lint, compile, and demo payload contracts passed; 457 non-Bash tests passed. Six focused export-manifest tests require `/bin/bash`, unavailable on this host.
- Release claims remain `release_claims_blocked_missing_evidence` and `measurement_only_no_quality_claim`.

## Milestone status

| Milestone | Status | Exit evidence |
|---|---|---|
| 0. Recovery and baseline | complete for current checkpoint | isolated clean worktree, repository/PR/CI verified, architecture and gap map recorded |
| 1. Versioned product-local graph state | complete | typed v1 state, reducer discipline, canonical serializer, fixture, import-boundary tests; exact-head CI green |
| 2. Interpretation and policy nodes | implemented; validation pending | explicit state deltas, safe typed trace events, deterministic normalization, replay tests |
| 3-5. Evidence, provider, critic/score/decision nodes | pending | preserve current behavior with parity tests |
| 6. Sequential LangGraph | pending | fake-runtime path; domain truth remains outside graph |
| 7-10. Repair, decisions, ledger/card, API compatibility | pending | bounded budgets and six dispositions |
| 11-13. Checkpoints, human gates, PostgreSQL | pending | resume, migration, rollback, retention, redaction |
| 14-18. Observability, retrieval, UI, providers, evaluation | pending | opt-in live evidence and fixed quality metrics |
| 19-20. Deployment and release audit | pending | operational proof before claim changes |

## Next exact milestone

Add provider-free evidence-need and evidence-routing nodes that reuse the current `classify_source_need` and project retriever. Red tests must prove skip/retrieve routing, evidence attribution, safe state deltas, idempotent trace replay, and parity with the existing source-need behavior. Do not add LangGraph execution yet.

## Claim discipline

Completing a code milestone does not upgrade release claims. Public deployment, live-provider quality, production readiness, and telemetry claims remain blocked until their existing evidence gates pass with committed artifacts.
