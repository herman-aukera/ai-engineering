# Estimator — Session 13/14 + Session 15 production envelope

This directory is the production/runtime ring around the consolidated Session 13/14 Energy-Aware estimator control plane.

Production now starts the isolated composition root `app.estimator.production_app:app`. The broad historical `app.main` application remains available for coursework/local compatibility, but it is **not** the deployable product surface.

## Production surface

The isolated app publishes only:

- `/startup`, `/health`, `/ready`, `/version` operational probes;
- the canonical `/api/v1/estimate/graph/unified/...` estimator API.

Historical demos, embeddings/search exercises, older graph generations and `/api/v2` coursework compatibility routes are deliberately absent from the production process.

## Topology

```text
Internet
  -> HTTPS 443 / HTTP 80
  -> Caddy (only host-published production service)
  -> estimator/FastAPI :8000 on a private Docker network
  -> durable external PostgreSQL
  -> runtime Redis endpoint
  -> outbound HTTPS to explicitly selected LLM providers
```

The repository-root `docker-compose.yml` remains a developer composition and may publish developer ports. It is **not** the production network contract.

Production Compose intentionally does not start PostgreSQL or Redis on the replaceable application host. Authoritative workflow/checkpoint state must live in durable PostgreSQL outside the Spot instance lifecycle.

## Deterministic CI versus AI evaluation

Blocking `.github/workflows/ci.yml` uses deterministic fake provider configuration and never performs a real model call. The production contract fails if normal CI begins consuming repository secrets or running live-provider evaluation.

Credentialed provider quality/latency/cost evaluation lives in `.github/workflows/provider-evaluation.yml` and is manually dispatched.

## Health semantics

- `/startup`: application lifespan initialization completed.
- `/health`: cheap local liveness; no database or LLM call.
- `/ready`: requires startup completion, the durable unified graph runtime, and at least one non-placeholder provider credential. It performs no model call.
- `/version`: safe service version plus injected Git SHA.
- `/api/v1/estimate/graph/unified/readiness`: graph-specific sanitized runtime evidence.

Caddy uses `/ready` for upstream health.

## Immutable build/release/run separation

`.github/workflows/release-image.yml` builds the estimator from an exact Git SHA and pushes it to GHCR. Runtime configuration and credentials are injected only when the image runs. Deploy an immutable `name@sha256:digest`, never `latest`.

## Runtime configuration

Required by the production Compose path:

- `ESTIMADOR_IMAGE`: exact OCI digest.
- `PUBLIC_HOST`: public DNS name for Caddy/TLS.
- `DATABASE_URL`: durable external PostgreSQL.
- `REDIS_URL`: runtime Redis endpoint.
- at least one real provider key at runtime for the production service to become ready.

## Deploy

```sh
ESTIMADOR_IMAGE='ghcr.io/owner/estimador-cag@sha256:...' \
PUBLIC_HOST='estimate.example.com' \
DATABASE_URL='postgresql://...' \
REDIS_URL='redis://...' \
sh deploy.sh
```

The script rejects mutable image references, validates Compose, pulls the exact artifact, replaces the application and waits for `/ready`. It never rebuilds source on the server.

## Rollback

```sh
ROLLBACK_IMAGE='ghcr.io/owner/estimador-cag@sha256:previous...' \
PUBLIC_HOST='estimate.example.com' \
DATABASE_URL='postgresql://...' \
REDIS_URL='redis://...' \
sh rollback.sh
```

Rollback means redeploying a previously known-good immutable artifact.

## AWS EC2 Spot boundary

Treat application compute as disposable: expose 80/443 only, use IAM roles and SSM/Secrets Manager, place PostgreSQL outside the Spot lifecycle, bootstrap from an exact released digest, and never use application-host disk for authoritative workflow state.

Repository CI/container evidence is not proof of a real AWS deployment. Real EC2/RDS deployment, DNS/TLS observation, backup/restore, live-provider evaluation and production telemetry remain separate evidence levels before a production-ready claim.
