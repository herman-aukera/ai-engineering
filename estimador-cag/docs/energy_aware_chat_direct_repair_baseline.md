# EACHAT direct repair baseline

Status: verified Phase 0 audit record. No runtime implementation is changed by this commit.

## Repository checkpoint

```text
repository=herman-aukera/ai-engineering
source_branch=EACHAT
baseline_sha=ec9cd03883502c0f5c288ccdd0d5195492b72231
repair_branch=repair/eachat-foundation-and-release-evidence
source_pr=#5
source_pr_state=open,mergeable,unmerged
exact_head_ci_runs=29808189100,29808187411
exact_head_ci=success
reported_suite=624 passed, 7 skipped
```

The existing green CI proves deterministic regression health. It does not by itself prove durable PostgreSQL persistence, application-lifetime HTTP replay, complete human interrupt/resume, integrated observability, integrated citation enforcement, provider-adapter completeness, context-compaction runtime, multi-agent runtime, live quality improvement, browser security, restart continuity, public deployment, or production readiness.

## Product boundary

EACHAT owns general-purpose chat interpretation, evidence routing, candidate generation, critic panels, authoritative energy, bounded repair, clarification/refusal/rejection/escalation, Decision Ledger, Energy Card, graph-backed API, chat persistence, human gates, provider routing, context compaction, observability, UI, and chat evaluation.

This repair branch must not modify EACODE, EACORE, Session 13/14 branches, `main`, or `finalproject-GGC`.

## Evidence map

| Milestone | Current implementation evidence | Integration evidence | Test/CI evidence | Audit classification | Missing evidence |
|---|---|---|---|---|---|
| 0–9 | Typed graph state, evidence routing, immutable candidates, critic/score/decision nodes, bounded repair, six dispositions, Decision Ledger, Energy Card v2, final projection | Canonical graph execution exists | Broad deterministic suite and exact-head CI green | implemented | Continue regression protection |
| 10 Graph API | V2 contracts, deterministic/live routes, application service | Routes call one graph; legacy routes preserved | V2 tests and CI green | partial | Route-specific execution contract, explicit fallback authorization, V2 feature flag, truthful no-provider awaiting-evidence projection |
| 11 In-memory checkpoint | `InMemoryCheckpointer` and graph-level replay tests | Checkpointer can be injected into graph | Internal thread/replay tests | partial | Shared application-lifetime checkpointer, separate HTTP-request replay, authoritative thread-state/replay endpoint |
| 12 Human gates | Typed human action, graph interrupt, Command resume | Runtime accepts resumed action | Focused tests | partial | Production revision validation in resume path, typed public resume API, stale/wrong-thread/duplicate action tests against production code |
| 13 PostgreSQL | Postgres wrapper, DDL string, optional integration tests | No default application wiring; retention/redaction placeholders | Seven tests skipped without database | partial | Required PostgreSQL CI job, applied migrations, persisted redaction inspection, retention execution, restart/reopen/resume proof |
| 14 Observability | Span and aggregate models/helpers | Not integrated into actual graph nodes/state/API projection | Unit tests | documented/partial | Node spans from real execution, safe errors, API projection, graph-linked metrics |
| 15 Evidence hardening | Body hash, integrity, freshness and citation helper functions | Not integrated into retrieval/critic/decision/finalization | Unit tests | documented/partial | Decision impact, fabricated-citation handling, ledger/final projection integration |
| 16 UI | Same-origin V2 static demo | Calls V2 API | Route test | partial | Real thread replay, browser automation, XSS-safe rendering, disabled-feature behavior |
| 17 Providers | DeepSeek live seam; typed catalog | Kimi/OpenAI unavailable | Fake-provider tests | partial | Correct temporal facts, explicit API surfaces, no-fallback adapter mode, separate Kimi/OpenAI adapters, bounded live proof |
| 18 Context/multi-agent | Typed policies, snapshots and budgets | Module explicitly defers runtime | Unit tests | documented | Either implement runtime with budgets/invariants or downgrade claims truthfully |
| 19 Evaluation | Rubric and scoring framework | No completed fixed-corpus product run | Unit tests | framework implemented; evaluation blocked | Versioned corpus, deterministic baseline comparison, optional matched live evaluation |
| 20–21 Release/deployment | Hard-coded claim objects and readiness helper | Not connected to CI, DB, browser, deployment or provider evidence | Shape tests | scaffolding | Evidence collectors, contradiction/staleness states, browser/security/restart gates, deployment evidence |

## Verified foundational defects to convert into regression tests

1. External V2 requests expose caller-controlled `execution_profile`; routes silently overwrite contradictory values instead of using route-specific contracts or rejecting conflicts.
2. No explicit `allow_provider_fallback` contract exists.
3. The fallback-capable baseline seam can invoke a provider ladder when its provider supports fallback.
4. The V2 API lacks a tested configuration-controlled rollback feature flag.
5. Awaiting-evidence responses can report a deterministic provider/model despite zero candidate-provider calls.
6. A new in-memory checkpointer can be created per request, so public HTTP replay is not proven.
7. Human action revision validation is not proven in the production resume path.
8. PostgreSQL redaction and retention are contracts/placeholders rather than enforced behavior.
9. Observability and evidence-hardening helpers are not wired into actual graph execution.
10. Provider catalog temporal facts and API-surface distinctions require revalidation.
11. Context and multi-agent modules explicitly defer runtime while roadmap/docs mark them implemented.
12. Release claims are hard-coded rather than collected from evidence.
13. Deployment readiness does not include every declared prerequisite in the final readiness calculation.
14. The V2 browser demo uses dynamic HTML rendering patterns that require XSS-safe correction and browser proof.

## Repair sequence

1. M10 route/fallback/feature-flag/awaiting-evidence contracts.
2. Application-lifetime checkpointing and real HTTP replay.
3. Production human revision validation and typed resume API.
4. PostgreSQL service-container CI, migrations, redaction, retention, restart and resume.
5. Graph-integrated observability and evidence integrity.
6. Provider catalog correction and adapter boundaries.
7. Milestone 18 truth gate.
8. Fixed-corpus evaluation.
9. Evidence-driven release audit.
10. Browser, security, restart and deployment gates.
11. Documentation reconciliation.

## Safety and rollback

- Work occurs only on `repair/eachat-foundation-and-release-evidence`.
- The branch started exactly at `ec9cd03883502c0f5c288ccdd0d5195492b72231`.
- Each coherent repair slice receives its own commit after applicable gates pass.
- No merge occurs without explicit user approval.
- `EACHAT` remains the rollback surface throughout the repair program.
