# Energy-Aware Estimator Architecture

## Product boundary

`main` owns estimation semantics. It is not EACHAT and not EACODE, but implements the same Energy-Aware governance philosophy.

Production composition root: `app.estimator.production_app:app`.

```text
Request
  -> UNDERSTAND: reformulation + semantic policy
  -> GATHER_EVIDENCE: structure/retrieval
  -> PROPOSE: deterministic estimate + candidate competition
  -> CRITIQUE: reliability + review critic + coherence
  -> SCORE/DECIDE: deterministic Energy/review/Boss policy
  -> REPAIR: bounded selective recovery
  -> AUTHORIZE: persistent human review when required
  -> RECORD: proposal, trace, decision evidence
```

## Authority

The unified supervisor owns transitions. Specialists and models return typed evidence/proposals. Deterministic Python owns arithmetic, hard constraints, route budgets and machine disposition. Human review owns explicitly protected approval/adjust/reject transitions.

## State

Authoritative graph/HITL state uses stable `estimate:<estimation_id>` identity and PostgreSQL-backed checkpointing. Replay-sensitive reducers deduplicate identical replay and reject conflicting identities.

## Production boundary

Only `/api/v1/estimate/graph/unified...` is mounted in the isolated production app. Historical demos, embeddings/search exercises, older graph versions and coursework compatibility APIs remain outside the production process.

## Portfolio mapping

The neutral stages and contracts are defined in `ENERGY_AWARE_PROTOCOL_V1.md`. Domain-specific estimator state and policies remain product-local.
