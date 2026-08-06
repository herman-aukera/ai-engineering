# Session 13 + 14 Plus — Unified Final Handoff

## Handoff decision

**Verdict:** coherent with bounded debt.

The consolidation candidate is implemented and available for review, but it is intentionally draft, unmerged and not presented as production-ready.

```text
Branch: gg-session-14/plus-consolidated
Pull request: #21
Base: gg-session-14/plus
PR mode: draft, open, unmerged
Graph: session13_14_plus_unified_graph
Graph version: session13_14_plus.unified.v1
```

Source lines retained:

```text
Session 13 Plus: f87605cb8a8ee5ff2606c51e5490b6beb2ca7f7a
Session 14 Plus: 34011bcd9442130e09ab776d9072c0d53a2d93c2
Common ancestor: d9caf76d013d18cf6235f29d21f7a73f8133bce8
Controlled ancestry merge: 6e0289cb1006fd3980fd59ceaf37e78f6a77bb5a
```

## Final-proof rule

This document does not embed its own commit SHA because that would create a self-referential commit/run cycle.

Final repository proof is:

1. current head of `gg-session-14/plus-consolidated`;
2. latest successful PR #21 workflow whose `head_sha` equals that head;
3. successful deterministic/static, unified PostgreSQL and container-readiness jobs;
4. PostgreSQL and container artifacts named with the same head SHA;
5. PR metadata updated to cite that same head and run without changing source history.

Earlier green runs remain historical evidence only.

## Unified architecture

```text
START
-> policy/capability/context bootstrap
-> deterministic unified supervisor
-> reformulation with immutable source identity
-> semantic classification and typed structure
-> optional durable structure review
-> bounded retrieval with sequential fallback
-> deterministic estimate
-> four immutable candidates and Energy assessment
-> reliability analyst
-> typed Critic
-> deterministic bounded Boss recommendation
-> selective recovery when authorized and improving
-> independent coherence validation
-> persistent human review
-> supervisor
   -> proposal for approve/adjust
   -> stopped finalization for reject
-> supervisor/finalize
-> END
```

## Authority contract

- Critic emits typed findings and does not route.
- Boss emits a bounded recommendation and does not own topology.
- The unified supervisor owns every graph transition.
- Python owns arithmetic, constraints, budgets, privileges and deterministic escalation.
- The persisted human gate owns approve, adjust and reject authority.

Every human outcome returns to the supervisor:

```text
approve/adjust -> supervisor -> proposal -> supervisor -> finalize
reject         -> supervisor -> stopped finalization
```

## Reducer and identity contract

Replay-sensitive budget evidence, graph issues and domain trace events use deterministic semantic identities with optional explicit IDs. They:

- deduplicate identical replay;
- reject conflicting identity reuse;
- preserve first-seen retrieval rank, diagnostic order and trace chronology;
- leave input collections unmodified.

Unified route, contribution, HITL and context reducers retain their keyed replay contracts. Nodes emit deltas only.

Bounded debt: inherited `stage_route_events` remains an `operator.add` provider-routing accumulator. It is not the canonical transition ledger and completed-node guards prevent duplicate execution, but a reducer-level stable ID requires a separate compatibility slice.

## Persistence and HITL contract

The unified runtime uses `AsyncPostgresSaver` and stable thread identity. Exact-head infrastructure evidence must prove:

```text
start
-> interrupt
-> close checkpointer
-> reopen
-> resume same thread and expected revision
-> refresh context
-> proposal/finalize
-> close checkpointer
-> reopen
-> reread identical terminal state
```

Approve, adjust and reject use revision and idempotency guards. Interrupt and control payloads are allowlisted and sanitized.

## Provider and context contract

The runtime registry is built from a sanitized immutable historical benchmark snapshot. Passing benchmark records may authorize exact routes, but historical calibration is not current reachability.

Primary and fallback capabilities both fail closed on missing identity, disabled lifecycle, unsupported effort, output-limit excess or unsupported tools. Deterministic Python recovery is explicit and separate.

Compacted context is derived, freshness-checked and sanitized. It preserves identities, hard constraints, evidence refs, route plan, checkpoint/human revision, source SHA, rollback and claim boundaries. It excludes transcript from control projection, prompts, hidden reasoning, raw provider output, credentials and DSNs.

## Competition and Energy contract

Baseline, aggressive, conservative and synthesized candidates are immutable and fingerprinted. Python owns bounds and arithmetic. Missing hours and material divergence escalate. The selected candidate and Energy snapshot survive resume. Coherence validation may veto synthesis.

## API and rollback contract

Unified additive endpoints:

```text
GET  /api/v1/estimate/graph/unified/readiness
POST /api/v1/estimate/graph/unified
POST /api/v1/estimate/graph/unified/{estimation_id}/resume
POST /api/v1/estimate/graph/unified/control
POST /api/v1/estimate/graph/unified/control/{estimation_id}/resume
```

Rollback endpoints:

```text
POST /api/v1/estimate/graph
POST /api/v1/estimate/graph/reviewed/start
```

A unified-runtime initialization failure is isolated and must not disable the supervised or reviewed services. Historical checkpoints are not upgraded without an explicit versioned adapter.

## Control Room status

The Streamlit Control Room and allowlisted projection are implemented. Deterministic tests verify URLs, decision contracts, route/candidate rows and recursive privacy rejection.

Browser evidence status: **unverified**. No screenshot or human-visible start/review/resume/final smoke artifact is currently part of the exact-head CI evidence. The UI must not be described as browser-validated.

## Validation gates

Every final candidate head must pass:

```text
Ruff
Python compilation
full deterministic pytest suite excluding live-provider tests
git diff --check
tracked-secret scan
real PostgreSQL pause/reopen/resume evidence
production-image build and readiness probes
sanitized readiness assertions
```

Credentialed live-provider smoke remains separate and opt-in. A skipped provider job means current reachability is unknown.

## Documentation entrypoints

- `docs/session13_14_plus_unified_architecture.md`
- `docs/session13_14_plus_unified_migration_map.md`
- `docs/session13_14_plus_unified_state_and_reducers.md`
- `docs/session13_14_plus_unified_api.md`
- `docs/session13_14_plus_unified_evidence.md`
- `docs/session13_14_plus_unified_audit.md`
- `docs/session13_14_plus_unified_final_handoff.md`

## Rollback

1. Keep PR #21 draft and unmerged.
2. Continue calling supervised or reviewed endpoints.
3. Disable or omit unified runtime exposure at composition time.
4. Retain original source branches and immutable benchmark evidence.
5. Never reinterpret a thread with another graph version.
6. Revert consolidation-only commits in reverse order on the writable branch if necessary; do not rewrite protected history.

## Remaining limitations

- no current live-provider reachability proof;
- no browser/UI smoke artifact;
- no matched superiority evaluation;
- no lossless-compaction proof;
- no historical-checkpoint adapter;
- inherited `stage_route_events` lacks reducer-level semantic identity;
- PR history is large, although ancestry, base and rollback boundaries are explicit.

## Release boundary

This handoff authorizes review of a **coherent candidate with bounded debt**. It does not authorize merge, production promotion, retirement of rollback paths or stronger claims than the exact final evidence supports.
