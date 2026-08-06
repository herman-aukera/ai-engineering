# Estimador CAG

## Current consolidation candidate

```text
Working mode: LIDR coursework continuity + Session 13/14 Plus semantic consolidation
Branch: gg-session-14/plus-consolidated
Draft PR: #21
PR base: gg-session-14/plus
Graph: session13_14_plus_unified_graph
Graph version: session13_14_plus.unified.v1
Status: draft, open, unmerged; review candidate with bounded evidence debt
```

This branch semantically consolidates the mature Session 13 Plus reviewed lifecycle with Session 14 Plus supervision, persistent human authority, capability/context controls, deterministic candidate competition and Energy policy. It does not replace or modify the source branches.

Canonical entrypoints:

- `docs/session13_14_plus_unified_architecture.md`
- `docs/session13_14_plus_unified_migration_map.md`
- `docs/session13_14_plus_unified_state_and_reducers.md`
- `docs/session13_14_plus_unified_api.md`
- `docs/session13_14_plus_unified_evidence.md`
- `docs/session13_14_plus_unified_audit.md`
- `docs/session13_14_plus_unified_final_handoff.md`

## Authority model

```text
Models and specialists -> typed proposals, findings and evidence
Critic                -> typed defects; no route authority
Boss policy           -> deterministic bounded recommendation
Unified supervisor    -> every graph transition
Python policy         -> arithmetic, hard constraints, Energy, budgets and privileges
Persistent human gate -> approve, adjust or reject protected outcomes
```

Every final human decision returns to the supervisor:

```text
approve/adjust -> supervisor -> proposal -> supervisor -> finalize
reject         -> supervisor -> stopped finalization
```

## Unified lifecycle

```text
START
-> policy_bootstrap
-> supervisor
-> structure phase and optional structure review
-> supervisor
-> bounded retrieval with sequential fallback
-> deterministic estimate
-> supervisor
-> four-candidate competition and Energy
-> supervisor
-> reliability analysis
-> typed Critic and deterministic Boss recommendation
-> supervisor
-> bounded selective recovery when justified
-> supervisor
-> independent coherence validation
-> supervisor
-> persistent human review when required
-> supervisor
-> proposal or stopped finalization
-> supervisor/finalize
-> END
```

The consolidated graph is additive. Runtime failure in the unified composition must not prevent the supervised or reviewed services from opening.

## API

Unified routes:

```text
GET  /api/v1/estimate/graph/unified/readiness
POST /api/v1/estimate/graph/unified
POST /api/v1/estimate/graph/unified/{estimation_id}/resume
POST /api/v1/estimate/graph/unified/control
POST /api/v1/estimate/graph/unified/control/{estimation_id}/resume
```

Rollback routes:

```text
POST /api/v1/estimate/graph
POST /api/v1/estimate/graph/reviewed/start
```

The control endpoints return an allowlisted projection. Raw graph state, source transcript, prompts, hidden reasoning, raw provider output, credentials and connection strings are excluded.

## Persistence

The unified runtime uses `AsyncPostgresSaver` and stable thread identity:

```text
thread_id = estimate:<estimation_id>
```

The CI lifecycle evidence covers interrupt, checkpointer close/reopen, same-thread revision-guarded resume, proposal/finalization, a second reopen and terminal reread equality.

Historical checkpoints are not automatically interpreted as unified checkpoints. Existing reviewed and supervised threads remain on their originating graph versions.

## State and reducers

The state hierarchy is additive:

```text
EstimationGraphState
└─ ReviewedEstimationGraphState
   └─ Session14EstimationGraphState
      └─ Session14PlusEstimationGraphState
         └─ UnifiedEstimationGraphState
```

Replay-sensitive unified reducers use stable identities, deduplicate identical replay, fail closed on conflicting reuse and retain semantic order. Nodes emit deltas rather than full accumulated lists.

The inherited `stage_route_events` provider-routing accumulator remains documented bounded debt: it is not the canonical graph-transition ledger, and completed-node guards currently prevent duplicate execution. A dedicated semantic-ID reducer requires a separate compatibility slice.

## Provider policy

Documentation and configuration do not enable a provider route.

The unified registry is built from a sanitized historical benchmark snapshot and distinguishes benchmark calibration from present reachability. Both primary and fallback routes must be capability-authorized. Unsupported efforts, excessive output limits, missing fallbacks and unrecognized model identities fail closed. Deterministic Python recovery remains explicit and normal CI makes no paid provider calls.

A skipped credentialed provider job means current reachability is unverified; it does not invalidate historical calibration evidence.

## Context and competition

Compacted context is a derived projection, never source of truth. It preserves identity, versions, hard constraints, evidence references, route-plan identity, checkpoint/human revision, source branch/SHA, rollback and claim boundaries. Sensitive content and stale source revisions are rejected.

Competition produces immutable baseline, aggressive, conservative and synthesized candidates. Python owns arithmetic and evidence bounds. Missing hours and material divergence escalate; downstream coherence validation may veto synthesis. No model owns authoritative totals.

## Validation

Normal CI is deterministic and requires:

```text
Ruff
Python compilation
full pytest suite excluding live-provider tests
git diff --check
tracked-secret scan
real PostgreSQL pause/reopen/resume evidence
production image build and readiness probes
sanitized readiness assertions
```

The exact final proof is the latest successful PR #21 workflow whose `head_sha` equals the current consolidation branch head, plus artifacts named with the same SHA.

## Control Room

Implementation:

```text
app/ui/unified_control_room.py
```

Run locally after FastAPI is available:

```zsh
ESTIMADOR_BACKEND_URL=http://localhost:8000 \
  uv run streamlit run app/ui/unified_control_room.py
```

Deterministic tests cover URL construction, decision payloads, candidate/route projection and recursive privacy rejection. A human-visible browser smoke and screenshot are not present in current CI evidence, so the UI is contract-tested but browser-unverified.

## Claim boundary

Supported only by exact-head deterministic/infrastructure evidence:

- a separately versioned unified graph exists;
- the supervisor owns graph transitions;
- persistent approve/adjust/reject returns through the supervisor;
- additive APIs and rollback paths are present;
- PostgreSQL and production-container gates can validate the exact head.

Not established:

- superiority over reviewed or supervised paths;
- current reachability of every historically calibrated provider;
- lossless context compaction;
- automatic migration of historical checkpoints;
- browser-validated Control Room usability;
- production promotion or authorization to merge.

## Historical coursework

Historical Session 10–14 submissions, artifacts and presentation material remain under `docs/`, `artifacts/`, `evals/` and `exercises/`. Their recorded branch names, SHAs, runs and test counts are historical evidence, not current consolidation status. See `docs/HISTORICAL_SESSIONS.md` and the session-specific handoff documents when auditing those lines.
