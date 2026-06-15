# Energy Aware Code Acceptance Trace

The acceptance trace connects the baseline spec acceptance criteria to the proof surfaces that currently protect them.

It is a reviewer artifact, not an executor.

## Command

```bash
python -m energy_core.acceptance_trace_cli \
  --project-root . \
  --format markdown \
  --fail-on-incomplete
```

## What it checks

- Acceptance criteria are parsed from `.energy/specs/0001-energy-policy-ledger/acceptance.md`.
- Each criterion is mapped to evidence, focused tests, and reviewer surfaces.
- Required acceptance evidence must have trusted passing records.
- Missing trace links make the report incomplete.

## Non goals

- It does not execute shell actions.
- It does not call LLM providers.
- It does not mutate evidence or the decision ledger.
