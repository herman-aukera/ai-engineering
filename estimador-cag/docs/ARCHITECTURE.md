# EACODE Architecture

## Product boundary

EACODE owns specification/proposal governance, repository/tool evidence, coding critics, deterministic Boss disposition, actor authorization, execution evidence and reevaluation. It does not own conversational answer semantics or estimator budgeting.

Production composition root: `app.eacode.production_app:app`.

```text
Specification
-> UNDERSTAND: normalize coding proposal/spec
-> GATHER_EVIDENCE: repository/provider/tool evidence
-> PROPOSE: inert proposal / effective repaired revision
-> CRITIQUE: deterministic hard gates + semantic jury/critics
-> SCORE/DECIDE: deterministic Boss
-> REPAIR: explicit effective proposal revision
-> AUTHORIZE: signed actor + exact-scope one-use receipt
-> EXECUTE: simulated unless a separately proven sandbox is enabled
-> VERIFY: deterministic reevaluation + cleanup/execution evidence
-> RECORD: PostgreSQL authority record
```

## Authority

Models/providers/tools cannot approve themselves or create process authority. Server-owned actor identity, deterministic policy and one-use authorization receipts protect the transition into execution.

## State

Production authority uses PostgreSQL. SQLite is compatibility/test-only. The application verifies the expected migration before readiness. Receipt consumption and execution reservation are transactional and replay-safe.

## Portfolio mapping

Neutral types/vocabulary follow `ENERGY_AWARE_PROTOCOL_V1.md`; coding specs, patch gates, command rules, provider registry and sandbox semantics remain EACODE-specific.
