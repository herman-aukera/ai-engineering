# Energy Aware Code command catalog

Status: incubator artifact.

Purpose: provide one reviewer-friendly list of supported Energy Core commands, their mutation behavior, smoke coverage, and non-goals.

## Command

From `estimador-cag`:

```bash
uv run python -m energy_core.command_catalog_cli --format markdown --fail-on-incomplete
```

From the repository root:

```bash
estimador-cag/.venv/bin/python -m energy_core.command_catalog_cli --format markdown --fail-on-incomplete
```

## What it proves

The command catalog should show:

1. every supported public command surface,
2. which commands mutate the append-only decision ledger,
3. which commands support dry-run behavior,
4. whether commands are supported from the repository root,
5. the smoke script that protects each command family.

## Current mutation boundary

Only `evaluate` mutates the ledger by default.

`evaluate --dry-run` does not mutate the ledger.

Review, validation, manifest, schema, release, package, reviewer, example, and constraint commands do not mutate the ledger.

## Non-goals

The command catalog does not execute shell actions.

The command catalog does not call LLM providers.

The command catalog does not approve adapter execution.
