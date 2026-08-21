# Estimator Security

## Enforced repository/runtime controls

- non-root production container;
- explicit CORS allowlist, no wildcard production default;
- security headers;
- provider credentials injected only at runtime;
- no live-provider call in blocking CI;
- secret-pattern gate in CI;
- one public Caddy ingress; PostgreSQL/Redis/application ports remain private in production topology;
- health probes never call an LLM;
- deterministic hard constraints and bounded provider routing;
- persistent human review uses revision-aware application contracts.

## Remaining production security blockers

The current estimator does not yet prove a complete tenant/actor ownership boundary for estimation IDs and human-resume operations. Before public multi-user staging, add authenticated actor/tenant context and bind every persisted estimation/thread to an owner so one tenant cannot inspect or resume another tenant's workflow.

Real secret rotation, managed IAM/SSM policy, external penetration testing, abuse/rate controls and production incident evidence remain external/next-stage work.
