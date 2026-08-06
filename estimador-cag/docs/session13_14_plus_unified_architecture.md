# Session 13 + 14 Plus — Unified Architecture

## Status and boundary

```text
Working mode: LIDR coursework continuity + semantic consolidation
Writable branch: gg-session-14/plus-consolidated
Draft PR: #21
Session 13 Plus source: f87605cb8a8ee5ff2606c51e5490b6beb2ca7f7a
Session 14 Plus source: 34011bcd9442130e09ab776d9072c0d53a2d93c2
Common ancestor: d9caf76d013d18cf6235f29d21f7a73f8133bce8
Controlled ancestry merge: 6e0289cb1006fd3980fd59ceaf37e78f6a77bb5a
```

The consolidation is semantic, additive and rollback-safe. It does not rewrite either source branch and it does not silently reinterpret old checkpoints.

## Objective

Provide one canonical orchestration path combining:

- Session 13 Plus reviewed lifecycle, editable structure review, bounded parallel retrieval, deterministic fallback, reliability, typed Critic, deterministic Boss policy, selective recovery, budgets, provider evidence, audit/scenario foundations and proposal projection;
- Session 14 manual supervision, typed `Command` routing, least privilege, persistent `interrupt()`, same-thread approve/adjust/reject and action auditing;
- Session 14 Plus strict capability authorization, context freshness/privacy, deterministic four-candidate competition, Energy escalation and independent coherence veto.

## Canonical graph

```text
START
-> policy_bootstrap
-> supervisor
-> structure_phase
   -> reformulate_request
   -> semantic_classify
   -> extract_requirements
   -> classify_components
   -> optional structure_review_gate
-> supervisor
-> estimation_phase
   -> bounded parallel retrieval or deterministic sequential fallback
   -> deterministic estimate generation
   -> validation
-> supervisor
-> candidate_competition
   -> baseline
   -> aggressive
   -> conservative
   -> deterministic synthesis
-> supervisor
-> reliability_analysis
-> supervisor
-> critic
-> deterministic Boss recommendation
-> supervisor
-> selective_recovery when justified and budgeted
-> supervisor
-> coherence_validator
-> supervisor
-> human_review_gate when protected authority is required
-> supervisor
   -> proposal for approve/adjust
   -> stopped finalization for reject
-> proposal
-> supervisor
-> finalize
-> END
```

Fixed internal phases may use explicit edges. Every runtime choice is visible and owned by the supervisor; the supervisor label is not used to conceal a fixed sequence.

Graph identity:

```text
session13_14_plus_unified_graph
session13_14_plus.unified.v1
```

## Authority model

```text
Models/specialists -> typed proposals, findings, evidence and bounded action requests
Critic             -> typed defects; no graph-transition authority
Boss policy        -> deterministic accept/repair/clarify/reject/escalate recommendation
Unified supervisor -> every graph transition and prerequisite/budget enforcement
Python             -> arithmetic, hard constraints, Energy, privileges and thresholds
Human gate         -> only approve/adjust/reject authority for protected outcomes
LangGraph          -> durable control flow and resume
PostgreSQL         -> checkpoint durability
```

Mandatory final-review transition:

```text
human_review_gate
-> supervisor
-> proposal or finalize
```

No direct human-gate edge to proposal or finalize is permitted.

## State and reducer model

The unified state extends the reviewed and supervised states additively. Runtime clients, database connections, checkpointers, callables, open files and secrets are excluded from state.

Reducer rules:

- nodes emit only deltas;
- explicit or deterministic semantic IDs identify replay-sensitive records;
- identical replay is idempotent;
- conflicting ID reuse fails closed;
- first-seen rank, diagnostic order and execution chronology are retained;
- completed terminal reads do not execute graph nodes again.

Canonical transition ledgers are `route_events` and `unified_route_events`. The inherited `stage_route_events` provider-routing accumulator is non-canonical bounded debt and still depends on terminal-node guards rather than reducer-level semantic identity.

## Persistence and HITL

Final human authority uses PostgreSQL-backed `interrupt()` with:

- stable thread ID;
- expected revision;
- idempotency key;
- actor and reason;
- typed adjustments;
- sanitized interrupt payload;
- same-thread resume;
- terminal reread.

Actions:

```text
approve -> supervisor -> proposal -> supervisor -> finalize
adjust  -> deterministic recalculation/revalidation -> supervisor -> proposal -> supervisor -> finalize
reject  -> supervisor -> stopped finalization
```

Old reviewed/supervised checkpoints remain on their original graph versions. No automatic converter exists.

## Provider policy

Provider lifecycle states are distinct:

```text
documented
configured
reachable
contract_verified
benchmark_calibrated
enabled
disabled
```

The runtime converts only passing records from the immutable sanitized benchmark snapshot into enabled capabilities. Historical benchmark evidence retains source commit and timestamp. It is not evidence of current reachability.

Both primary and fallback routes are checked for:

- exact provider/model identity;
- enabled lifecycle;
- supported effort;
- output ceiling;
- tool support;
- stage identity.

Unrecognized aliases, unsupported effort, excessive output and missing fallback authorization fail closed. Deterministic Python recovery remains explicit. Normal CI performs no paid calls.

## Context integrity

Compacted context is derived and never authoritative. It preserves:

- identities and versions;
- objective and working mode;
- hard constraints and accepted/rejected decisions;
- evidence references and route-plan identity;
- checkpoint and human-review revision;
- branch/source SHA;
- budgets, next action, rollback and claim boundary.

It rejects transcript content from control projections, prompts, hidden reasoning, raw provider output, keys, tokens, passwords and DSNs. It refreshes when authoritative revision changes and rejects stale fingerprints/source revisions.

## Competition and Energy

Python creates four immutable candidates:

- baseline;
- aggressive, bounded by known lower evidence limits;
- conservative, bounded by known upper evidence limits;
- synthesized, using bounded deterministic confidence weighting.

Missing hours are hard missing evidence. Material divergence creates conflict/escalation. The selected candidate ID and Energy snapshot persist across resume. Independent coherence validation may veto synthesis. No model owns authoritative arithmetic.

## API and rollback

| Path | Runtime | Status |
|---|---|---|
| `/api/v1/estimate/graph` | Session 14 supervised | preserved rollback |
| `/api/v1/estimate/graph/reviewed/start` | Session 13 Plus reviewed | preserved rollback |
| `/api/v1/estimate/graph/unified` | consolidated | additive candidate |
| `/api/v1/estimate/graph/unified/control` | allowlisted control projection | additive candidate |

Each composition root is isolated. Unified startup failure must not disable reviewed or supervised runtimes.

## Observability and privacy

Unified spans:

```text
session13_14_plus.graph.run
session13_14_plus.graph.node
```

Allowlisted telemetry may contain graph/policy version, route destination, reason code, capability-record IDs, candidate IDs, Energy snapshot ID, Critic/Boss disposition, review status/revision and delta keys.

It excludes transcript, prompts, raw model output, hidden reasoning, credentials and connection strings. Control responses expose projection models, not raw graph state.

## Evidence boundary

Supported after exact-head CI, PostgreSQL and container jobs succeed:

> The repository contains a separately versioned unified graph that semantically consolidates Session 13 Plus reviewed orchestration with Session 14 Plus supervised HITL, capability-authorized routing, context integrity and deterministic Energy-Aware competition while preserving rollback paths.

The Control Room implementation is deterministic-contract-tested, but no browser screenshot or human-visible smoke artifact is currently recorded. Provider current reachability is also unverified when the credentialed job is skipped.

Not established:

- superiority over reviewed or supervised paths;
- production promotion;
- current reachability of every calibrated provider;
- lossless context compaction;
- automatic historical-checkpoint migration;
- browser-validated UI usability;
- authorization to merge or retire rollback paths.
