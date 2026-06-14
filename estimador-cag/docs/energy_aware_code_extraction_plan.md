# Energy Aware Code extraction plan

Status: incubator plan.

Scope: keep Energy Aware Code inside `herman-aukera/ai-engineering` while the AI Engineering course continues, then extract when the product boundary is stable.

## Why not extract immediately

The current branch is intentionally an incubator branch because later sessions may still add useful material around RAG, agents, evaluation, observability, deployment, and final project requirements.

Immediate extraction would create unnecessary repo choreography before the product shape is stable.

## Current product boundary

Energy Aware Code currently owns:

1. `.energy/specs/0001-energy-policy-ledger/`.
2. `energy_core/`.
3. `scripts/energy_core_smoke.py`.
4. `scripts/energy_core_boundary_check.py`.
5. `tests/test_energy_core_*.py`.
6. `docs/energy_aware_code_*.md`.

Energy Aware Code must not depend on:

1. `app/`.
2. FastAPI routes.
3. Streamlit.
4. DeepSeek, OpenAI, Kimi, Anthropic, LiteLLM, or provider runtime clients.
5. Redis or app cache infrastructure.
6. Aider, Cline, OpenCode, or shell execution adapters.
7. Energy Aware Chat internals.

## Extraction readiness gates

Before extracting to a dedicated repository, these must pass:

1. `uv run ruff check energy_core tests scripts`.
2. `uv run python -m py_compile $(find energy_core tests scripts -name '*.py' -type f)`.
3. `uv run pytest -q tests/test_energy_core_*.py`.
4. `uv run python scripts/energy_core_boundary_check.py`.
5. `uv run python scripts/energy_core_smoke.py`.
6. Documentation explains how to run the CLI without course-specific services.
7. The package boundary check shows no forbidden app, UI, provider, cache, or adapter imports.

## Extraction target repository shape

Suggested future repository:

    energy-aware-code/
      .energy/
      energy_core/
      scripts/
      tests/
      docs/
      pyproject.toml
      README.md
      LICENSE

## Extraction sequence

1. Freeze the incubator branch at a known green commit.
2. Copy only the Energy Aware Code boundary files.
3. Create a dedicated `pyproject.toml` with minimal deterministic dependencies.
4. Port CI with ruff, py_compile, pytest, boundary check, and smoke.
5. Preserve the incubator commit reference in the new README.
6. Add adapters only after the extracted judge remains green.

## Explicit non-goals before extraction

1. No shell executor.
2. No Aider adapter.
3. No Cline adapter.
4. No OpenCode adapter.
5. No IDE extension.
6. No provider calls.
7. No Chat bridge.

## Decision rule

Extract only when the judge layer is stable enough that future work can happen as product evolution rather than coursework recovery.
