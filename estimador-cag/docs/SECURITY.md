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
- persistent human review uses revision-aware application contracts;
- signed actor/session identity is required on the production estimation surface;
- PostgreSQL ownership binds estimation identifiers and persisted workflow threads to an actor;
- inspect/resume operations enforce that ownership boundary before exposing or mutating persisted state.

## Remaining external/pre-production security evidence

The repository now implements and tests the application-level actor/ownership boundary; that is no longer an open repository blocker. It does **not** prove an external enterprise identity provider, managed cloud IAM, internet-facing abuse resistance, or operational security under real traffic.

Before public multi-user production, external validation still includes:

- integrate and validate the intended external authentication/OIDC or gateway identity source while preserving the signed internal actor contract;
- configure managed secret storage/rotation and least-privilege cloud IAM;
- add or validate edge rate/abuse controls for the selected deployment platform;
- run internet-facing penetration/adversarial testing;
- validate alerting, incident response, backup/restore and credential-rotation procedures in staging/AWS.

These are external evidence/deployment tasks and must not be presented as already proven by repository tests.
