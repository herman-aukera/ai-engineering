# EACODE — Energy-Aware Code ⚡

EACODE is the coding-governance specialization of the Energy-Aware architecture. It turns a coding specification/proposal into typed evidence, deterministic hard gates and critics, a governed decision, protected operator authorization and reevaluation.

Canonical branch: `EACODE`. It is a peer product to the estimator `main` and `EACHAT`; it must not be merged into `main` as a feature branch.

## Production entry point

```text
app.eacode.production_app:app
```

Canonical production namespace: `/api/v1/eacode/*`. The broad coursework application retains `/eacode/*` compatibility; production deploys only the isolated versioned composition root.

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

## Identity and durable authority

Production requires `EACODE_DATABASE_URL` and `EACODE_SESSION_SIGNING_KEY`. Proposals, ownership, receipts, replay protection, execution reservations and reevaluated results are authoritative PostgreSQL state. The versioned migration is `energy_core/migrations/0001_eacode_beta_authority.sql`; SQLite is compatibility/test-only.

`/health` remains a cheap local liveness probe. `/ready` separately performs a bounded authority-store availability check and returns 503 when PostgreSQL authority is unavailable, so a live process with a dead authoritative database stops receiving production traffic without invoking a model/provider.

## Isolated production artifact

The deployable dependency closure is frozen independently from the coursework environment:

```text
deploy/eacode/pyproject.toml
deploy/eacode/uv.lock
deploy/eacode/uv.lock.sha256
```

`scripts/eacode_export_production_requirements.py` verifies the lock digest, refuses monorepo-only AI/notebook/UI dependencies and exports hashed requirements. CI, the PostgreSQL restart canary and immutable image release all consume this same contract.

The machine-readable portfolio mapping is `docs/energy_aware_product_manifest.json`. `scripts/verify_energy_aware_protocol.py` proves protocol/accountability invariants, while `scripts/product_split_dry_run.py` traces the production import closure and materializes a compile-checked product-only tree without peer-product imports.

## Observability

Production emits the neutral `energy-aware.event.v1` operational envelope through `app/energy_aware_observability.py`. Events carry request correlation, stable reason codes, outcome and duration; prompts, transcripts, authorization values and secrets are forbidden event attributes.

## Deterministic validation

```bash
cd estimador-cag
OPENAI_API_KEY=test DEEPSEEK_API_KEY=test KIMI_API_KEY=test uv run pytest -q -m "not live_provider"
python scripts/eacode_export_production_requirements.py
python scripts/verify_energy_aware_protocol.py
python scripts/product_split_dry_run.py
uv run python scripts/session15_eacode_production_contract.py
```

Real provider proof remains isolated in `.github/workflows/live-smoke.yml`. PostgreSQL authority/restart evidence runs in `.github/workflows/eacode-postgres-integration.yml`.

## Production topology

```text
Internet
-> Caddy :80/:443
-> private EACODE container :8000
-> signed actor / exact-scope authority
-> durable PostgreSQL / RDS
-> outbound provider HTTPS only in explicitly live paths
```

Release images are non-root, immutable and digest-addressed. Deploy applies the explicit authority migration, replaces the service and waits for `/ready`; rollback uses a previous post-migration digest.

## Execution claim boundary

The governed beta proves **simulated execution only**. Secure-runner research must not be exposed as arbitrary untrusted-code execution until filesystem/process/network/resource isolation and cleanup evidence are independently proven.

## Remaining external production gates

- real staging on EC2/RDS and DNS/TLS;
- RDS backup/restore and migration rollback exercise;
- real OIDC/identity-provider adapter;
- production SLOs, alerts and collected production telemetry;
- proven sandbox for arbitrary untrusted code.

EACODE is production-oriented and repository-hardened, but it is **not yet live production-ready**. Real deployment evidence is still required before making that claim.

## Canonical documentation

- `docs/ENERGY_AWARE_PROTOCOL_V1.md`
- `docs/energy_aware_product_manifest.json`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/OPERATIONS.md`
- `docs/RELEASE.md`
- `docs/REPO_SPLIT_MANIFEST.md`
- `docs/history/README.md`
