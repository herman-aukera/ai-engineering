# EACODE Session 15 production envelope

This directory adds a production/runtime ring around the existing deterministic EACODE control plane. It does **not** enable unrestricted code execution or change the deterministic Boss/critic authority model.

## Canonical production surface

The isolated production application is `app.eacode.production_app:app` and publishes only the EACODE service plus operational probes.

Canonical API:

- `GET /api/v1/eacode/status`
- `GET /api/v1/eacode/capabilities`
- `POST /api/v1/eacode/select`
- `GET /api/v1/eacode/ui`

The broad coursework application still exposes the historical `/eacode/*` routes for compatibility. New production deployment uses only the versioned isolated application.

The selector is deterministic: it resolves a governed **plan** and never claims that a provider/model was actually served. Credentialed provider proof remains isolated in the manually dispatched live-smoke workflow.

## Topology

```text
Internet
  -> HTTPS 443 / HTTP 80
  -> Caddy (only host-published service)
  -> EACODE production container :8000 on a private Docker network
```

This isolated HTTP control surface has no authoritative runtime database state. The policy/capability data is shipped as version-controlled application data; a replacement container reconstructs the same deterministic service from the immutable image. This makes the service itself suitable for replaceable/Spot compute once the artifact and host bootstrap are supplied.

## Health semantics

- `/startup`: process/application initialization completed.
- `/health`: cheap local liveness; no provider call.
- `/ready`: deterministic control plane is available; no external dependency or provider call.
- `/version`: safe service version and injected Git SHA.

No health endpoint invokes an LLM.

## Immutable artifact

`.github/workflows/eacode-release-image.yml` is a manually dispatched release workflow. It:

1. checks out the exact Git SHA;
2. validates the frozen `uv.lock`;
3. exports hash-pinned production requirements;
4. builds the non-root isolated EACODE image;
5. pushes a SHA-addressed image to GHCR;
6. emits the immutable `name@sha256:digest` deploy identity.

Environment changes do not require a rebuild.

## Deploy

Provide an exact released digest and public DNS name:

```sh
EACODE_IMAGE='ghcr.io/owner/eacode@sha256:...' \
PUBLIC_HOST='code.example.com' \
sh deploy.sh
```

`deploy.sh` rejects mutable tags, pulls the exact artifact, replaces the service, and waits for `/ready`. It never rebuilds source on the host.

## Rollback

```sh
ROLLBACK_IMAGE='ghcr.io/owner/eacode@sha256:previous...' \
PUBLIC_HOST='code.example.com' \
sh rollback.sh
```

Rollback is therefore artifact replacement, not source reconstruction.

## CI versus model evaluation

Blocking `.github/workflows/ci.yml` uses only deterministic application behavior and fake provider credentials. It includes the Session 15 production contract and an isolated container canary.

Real provider evidence remains in `.github/workflows/live-smoke.yml`, which is manually dispatched and uses a separate cadence. Provider availability, quota, latency, stochasticity, or billing must never determine whether normal software CI is green.

## AWS EC2 Spot boundary

For direct EC2 deployment:

- expose only 80/443 through the public security group;
- prefer SSM Session Manager or tightly restricted administration rather than broad SSH;
- use an IAM instance role instead of static AWS credentials;
- fetch the exact released image digest during bootstrap;
- use SSM Parameter Store / Secrets Manager for any future runtime secrets;
- allow the container stop grace period before Spot termination;
- treat the instance filesystem as disposable.

Because this isolated deterministic selector does not own authoritative mutable state, replacement of the application instance does not require state restoration. Any future EACODE execution ledger or remote execution state must be re-audited before being placed on Spot compute.

This repository intentionally does **not** provision paid AWS resources. A real EC2 deployment, DNS/TLS observation, release-image execution, live provider evidence and production telemetry remain separate evidence gates before claiming live production readiness.
