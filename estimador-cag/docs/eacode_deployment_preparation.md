# EACODE deployment preparation

These assets prepare deployment; they are not external-deployment or production evidence.

## Local profiles

```text
docker compose --profile dev up --build
docker compose --profile test run --rm test
docker compose --profile demo up --build
```

Open `http://localhost:8000/eacode/ui`. Stop with `docker compose --profile demo down`.
To reset only named demo data after confirming the project name, run
`docker compose --profile demo down --volumes`. This is destructive to the Compose project's
Postgres and Redis volumes.

The API container is non-root and has no Docker socket. The runner is a separate non-root,
read-only container with all Linux capabilities dropped. This is a process boundary, not a
hostile-code sandbox.

## GHCR and Dokploy-style host

The `EACODE container image` workflow builds pull requests without publishing and publishes
commit-addressed images from allowed branches. A host operator should pin an exact image digest,
configure Postgres and Redis as private services, expose only the API, supply secrets through the
host secret store, and verify `/health` before switching traffic.

Rollback means redeploying the previously verified image digest and retaining compatible database
volumes. Database migrations must be forward/backward reviewed before any external deployment.
No external host, DNS, credentials, or paid infrastructure may be changed without explicit approval.

Google and Apple callbacks must use the final HTTPS origin. Deterministic configuration tests do not
prove live SSO; credential-backed callback proof is a separate manual gate.
