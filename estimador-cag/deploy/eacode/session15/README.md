# EACODE production envelope

The isolated production application is `app.eacode.production_app:app`. It publishes only EACODE plus operational probes under the explicit `/api/v1/eacode/*` product namespace.

## Production truth

EACODE is **not stateless anymore** once the governed beta API owns proposals, authorization receipts, replay protection, execution reservations and reevaluation records. Production therefore requires durable PostgreSQL through `EACODE_DATABASE_URL`.

SQLite remains only a coursework/local/test compatibility backend through the broad application. It is never configured by production Compose.

## Authority lifecycle

```text
signed session
-> tenant-owned inert proposal
-> deterministic gates and critics
-> repaired effective proposal
-> operator/admin authorization
-> one-use exact-scope receipt
-> atomic execution reservation
-> simulated execution
-> deterministic reevaluation
-> integrity-checked PostgreSQL result
```

Execution is still simulated. PostgreSQL persistence does not imply arbitrary code is safe to execute.

## Canonical API

- `GET /api/v1/eacode/status`
- `GET /api/v1/eacode/capabilities`
- `POST /api/v1/eacode/select`
- `GET /api/v1/eacode/ui`
- governed `/api/v1/eacode/demo...` proposal/authorization/execution routes.

The broad coursework app retains `/eacode/*` compatibility but is not the production process.

## Runtime requirements

- `EACODE_IMAGE`: immutable OCI digest.
- `PUBLIC_HOST`: public DNS name.
- `EACODE_DATABASE_URL`: durable PostgreSQL/RDS endpoint.
- `EACODE_SESSION_SIGNING_KEY`: at least 32 bytes, injected only at runtime.

Application startup verifies that migration `0001_eacode_beta_authority` is already present. `deploy.sh` explicitly runs the migration before replacing the app.

## Health semantics

- `/startup`: production lifespan completed.
- `/health`: cheap local liveness; no provider or database call.
- `/ready`: startup completed with verified PostgreSQL authority schema.
- `/version`: safe version and Git SHA.

## Persistence and replacement proof

`.github/workflows/eacode-postgres-integration.yml` provisions PostgreSQL, applies the migration, runs store-level integration, starts the real container, creates/authorizes/executes a governed proposal, destroys the application container, recreates it against the same database and verifies the completed record survives.

This proves application-container replaceability. It is not yet evidence of a real EC2 Spot interruption or RDS backup/restore.

## Build, deploy and rollback

Release remains keyless with respect to model providers and emits an immutable image digest. Deployment rejects mutable tags, applies the versioned PostgreSQL migration and waits for `/ready`. Rollback redeploys a previous digest.

**Migration boundary:** rollback to images predating PostgreSQL authority is intentionally unsupported because those images cannot read the durable authority schema. Roll back only to a known-good post-migration image.

## AWS EC2 Spot boundary

Compute may be disposable only because authoritative beta state now lives outside the instance. On AWS use RDS/private networking, IAM instance roles, SSM/Secrets Manager and 80/443-only public ingress. Do not store authoritative EACODE state on the Spot filesystem.

Remaining external gates before a production-ready claim include real EC2/RDS deployment, DNS/TLS, RDS backup/restore, live identity provider integration, SLO/alerts/telemetry and a proven sandbox before any arbitrary untrusted-code execution.
