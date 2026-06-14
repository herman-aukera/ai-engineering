# Energy Aware Code Critic Coverage

The critic coverage matrix reports which energy-policy constraints are enforced by deterministic critics and which constraints are still policy-only.

It is intentionally not a success theater document. Policy-only constraints remain visible because EACODE has not yet added shell execution, git branch readers, provenance scanners, or executor roles.

## Command

```bash
python -m energy_core.critic_coverage_cli \
  --format markdown \
  --fail-on-unclassified
```

From the repository root:

```bash
estimador-cag/.venv/bin/python -m energy_core.critic_coverage_cli \
  --policy .energy/specs/0001-energy-policy-ledger/energy-policy.yaml \
  --format markdown \
  --fail-on-unclassified
```

## Interpretation

- `enforced` means a deterministic critic maps the constraint to violations.
- `policy_only` means the policy declares the constraint, but no deterministic runtime reader exists yet.
- `unclassified` means the policy and coverage table have drifted and must be repaired.

## Non-goals

- No shell execution.
- No provider calls.
- No adapter approval.
- No fake full-coverage claims.
