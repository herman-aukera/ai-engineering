# Session 13 + 14 Plus — Unified Evidence

## Evidence classes

The consolidation distinguishes four evidence levels:

1. **Contract evidence** — typed schemas, reducers and focused tests.
2. **Deterministic integration evidence** — complete graph execution with fake external adapters.
3. **Infrastructure evidence** — PostgreSQL restart and production-container readiness.
4. **Live-provider evidence** — matched provider calls and telemetry, separate from normal CI.

A lower level does not substitute for a higher one.

## Source evidence retained

### Session 13 Plus production readiness

```text
Source branch: gg-session-13/plus
Source head: f87605cb8a8ee5ff2606c51e5490b6beb2ca7f7a
Production CI: 29943760790
Provider artifact: session13-plus-provider-readiness-dd0af5149ec796156fc16dcefe302936d90b4df1
```

The sanitized provider benchmark snapshot is preserved at:

```text
artifacts/provider-readiness/provider-benchmark-snapshot.json
```

It records route IDs, sample counts, quality/schema/tool pass rates, latency, cost and failure counts. It contains no keys or raw provider responses.

### Mandatory Session 14 hosted trace

```text
https://logfire-eu.pydantic.dev/public-trace/8cadbba1-e228-4881-85f0-94b5d053964d?spanId=502588e17129e153
```

This remains evidence for the submitted Session 14 pause/review/resume lifecycle. It is not presented as a unified-graph trace.

### Session 14 Plus PostgreSQL evidence

```text
artifacts/session14_plus/postgres_pause_resume.json
```

This remains evidence for provider/context policy, competition and the Session 14 Plus lifecycle before semantic consolidation.

## Unified deterministic evidence

Focused and full-suite tests cover:

- replay-safe unified route reducer;
- single supervisor authority sequence;
- approve, adjust and reject supervisor transitions;
- synchronized unified and Session 14 routing counters;
- bounded recovery exhaustion;
- canonical topology;
- immutable source request and canonical reformulated brief;
- reviewed reformulation compatibility;
- exact calibrated capabilities;
- primary and fallback route authorization;
- failure when a fallback capability is absent;
- additive API and resume delegation;
- sanitized Control Room projection;
- rejection of sensitive nested keys and bearer-token-shaped values;
- recursive validation of authorized capabilities;
- decision-contract validation;
- full deterministic journey through structure, estimation, competition, reliability, Critic/Boss, coherence, human authority, proposal and finalization.

## Unified PostgreSQL evidence

CI runs:

```text
python -m scripts.session13_14_unified_postgres_evidence
```

against a real PostgreSQL/pgvector service and the exact ORBITA teacher fixture.

Required lifecycle:

```text
start unified graph
-> structure phase
-> retrieval and deterministic estimate
-> four candidates and Energy
-> reliability
-> Critic/Boss
-> coherence
-> final human interrupt
-> close PostgreSQL checkpointer
-> reopen
-> approve expected revision on same thread
-> refresh compact context
-> proposal/finalize
-> close/reopen
-> terminal reread
```

The artifact schema is:

```text
session13_14.unified.postgres-evidence.v2
```

Required assertions and fields:

- `source_sha` equals the PR head checked out by CI;
- `pause_execution_status = awaiting_human_review`;
- `pause_interrupt_count = 1`;
- `pause_checkpoint_human_review_status` records the raw checkpoint field separately from public execution status;
- `checkpoint_lifecycles = 3`;
- same thread before and after resume;
- human revision `1 -> 2`;
- final human status `approved`;
- four candidates persisted;
- Energy snapshot persisted;
- typed `critic_verdict` and `critic_issue_count` persisted;
- typed `boss_action` and `boss_issue_code_count` persisted;
- unified route ledger persisted;
- capability records for primary and fallback routes persisted;
- compact-context revision and fingerprint change after approval;
- proposal completes;
- terminal reread equals resumed state.

The raw checkpoint field may still read `not_requested` before resume because LangGraph persists the interrupt before the public service projection normalizes the paused response. The public API contract returns `human_review_status = awaiting_human_review`; the artifact labels the raw value explicitly to avoid conflating these layers.

Repository artifact path:

```text
artifacts/session13_14_unified/postgres_pause_resume.json
```

CI artifact naming rule:

```text
session13-14-unified-postgres-<exact-pr-head-sha>
```

## Container evidence

The consolidated PR builds the production image, starts PostgreSQL and Redis, and verifies:

- `/health` returns HTTP 200;
- `/ready` returns HTTP 200;
- `/api/v1/estimate/graph/unified/readiness` returns HTTP 200;
- the bundled sanitized benchmark snapshot initializes the unified registry;
- existing configured-provider readiness remains sanitized;
- unified graph name and rollback paths are present;
- provider keys, database URLs and Redis URLs are absent from payloads.

The Docker build context excludes all provider artifacts except:

```text
artifacts/provider-readiness/provider-benchmark-snapshot.json
```

Container artifact naming rule:

```text
container-readiness-evidence-<exact-pr-head-sha>
```

## Audited technical checkpoint

Before the final documentation commit, the repaired implementation passed:

```text
SHA: c054399ace1a618fc8eec2ae0ad18333a226e715
CI run: 30861856860
Ruff: passed
Python compilation: passed
Deterministic tests: 1135 passed, 11 skipped, 3 deselected
Diff gate: passed
Tracked-secret gate: passed
Unified PostgreSQL lifecycle: passed
Production container readiness: passed
```

Its PostgreSQL artifact digest was:

```text
sha256:e2b739a6e31b2487bd94c38f0fd2351278baaa924567e7afe4376b8bf791e8f8
```

The documentation commit must pass the same gates. The latest successful PR run whose `head_sha` equals the current branch head supersedes this checkpoint as final-head proof.

## Observability

Unified execution uses:

```text
session13_14_plus.graph.run
session13_14_plus.graph.node
```

The unified PostgreSQL CI evidence is deterministic and does not require a Logfire token. A hosted public trace is a separate optional artifact and must not be fabricated from unit-test evidence.

## Claim matrix

| Claim | Required evidence |
|---|---|
| contracts compile and enforce invariants | focused tests + Ruff + compile |
| full canonical path is reachable | deterministic E2E test |
| pause/resume survives process/checkpointer lifecycle | unified PostgreSQL job |
| production image initializes unified runtime | container readiness job |
| provider route was calibrated historically | immutable benchmark snapshot + source CI |
| provider is currently reachable | fresh credentialed provider run |
| unified graph is superior | matched product evaluation, not established |
| context compaction is lossless | dedicated information-retention evaluation, not established |

## Secret and privacy boundary

Tracked evidence and artifacts must exclude:

- API keys and bearer tokens;
- connection strings;
- source transcript;
- prompts;
- hidden reasoning;
- raw provider output;
- private attachment contents.

CI includes `git diff --check` and tracked-secret scanning. Deliberate credential-shaped sanitizer fixtures require the `test-secret-fixture` marker. Control projections use allowlists and recursively reject sensitive nested keys or secret-like values, including authorized-capability values.

## Final-head rule

Final handoff proof is the latest successful PR #21 run whose head SHA equals the current `gg-session-14/plus-consolidated` branch head. Evidence from an earlier checkpoint may be retained as history but cannot be described as final-head proof.
