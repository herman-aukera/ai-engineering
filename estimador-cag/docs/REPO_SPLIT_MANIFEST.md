# Repository Split Manifest — EACODE

Future repository candidate: `energy-aware-code`.

## Retain

- `app/eacode/production_app.py` and EACODE router/product API;
- active `energy_core/` coding-governance modules required by import closure;
- PostgreSQL authority store + versioned migrations;
- EACODE tests/specs/evaluations and secure-runner evidence still relevant to the product;
- `deploy/eacode/` production files;
- `.env.example`;
- deterministic CI, PostgreSQL restart integration, live-provider smoke and image release workflows;
- canonical docs and current SDD/spec evidence.

## Exclude/retire after dependency proof

- estimator application/runtime/UI;
- EACHAT modules;
- old session-specific demos/evals unrelated to coding governance;
- duplicated historical Energy Core scaffold/reviewer/export scripts once current contracts replace them;
- stale branch/PR instructions and generated evidence not required by an active release contract.

## Production entry point

`app.eacode.production_app:app`

## External state

PostgreSQL is authoritative for proposals, ownership, receipts, replay protection, reservations and results. Session-signing material and provider credentials are runtime secrets.

## Remaining split blockers

The production Docker requirement export still starts from the monorepo-wide frozen project dependency set. Before physical extraction, derive and lock a minimal EACODE runtime dependency manifest from the proven import closure and re-run vulnerability/SBOM/container gates. Secure execution remains simulated unless sandbox evidence is upgraded.

Run `python scripts/verify_repo_split_readiness.py` before extraction.
