# EACHAT Architecture

## Product boundary

EACHAT owns answer generation/governance, grounding, repair, Energy Cards, Decision Ledger, chat replay and human continuation. It does not own repository mutation or coding-agent execution.

Production composition root: `app.energy_chat.production_app:app`.

```text
Request
-> UNDERSTAND: interpretation + request policy
-> GATHER_EVIDENCE: source need, project retrieval, citation validation
-> PROPOSE: answer candidate
-> CRITIQUE: deterministic critic panel
-> SCORE/DECIDE: Energy + deterministic disposition
-> REPAIR: bounded answer repair
-> AUTHORIZE: durable human interrupt/resume when protected
-> RECORD: answer, Energy Card, Decision Ledger, trace
```

## Production API isolation

`app.energy_chat.production_router` is self-contained and imports only V2 runtime/contracts. Legacy `router.py` contains historical evaluation/benchmark/MVP paths for compatibility but is not a production dependency.

## State

PostgreSQL is authoritative for strict graph checkpoints and encrypted conversations. Runtime records can be reconstructed from durable checkpoints after process replacement. Replay/idempotency and human-action guards prevent conflicting reuse.

## Portfolio relationship

Neutral concepts follow `ENERGY_AWARE_PROTOCOL_V1.md`; chat-specific graph state, evidence rules, Energy Cards and answer policy remain local to EACHAT.
