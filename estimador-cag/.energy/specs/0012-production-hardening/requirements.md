# Spec 0012 — Production Hardening Slice: Requirements

## Status

Implementation candidate. Production readiness remains explicitly blocked.

## Objective

Replace the demo-only authority and process-local evidence path introduced by Spec 0011 with a durable, server-owned, replay-safe beta control plane and executable container-runtime proof.

## Functional requirements

1. `POST /eacode/demo` MUST accept only a provider-neutral `CodingProposal`.
2. The proposal-preparation endpoint MUST NOT accept or infer human authorization from client-controlled Boolean fields.
3. Preparation MUST evaluate concrete deterministic hard gates. An empty finding collection MUST NOT be treated as positive proof.
4. Automated repair MUST create and retain a distinct effective proposal revision.
5. Prepared proposals MUST remain inert until a signed backend session with `operator` or `admin` role is verified.
6. Authorization MUST be represented by a short-lived server-issued receipt bound to proposal ID, authenticated actor, exact effective command scope, and issuance/expiry timestamps.
7. Receipt consumption MUST be atomic and one-time. Replay, actor mismatch, scope mismatch, expiry, and concurrent consumption MUST fail closed.
8. Proposal results and authorization receipts MUST survive application restart.
9. Persisted records MUST include integrity hashes and fail closed when tampering is detected.
10. Execution in this slice MUST remain simulated and clearly labelled as simulated.
11. Reevaluation MUST operate on the effective repaired proposal, not the original defective proposal.
12. The deterministic beta benchmark MUST calculate decisions from proposal evidence and MUST NOT use `expected` labels to generate `actual` decisions.
13. Container CI MUST start PostgreSQL, Redis, and the API; prove API health; prove non-root execution; restart the API; and prove persisted demo state remains inspectable.
14. The runtime image MUST exclude the development/test extra and MUST not include repository tests in its filesystem.
15. The isolated runner boundary MUST remain non-root, read-only, capability-dropped, and Docker-socket-free.

## Security requirements

- Session signing keys MUST come from runtime configuration.
- Missing signing configuration MUST fail authorization endpoints with service-unavailable status.
- Invalid, expired, viewer, or reviewer sessions MUST not authorize execution.
- Authorization receipt IDs are capabilities and MUST never be logged as credentials.
- No real provider or process execution is introduced by this slice.

## Non-goals

- arbitrary untrusted-code isolation;
- real coding-agent integration;
- live provider evaluation;
- live Google or Apple login;
- production deployment;
- multi-tenant authorization;
- EACORE extraction.

## Claim boundary

Passing this specification proves a durable and replay-safe simulated beta path plus container startup evidence. It does not prove autonomous repair quality, real process safety, external authentication, live-provider success, or production readiness.
