# EACODE — Energy-Aware Code ⚡

EACODE is the coding-governance specialization of the Energy-Aware architecture. It turns a coding specification/proposal into typed evidence, deterministic hard gates and critics, a governed decision, protected operator authorization and reevaluation.

Canonical branch: `EACODE`. It is a peer product to the estimator `main` and `EACHAT`; it must not be merged into `main` as a feature branch.

## Production entry point

```text
app.eacode.production_app:app
```

Canonical production namespace:

```text
/api/v1/eacode/*
```

The broad coursework application retains `/eacode/*` compatibility. Production deploys only the isolated versioned composition root.

## Governed beta lifecycle

```text
signed session
-> tenant-owned inert coding proposal
-> deterministic hard gates + semantic critics
-> repaired effective proposal
-> deterministic Boss disposition
-> operator/admin authorization
-> exact-scope, short-lived, one-use receipt
-> atomic execution reservation
-> simulated execution
-> deterministic reevaluation
-> integrity-checked PostgreSQL record
```

Provider/model output is evidence, not authority. Requested, planned and actually served provider identities remain distinct. Client-controlled `human_authorization` is rejected.

Common portfolio terminology is defined by `docs/ENERGY_AWARE_PROTOCOL_V1.md`.

## Production state truth

Production EACODE is **stateful** because proposals, ownership, authorization receipts, nonce/replay protection, execution reservations and reevaluated results are authoritative.

Production therefore requires:

```text
EACODE_DATABASE_URL
EACODE_SESSION_SIGNING_KEY
```

The versioned PostgreSQL migration is `energy_core/migrations/0001_eacode_beta_authority.sql`. SQLite remains only local/test/coursework compatibility.

## Deterministic validation

```bash
cd estimador-cag
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test \
uv run pytest -q -m "not live_provider"
uv run python scripts/session15_eacode_production_contract.py
uv run python scripts/verify_repo_split_readiness.py
```

Real provider proof remains isolated in `.github/workflows/live-smoke.yml`. PostgreSQL authority/restart evidence runs separately in `.github/workflows/eacode-postgres-integration.yml`.

## Production topology

```text
Internet
-> Caddy :80/:443
-> private EACODE container :8000
-> durable PostgreSQL / RDS
-> outbound provider HTTPS only in explicitly live paths
```

Release images are non-root, immutable and digest-addressed. Deploy runs the explicit authority migration, replaces the service and waits for `/ready`; rollback uses a previous post-migration digest.

## Execution claim boundary

The governed beta still proves **simulated execution only**. Existing secure-runner research must not be exposed as arbitrary untrusted-code execution until filesystem/process/network/resource isolation and cleanup evidence are sufficient.

## Current production blockers

- real staging on EC2/RDS and DNS/TLS;
- RDS backup/restore and migration rollback exercise;
- real OIDC/identity-provider adapter;
- production SLOs, alerts and telemetry;
- proven sandbox for arbitrary untrusted code;
- isolated product dependency lock/minimal runtime dependency set rather than the current monorepo-wide frozen dependency source.

EACODE is therefore production-oriented and repository-hardened, but not yet truthful to call live production-ready.

## Canonical documentation

- `docs/ARCHITECTURE.md`
- `docs/ENERGY_AWARE_PROTOCOL_V1.md`
- `docs/SECURITY.md`
- `docs/OPERATIONS.md`
- `docs/RELEASE.md`
- `docs/REPO_SPLIT_MANIFEST.md`
- `docs/history/README.md`
