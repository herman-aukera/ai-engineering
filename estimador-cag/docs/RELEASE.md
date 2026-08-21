# EACODE Release Contract

```text
exact Git SHA
-> deterministic CI + contract/smoke/Postgres restart evidence
-> non-root OCI image
-> immutable GHCR digest
-> explicit PostgreSQL migration
-> deploy exact digest
-> /ready gate
-> rollback previous compatible digest
```

Blocking CI never calls a real provider; credentialed provider smoke has a separate explicit cadence.

Rollback to pre-PostgreSQL-authority images is intentionally unsupported because those images cannot honor the current durable authority contract. Roll back only to a known-good post-migration artifact.

The current Docker build is reproducible from the monorepo frozen lock but is not yet dependency-minimal; product-specific dependency-lock extraction belongs to the repository-split slice.
