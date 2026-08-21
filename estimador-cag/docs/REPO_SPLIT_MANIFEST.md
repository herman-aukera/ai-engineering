# Repository Split Manifest — Energy-Aware Estimator

Future repository candidate: `energy-aware-estimator`.

## Retain

- `app/estimator/`
- estimator-required `app/generation/`, `app/services/`, `app/schemas/`, `app/persistence/`, `app/prompts/`, middleware/config dependencies discovered by import closure;
- canonical unified estimator router;
- production Docker/deploy files;
- estimator tests/evals required by current contracts;
- `pyproject.toml`, `uv.lock`, `.env.example`;
- deterministic CI, provider evaluation and image release workflows;
- canonical docs plus relevant SDD/history index.

## Exclude from the future production repository unless dependency analysis proves otherwise

- peer-product EACHAT/EACODE modules;
- old Streamlit/session demos not used by the current product;
- superseded session-only graph/API generations after compatibility retirement;
- generated historical evidence not required by an active contract;
- stale branch/PR instructions.

## Production entry point

`app.estimator.production_app:app`

## External state

Durable PostgreSQL is authoritative for graph/HITL state. Redis is runtime infrastructure. Runtime provider credentials are secrets.

## Remaining split blockers

The current monorepo still contains historical coursework modules that are transitively imported by the unified estimator and therefore need an import-closure/dependency cleanup before a minimal copy can be produced. Multi-tenant identity/ownership is also a product-readiness blocker, not a repository-split dependency.

Run `python scripts/verify_repo_split_readiness.py` before any physical split.
