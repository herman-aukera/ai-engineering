# Energy Aware Code Policy Roadmap

The policy roadmap reports constraints that are intentionally policy-only in the current judge layer.

It is designed to prevent fake coverage claims.

## Command

```bash
python -m energy_core.policy_roadmap_cli \
  --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
  --format markdown \
  --fail-on-incomplete
```

## What it reports

- policy-only constraint IDs
- current execution boundary
- unblocker required before enforcement
- future evidence type
- future implementation slice

## Current boundary

The current EACODE incubator is a deterministic judge. It does not execute shell commands, read live git state, scan provenance, call providers, or approve adapter execution.

## Non-goals

- It does not execute shell actions.
- It does not call LLM providers.
- It does not approve adapter execution.
- It does not turn policy-only constraints into fake enforced constraints.
