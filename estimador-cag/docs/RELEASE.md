# EACHAT Release Contract

```text
exact Git SHA
-> deterministic CI + browser/security/Postgres/container evidence
-> non-root OCI image
-> immutable GHCR digest
-> deploy exact digest
-> /ready gate
-> rollback previous digest
```

Blocking CI must not call a real model. Live-provider smoke is an explicit separate workflow.

Production deploy lives in `deploy/eachat/session15/`. It requires durable PostgreSQL and conversation encryption, refuses mutable image tags and does not rebuild source on the server.

Repository green is a release-candidate evidence level, not proof of live production readiness.
