# EACHAT production envelope

This directory adds the production/runtime ring around the Energy-Aware Chat graph and policy architecture.

The production composition root is `app.energy_chat.production_app:app`. It publishes the canonical `/energy-chat/v2/*` product contract only. Historical evaluation, benchmark, draft-generation and coursework MVP endpoints remain in the broad compatibility application but are deliberately **not mounted in production**.

## Topology

```text
Internet
  -> HTTPS 443 / HTTP 80
  -> Caddy (only host-published service)
  -> EACHAT production container :8000 on a private Docker network
  -> durable external PostgreSQL
  -> outbound HTTPS to explicitly selected LLM providers
```

Authoritative conversations, encrypted turn payloads, LangGraph checkpoints, HITL/replay state and idempotency evidence must survive application/EC2 replacement. Use durable PostgreSQL such as RDS rather than a Spot-local volume.

## Canonical public surface

Business routes are explicitly major-versioned beneath `/energy-chat/v2/`, including chat, bounded live chat, replay/thread state, conversation history/turns and durable human-gate continuation. The bundled demo is also `/energy-chat/v2/demo`.

Legacy `/energy-chat/evaluate`, benchmark, source-classification and old MVP routes are not part of the production service.

## Runtime contract

Required:

- `PUBLIC_HOST`.
- `EACHAT_IMAGE`: immutable OCI digest.
- `EACHAT_POSTGRES_URL`: durable PostgreSQL.
- `EACHAT_MEMORY_ENCRYPTION_KEY`: conversation encryption key.

Production fixes `LANGGRAPH_STRICT_MSGPACK=true` and deliberately omits `EACHAT_ALLOW_IN_MEMORY`. Explicit CORS origins are optional for trusted cross-origin clients; the bundled UI is same-origin.

Provider credentials are runtime secrets only. Live provider evidence runs in `.github/workflows/eachat-live-provider-smoke.yml`, never in blocking deterministic CI.

## Health semantics

- `/startup`: initialization completed.
- `/health`: cheap liveness; no database/cache/LLM call.
- `/ready`: runtime and conversation-store composition completed; production startup fails closed when durable state cannot initialize.
- `/version`: safe service version and Git SHA.

## Build, deploy and rollback

`.github/workflows/eachat-release-image.yml` builds an isolated non-root image and emits an immutable `name@sha256:digest` identity. `deploy.sh` rejects mutable tags, pulls the exact image and waits for `/ready`. `rollback.sh` redeploys a previous immutable digest rather than rebuilding source.

## AWS EC2 Spot boundary

The application container is disposable. Existing CI destroys and recreates the application against the same PostgreSQL service and verifies conversation recovery. Keep PostgreSQL outside the Spot lifecycle, inject secrets through SSM/Secrets Manager, prefer IAM instance roles and allow the configured graceful termination window.

A real EC2/RDS deployment, DNS/TLS observation, live-provider run, backup/restore exercise and production telemetry remain external gates before a production-ready claim.
