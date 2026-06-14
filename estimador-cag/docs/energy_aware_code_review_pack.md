# Energy Aware Code Review Pack

Status: active  
Scope: EACODE incubator reviewer handoff

## Purpose

The review pack exports generated Markdown artifacts into one output directory.

Use it when you want to hand a compact reviewer folder to a teacher, future repo reviewer, or future extraction pass.

The pack is generated from deterministic repository artifacts.

It does not:

- execute shell actions,
- call LLM providers,
- approve adapter execution,
- append to the decision ledger.

## Command

From `estimador-cag`:

```bash
uv run python -m energy_core.review_pack_cli \
  --output-dir /tmp/eacode-review-pack \
  --format markdown \
  --fail-on-incomplete
```

From repository root:

```bash
estimador-cag/.venv/bin/python -m energy_core.review_pack_cli \
  --project-root estimador-cag \
  --output-dir /tmp/eacode-review-pack \
  --format markdown \
  --fail-on-incomplete
```

## Generated files

The current pack writes:

- `README.md`
- `reviewer_snapshot.md`
- `release_readiness.md`
- `package_manifest.md`
- `command_catalog.md`

## Smoke coverage

The command is protected by:

```bash
uv run python scripts/energy_core_review_pack_smoke.py
```

The smoke script verifies that the command works from repository-root style invocation and that every generated file exists and is non-empty.
