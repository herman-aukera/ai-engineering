# Energy Aware Code Reviewer Snapshot

The reviewer snapshot is a teacher and future-repository review index for the Energy Aware Code incubator branch.

It does not execute commands, call LLM providers, or approve adapter actions. It links the deterministic review surfaces that already exist in the judge layer.

## Command

From `estimador-cag`:

```bash
uv run python -m energy_core.reviewer_cli \
  --project-root . \
  --format markdown \
  --fail-on-incomplete
```

From repository root:

```bash
estimador-cag/.venv/bin/python -m energy_core.reviewer_cli \
  --project-root estimador-cag \
  --format markdown \
  --fail-on-incomplete
```

## What it links

The snapshot points reviewers to:

1. Release readiness.
2. Package manifest.
3. Audit pack.
4. Schema bundle.
5. Example matrix.
6. Constraint index.
7. Smoke suite.

## Non-goals

The snapshot does not include shell execution, provider calls, Cline, Aider, OpenCode, auto-commit, or auto-push behavior.
