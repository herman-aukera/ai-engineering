# Session 13/14 + Session 15 production envelope

This directory adds the Session 15 production/runtime ring around the consolidated Session 13/14 estimator control plane. It preserves the typed LangGraph state, supervisor, specialists, deterministic policy/critic boundaries, replay/HITL semantics and persisted workflow state already implemented inside the application.

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

Production Compose intentionally does not start PostgreSQL or Redis on the replaceable application host. Authoritative workflow/checkpoint state must live in durable PostgreSQL outside the Spot instance lifecycle. Redis must be treated according to the application feature using it; do not promote disposable cache data into authoritative state.

## Deterministic CI versus AI evaluation

Blocking `.github/workflows/ci.yml` is provider-keyless in the production sense: provider environment values are deterministic fakes, and no real model endpoint is invoked. The Session 15 contract explicitly fails if blocking CI starts consuming repository secrets or running live-provider tests/benchmarks.

Credentialed provider quality/latency/cost evaluation has a separate cadence in `.github/workflows/provider-evaluation.yml` and is manually dispatched. Model availability, rate limits, stochasticity and quota therefore cannot make software CI randomly red.

## Public API/versioning

The consolidated Session 13/14 graph boundary uses the canonical major-version namespace under `/api/v1/...`, including `/api/v1/estimate/graph/unified/...`. Historical coursework routes remain available in the broad application where compatibility requires them; production hardening does not silently rewrite old clients.

Operational probes are deliberately not versioned API resources.

## Health semantics

- `/startup`: initialization completed; cheap/local and LLM-free.
- `/health`: liveness; cheap/local and LLM-free.
- `/ready`: production composition/readiness contract; never calls the LLM.
- `/api/v1/estimate/graph/unified/readiness`: graph-specific readiness evidence.

Caddy uses `/ready` for upstream health.

## Immutable build/release/run separation

`.github/workflows/release-image.yml` builds the estimator from an exact Git SHA and pushes it to GHCR. The workflow emits the immutable `name@sha256:digest` identity. Runtime environment configuration and provider credentials are injected only when the image runs.

Do not deploy a mutable `latest` tag.

## Runtime configuration

Required by the production Compose path:

- `ESTIMADOR_IMAGE`: exact OCI digest such as `ghcr.io/owner/estimador-cag@sha256:...`.
- `PUBLIC_HOST`: public DNS name for Caddy/TLS.
- `DATABASE_URL`: durable external PostgreSQL.
- `REDIS_URL`: runtime Redis endpoint.

Provider credentials are runtime secrets only and are optional until a provider-backed request is actually used.

## Deploy

```sh
ESTIMADOR_IMAGE='ghcr.io/owner/estimador-cag@sha256:...' \
PUBLIC_HOST='estimate.example.com' \
DATABASE_URL='postgresql://...' \
REDIS_URL='redis://...' \
sh deploy.sh
```

The script refuses mutable image references, validates Compose, pulls the exact artifact, replaces the application and waits for `/ready`. It never rebuilds source on the server.

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

The application compute should be treated as disposable:

- public security group: 80/443 only;
- use IAM instance roles rather than static AWS credentials;
- prefer SSM Session Manager or tightly restricted admin access;
- inject runtime secrets from SSM Parameter Store or Secrets Manager;
- use durable PostgreSQL such as RDS outside the Spot lifecycle;
- use a managed/external Redis endpoint if Redis is required across instance replacement;
- bootstrap the host from an exact released image digest;
- allow graceful container termination before Spot reclaim;
- never rely on application-host local disk for authoritative workflow state.

The CI PostgreSQL lifecycle evidence and container readiness checks are repository evidence, not proof of a real AWS deployment. This repository deliberately does **not** create paid AWS resources. Real EC2/RDS deployment, DNS/TLS observation, live-provider evaluation and production telemetry remain separate evidence levels before the system can be called live production-ready.
