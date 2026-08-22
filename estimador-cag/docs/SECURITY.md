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
- runtime secrets are not baked into the image;
- signed actor/session identity is required by the production chat surface;
- PostgreSQL ownership binds conversations and persisted graph threads to an actor;
- read/replay/resume/delete operations enforce owner or explicit administrative authority.

## Remaining external/pre-production security evidence

The repository implements and tests the application-level actor/ownership boundary; that is no longer a critical repository blocker. It does **not** prove an external enterprise identity provider, internet-facing abuse resistance, managed cloud IAM, or production incident handling.

Before public multi-user production, external validation still includes:

- integrate and validate the intended external authentication/OIDC or gateway identity source while preserving the signed internal actor contract;
- configure managed secret storage/rotation and least-privilege cloud IAM;
- add or validate edge rate/abuse controls for the selected deployment platform;
- run internet-facing penetration/adversarial testing, including hostile retrieved content and prompt-injection cases;
- validate alerting, incident response, backup/restore and credential-rotation procedures in staging/AWS.

These are external evidence/deployment tasks and must not be presented as already proven by repository tests.
