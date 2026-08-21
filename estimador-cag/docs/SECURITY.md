# EACHAT Security

## Enforced controls

- non-root isolated production image;
- explicit CORS and security headers;
- strict checkpoint deserialization;
- encrypted durable conversation storage;
- PostgreSQL required for production persistence;
- revision/idempotency protection for conversation turns and HITL;
- V2-only production API surface;
- model/provider calls absent from blocking deterministic CI;
- single public Caddy ingress; database/application internals remain private;
- runtime secrets are not baked into the image.

## Critical remaining blocker

Current V2 conversation/thread/HITL identifiers are not yet bound to a fully authenticated tenant/actor ownership model. Before public multi-user staging, introduce an IdentityProvider boundary and persist owner/tenant identity with conversations and graph threads. Every read/replay/resume/delete must prove ownership or an explicit admin/service authorization.

Also pending: production rate/abuse controls, managed secret rotation, external auth/OIDC adapter, penetration testing and real operational incident evidence.
