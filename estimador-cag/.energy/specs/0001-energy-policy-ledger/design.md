# Design

spec_id: 0001-energy-policy-ledger
status: active
owner: Gonzalo / AI Engineer LIDR

## Architecture summary

The first Energy Aware Code slice is a deterministic evaluator. It reads policy, candidate state, and evidence records, then produces a typed decision and appends it to a ledger.

## Core modules

| Module | Responsibility |
| --- | --- |
| `energy_core.models` | Typed contracts |
| `energy_core.policy` | Policy loading |
| `energy_core.state` | Candidate state loading |
| `energy_core.evidence` | Evidence JSONL loading |
| `energy_core.critics` | Deterministic violation detection |
| `energy_core.scorer` | Energy aggregation |
| `energy_core.decider` | Decision precedence |
| `energy_core.ledger` | Append-only decision records |
| `energy_core.cli` | User-facing CLI entry point |

## Boundary

Adapters and model calls are deliberately deferred until the deterministic judge exists.
