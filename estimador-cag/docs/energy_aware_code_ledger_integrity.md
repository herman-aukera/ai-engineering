# Energy Aware Code Ledger Integrity

The ledger integrity surface inspects the append-only decision ledger without
mutating it.

## Command

```bash
python -m energy_core.ledger_integrity_cli \
  --ledger .energy/specs/0001-energy-policy-ledger/decisions.jsonl \
  --format markdown \
  --fail-on-invalid
```

## What it checks

- The ledger file exists.
- Each non-empty JSONL line parses as an `EnergyDecision`.
- `energy_delta` matches `energy_after - energy_before`.
- Decision counts can be summarized deterministically.
- Duplicate candidate IDs are surfaced as review warnings.

## Current expected state

The committed course ledger may be empty before real accepted decisions exist.
An empty existing ledger is integrity-clean.

## Non-goals

- It does not append to the decision ledger.
- It does not execute shell actions.
- It does not call LLM providers.
- It does not prove git-level append-only history by itself.
