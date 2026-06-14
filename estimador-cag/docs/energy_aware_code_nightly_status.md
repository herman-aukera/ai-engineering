# Energy Aware Code Nightly Status

The nightly status pack is a non-mutating maintainer checkpoint for overnight work.

It groups five medium review milestones into one command:

1. Policy health.
2. Evidence completeness.
3. Command safety surface.
4. Release and export readiness.
5. Maintainer handoff.

## Command

```bash
python -m energy_core.nightly_status_cli \
  --project-root . \
  --format markdown \
  --fail-on-incomplete
```

From the course repository root:

```bash
estimador-cag/.venv/bin/python -m energy_core.nightly_status_cli \
  --project-root estimador-cag \
  --format markdown \
  --fail-on-incomplete
```

## Safety boundary

The nightly status pack does not execute shell actions, call providers, approve adapter execution, or append to the decision ledger.

It reads existing policy, evidence, package manifest, and command catalog data, then produces a deterministic review summary.
