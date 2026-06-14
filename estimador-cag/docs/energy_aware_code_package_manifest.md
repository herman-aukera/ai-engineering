# Energy Aware Code Package Manifest

Status: incubator judge layer.

Purpose: describe the files that should move into a future standalone Energy Aware Code repository without performing the extraction.

The manifest is deterministic and metadata-only. It records file groups, paths, sizes, SHA-256 hashes, copy roots, and explicit non-goals. It does not embed source file contents, execute shell commands, call providers, or mutate the decision ledger.

## From `estimador-cag`

    uv run python -m energy_core.package_cli \
      --project-root . \
      --format markdown \
      --fail-on-incomplete

## From the repository root

    estimador-cag/.venv/bin/python -m energy_core.package_cli \
      --project-root estimador-cag \
      --format markdown \
      --fail-on-incomplete

## CI smoke

The package manifest command is covered by:

    uv run python scripts/energy_core_package_smoke.py

The smoke verifies project-root and repository-root usage and expects the manifest to report `Complete: True`.

## What belongs in the future standalone package

Copy roots reported by the manifest:

1. `energy_core/`
2. `.energy/`
3. `docs/energy_aware_code_*.md`
4. `scripts/energy_core_*.py`

## What is intentionally not included

1. No shell execution.
2. No provider clients or API keys.
3. No Aider, Cline, or OpenCode adapter implementation.
4. No FastAPI or Streamlit layer.
5. No Energy Aware Chat bridge.

The manifest is a readiness and packaging aid, not an extraction command.
