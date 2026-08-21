# EACODE Security

## Enforced controls

- signed backend sessions with role checks;
- tenant-scoped proposal ownership plus explicit admin override;
- no client-owned authorization flag;
- exact-scope, actor/proposal/expiry-bound one-use receipts;
- atomic receipt consumption and execution reservation;
- integrity hashes on durable records;
- deterministic path/patch/secret/test/command/protected-surface hard gates;
- production PostgreSQL required for authoritative state;
- non-root product container and separate runner-isolation research;
- single public Caddy ingress;
- explicit CORS/security headers;
- normal CI remains provider-keyless and deterministic.

## Claim boundary

The current beta execution is simulated. Do not enable arbitrary untrusted-code execution until the runner proves process/filesystem/network/resource isolation, no Docker socket/privilege escalation, bounded timeouts and deterministic cleanup evidence.

External OIDC, managed secret rotation, staging penetration/abuse testing and operational incident evidence remain production blockers.
