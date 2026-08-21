# Estimator Release Contract

```text
Git SHA
-> deterministic CI + contract/smoke/integration evidence
-> one OCI build
-> immutable GHCR digest
-> deploy exact digest
-> wait /ready
-> retain previous digest
-> rollback by previous digest
```

Normal CI must not call a real LLM. Provider evaluation has a separate manually dispatched cadence.

Production deploy files live in `deploy/session15/`. `deploy.sh` rejects mutable tags and never rebuilds source on the server. `rollback.sh` redeploys a previous immutable artifact.

A green repository release is not equivalent to live production readiness; external staging, DNS/TLS, state recovery and telemetry are higher evidence levels.
