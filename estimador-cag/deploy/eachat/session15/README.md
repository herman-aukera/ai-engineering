# EACHAT Session 15 production envelope

This directory adds the production/runtime ring around the existing EACHAT graph and policy architecture. It does not change the chat decision semantics.

## Topology

```text
Internet
  -> HTTPS 443 / HTTP 80
  -> Caddy (only host-published service)
  -> EACHAT production container :8000 on a private Docker network
  -> durable external PostgreSQL
  -> outbound HTTPS to explicitly selected LLM providers
```

PostgreSQL is intentionally not defined as a local production Compose service. Authoritative conversations, encrypted turn payloads, LangGraph checkpoints, HITL/replay state and idempotency evidence must survive replacement of the application/EC2 compute. On AWS, use a durable PostgreSQL endpoint such as RDS rather than a volume attached only to a Spot instance.

## Runtime contract

Required:

- `PUBLIC_HOST`: DNS name terminated by Caddy.
- `EACHAT_IMAGE`: exact OCI image digest, for example `ghcr.io/owner/eachat@sha256:...`.
- `EACHAT_POSTGRES_URL`: durable PostgreSQL connection string.
- `EACHAT_MEMORY_ENCRYPTION_KEY`: application-level conversation encryption key.

Production defaults:

- `LANGGRAPH_STRICT_MSGPACK=true` is fixed in Compose.
- `EACHAT_V2_ENABLED=true` unless explicitly overridden.
- `EACHAT_ALLOW_IN_MEMORY` is deliberately absent from production Compose.
- `EACHAT_CORS_ORIGINS` defaults to empty because the bundled browser client is same-origin. Add only explicit trusted cross-origin callers.

Provider credentials are optional runtime secrets and are never required by normal deterministic CI. Live provider evidence runs in `.github/workflows/eachat-live-provider-smoke.yml`, not the blocking CI workflow.

## Health semantics

- `/startup`: initialization completed.
- `/health`: cheap liveness; it performs no database, cache or LLM call.
- `/ready`: application runtime and conversation-store composition completed; production startup itself fails closed when durable PostgreSQL/checkpoint initialization fails.
- `/version`: safe service version plus injected Git SHA.

No health probe calls an LLM.

## Build once, run many

`.github/workflows/eachat-release-image.yml` builds the isolated non-root image from the exact Git SHA and pushes it to GHCR. The workflow emits the immutable `name@sha256:digest` identity. Environment configuration and secrets are injected only when the image runs.

Do not deploy a mutable `latest` tag.

## Deploy

From an EC2 host with Docker Compose installed and runtime secrets already injected by the host/secret manager:

```sh
EACHAT_IMAGE='ghcr.io/owner/eachat@sha256:...' \
PUBLIC_HOST='chat.example.com' \
EACHAT_POSTGRES_URL='postgresql://...' \
EACHAT_MEMORY_ENCRYPTION_KEY='...' \
sh deploy.sh
```

`deploy.sh` refuses mutable image tags, pulls the exact artifact, replaces containers and waits for `/ready`. It never rebuilds source on the server.

## Rollback

```sh
ROLLBACK_IMAGE='ghcr.io/owner/eachat@sha256:previous...' \
PUBLIC_HOST='chat.example.com' \
EACHAT_POSTGRES_URL='postgresql://...' \
EACHAT_MEMORY_ENCRYPTION_KEY='...' \
sh rollback.sh
```

Rollback means redeploying a previously known-good immutable artifact, not rebuilding old source.

## AWS EC2 Spot boundary

The application container is designed to be disposable. Existing CI already destroys and recreates the EACHAT application container against the same PostgreSQL service and verifies conversation recovery. For a real Spot deployment, keep authoritative PostgreSQL outside the Spot lifecycle and bootstrap the instance so it can obtain the exact released image digest and runtime secrets without manual edits.

Recommended AWS boundary:

- Security group: public 80/443 only; restrict SSH/admin access separately or use SSM Session Manager.
- IAM instance role rather than static AWS credentials.
- SSM Parameter Store or Secrets Manager for runtime secrets.
- RDS/PostgreSQL in private networking.
- Graceful termination window long enough for the 60-second container stop grace period.
- Replace instance/app compute freely; never rely on its local disk for authoritative chat state.

This repository does **not** provision paid AWS resources. A real EC2/RDS deployment, DNS/TLS observation, live-provider run and production telemetry remain external evidence gates before claiming live production readiness.
