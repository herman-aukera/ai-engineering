# Session 13 + 14 Plus — Unified Final Handoff

## Handoff decision

The consolidation candidate is **implemented, audited and technically release-ready for review**, but it is intentionally **not merged**.

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
```

## Final-proof rule

This document intentionally does not embed its own commit SHA because doing so would create an endless self-referential commit/run cycle.

Final repository proof is:

1. the current head of `gg-session-14/plus-consolidated`;
2. the latest successful PR #21 workflow whose `head_sha` equals that branch head;
3. successful `test-estimador-cag`, `unified-postgres-evidence` and `container-readiness` jobs in that run;
4. PostgreSQL and container artifacts whose names include the same head SHA.

The audited pre-documentation technical checkpoint was:

```text
SHA: c054399ace1a618fc8eec2ae0ad18333a226e715
CI run: 30861856860
Deterministic tests: 1135 passed, 11 skipped, 3 deselected
PostgreSQL lifecycle: passed
Production container readiness: passed
```

## Canonical architecture

```text
START
-> calibrated capability and context bootstrap
-> deterministic unified supervisor
-> reformulation with immutable source identity
-> semantic classification
-> requirement extraction and component classification
-> optional durable structure review
-> bounded retrieval with sequential fallback
-> deterministic estimate
-> baseline/aggressive/conservative/synthesized competition
-> constraint-Energy assessment
-> reliability analyst
-> typed Critic
-> bounded Boss recommendation
-> selective recovery when authorized
-> independent coherence validation
-> persistent human review
-> proposal
-> finalization
-> END
```

## Authority contract

There is one graph-routing authority:

- Critic emits typed findings and does not route.
- Boss emits a bounded recommendation and does not own topology.
- The unified supervisor decides every transition.
- Python policy owns arithmetic, constraints, budgets, privileges and deterministic escalation.
- The persisted human gate owns approve, adjust and reject authority.

Every human outcome returns to the supervisor:

```text
approve or adjust -> proposal -> finalize
reject            -> finalize without proposal
```

## State and identity contract

The source request is preserved byte-for-byte for thread/service identity, including boundary whitespace. Reformulation produces a separate canonical brief in `reformulated_request`. Requirement extraction consumes that brief when present.

This preserves:

- exact request identity;
- reviewed-graph historical behavior;
- rollback provenance;
- deterministic specialist input;
- strict service validation.

## Persistence contract

The unified runtime uses `AsyncPostgresSaver` with stable thread identity derived from the estimation identifier.

The evidence gate proves:

```text
start
-> interrupt
-> close checkpointer
-> reopen
-> resume same thread and expected revision
-> finalize
-> close checkpointer
-> reopen
-> reread identical terminal state
```

Revision and idempotency protections remain those of the Session 14 human-review contract.

## Provider and routing contract

The runtime registry is built from the sanitized Session 13 Plus benchmark snapshot. A route is enabled only when its historical benchmark record meets the configured quality/schema/tool/failure gates.

The unified policy authorizes both:

- primary stage capability;
- declared fallback stage capability.

A missing required fallback fails closed. The deterministic Python recovery capability remains separate from provider LLM capability records.

The snapshot is bundled into the production image as the only admitted provider-readiness artifact. Raw rows, responses, logs and credentials are excluded.

## API and rollback contract

Unified additive endpoints:

```text
GET  /api/v1/estimate/graph/unified/readiness
POST /api/v1/estimate/graph/unified
POST /api/v1/estimate/graph/unified/{estimation_id}/resume
POST /api/v1/estimate/graph/unified/control
POST /api/v1/estimate/graph/unified/control/{estimation_id}/resume
```

Rollback paths retained:

```text
POST /api/v1/estimate/graph
POST /api/v1/estimate/graph/reviewed/start
```

A unified-runtime startup failure is isolated and must not disable the supervised or reviewed paths.

## Control Room privacy contract

The unified Control Room returns an allowlisted control-plane projection only. It excludes raw source text, prompts, hidden reasoning, raw provider output, credentials and connection strings.

Recursive projection validation rejects:

- sensitive key names;
- OpenAI-like keys;
- Logfire-like tokens;
- generic bearer credentials;
- private-key material;
- unsupported nested values.

Authorized-capability values are subject to the same recursive scanner.

## Validation gates

Every final candidate head must pass:

```text
Ruff
Python compilation
full deterministic pytest suite excluding live-provider tests
git diff --check
tracked-secret scan
real PostgreSQL pause/restart/resume evidence
production-image build and readiness probes
sanitized readiness assertions
```

Provider-readiness live calls remain a separate credentialed gate and are not fabricated by deterministic CI.

## Documentation entrypoints

- `docs/session13_14_plus_unified_architecture.md`
- `docs/session13_14_plus_unified_migration_map.md`
- `docs/session13_14_plus_unified_state_and_reducers.md`
- `docs/session13_14_plus_unified_api.md`
- `docs/session13_14_plus_unified_evidence.md`
- `docs/session13_14_plus_unified_audit.md`
- `docs/session13_14_plus_unified_final_handoff.md`

## Rollback plan

No rollback requires rewriting source history:

1. keep PR #21 unmerged;
2. continue using supervised and reviewed API paths;
3. disable or omit unified runtime exposure at composition time;
4. retain all source branches and immutable benchmark evidence;
5. diagnose unified-only state/checkpoint compatibility before any later promotion.

## Release boundary

This handoff authorizes **review of the consolidation candidate**, not automatic merge or production promotion.

Still unproven:

- superiority over existing paths;
- fresh reachability of every calibrated provider;
- lossless compaction;
- historical-checkpoint migration;
- safe retirement of rollback routes.

Those remain explicit post-consolidation evaluation and release decisions.
