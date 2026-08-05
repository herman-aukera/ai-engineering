# Energy Aware Chat completion roadmap

## Current status

Milestones 0-21 are implemented on `EACHAT`. There is no remaining repository-controlled implementation milestone in this roadmap. The current evidence matrix, historical defect disposition, claim boundary, and external runbooks are consolidated in `docs/energy_aware_chat_current_audit.md`.

Implemented product layers include typed graph state and reducers, evidence routing, provider boundaries, deterministic critics and decisions, bounded repair, six dispositions, Decision Ledger, Energy Card, graph-backed APIs, explicit fallback authorization, V2 rollback, honest pending responses, authoritative replay, thread isolation, human revision guards, PostgreSQL persistence, encrypted conversation memory, observability, evidence integrity, safe browser UI, bounded provider/context/orchestration runtimes, fixed-corpus evaluation, security/dependency audit, and container restart proof.

## External completion boundary

The following are not implementation milestones and remain evidence-gated:

1. credentialed live-provider smoke;
2. matched same-task live quality benchmark;
3. public deployment and smoke evidence;
4. incident response and real-user telemetry;
5. human release and integration decisions.

Release claims remain `release_claims_blocked_missing_evidence` and `measurement_only_no_quality_claim`. Do not claim provider superiority, routing/orchestration improvement, context-rot prevention, public deployment, production readiness, or production telemetry.

PR #5 is open, unmerged, and currently conflicts with `main`. Conflict resolution is a separate authorized integration task; it must not occur as a side effect of product completion.
