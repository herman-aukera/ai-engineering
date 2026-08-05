# Spec 0012 — Production Hardening Slice: Requirements

## Status

Implementation candidate. Production readiness remains explicitly blocked.

## Objective

Replace the demo-only authority and process-local evidence path introduced by Spec 0011 with a durable, tenant-scoped, server-owned, replay-safe simulated beta control plane and executable product-container proof.

## Functional requirements

1. `POST /eacode/demo` MUST accept only a provider-neutral `CodingProposal`.
2. Proposal preparation and inspection MUST require a valid signed backend session.
3. Non-admin sessions MUST access only proposals owned by the same backend user ID. Admin sessions MAY cross the owner boundary.
4. The proposal-preparation endpoint MUST NOT accept or infer human authorization from client-controlled Boolean fields.
5. Preparation MUST evaluate concrete deterministic hard gates. An empty finding collection MUST NOT be treated as positive proof.
6. Automated repair MUST create and retain a distinct effective proposal revision.
7. Prepared proposals MUST remain inert until a signed backend session with `operator` or `admin` role is verified.
8. Authorization MUST be represented by a short-lived server-issued receipt bound to proposal ID, authenticated actor, exact effective command scope, and issuance/expiry timestamps.
9. Receipt consumption MUST be atomic and one-time. Replay, actor mismatch, owner mismatch, scope mismatch, expiry, concurrent consumption, and a second execution reservation MUST fail closed.
10. Proposal results and authorization receipts MUST survive application restart.
11. Persisted records MUST include integrity hashes and fail closed when tampering is detected.
12. Execution in this slice MUST remain simulated and clearly labelled as simulated.
13. Reevaluation MUST operate on the effective repaired proposal, not the original defective proposal.
14. The deterministic beta benchmark MUST calculate decisions from proposal evidence and MUST NOT use `expected` labels to generate `actual` decisions.
15. Container CI MUST start the dedicated minimal EACODE API, prove API health and non-root execution, exercise signed tenant access, restart the API, and prove persisted state remains inspectable.
16. The EACODE product image MUST use its dedicated composition root and pinned minimal runtime dependency set. It MUST exclude tests, `pytest`, Torch, Jupyter, and estimator-only routes.
17. Image CI MUST fail on fixed high or critical OS/library vulnerabilities and MUST export an SPDX SBOM artifact.
18. Image publication MUST occur only from a push to canonical `EACODE`, use an immutable commit-SHA tag, and include BuildKit SBOM and provenance attestations.
19. The isolated runner boundary MUST remain non-root, read-only, capability-dropped, and Docker-socket-free.
20. CORS MUST use an explicit non-wildcard origin allowlist.

## Security requirements

- Session signing keys MUST come from runtime configuration.
- Missing signing configuration MUST fail signed-session endpoints with service-unavailable status.
- Invalid, expired, or insufficient-role sessions MUST fail closed.
- Viewer and reviewer sessions MAY prepare and inspect their own inert proposals but MUST NOT authorize or execute them.
- Authorization receipt IDs are capabilities and MUST not be emitted in general application logs.
- The execution reservation is fail-closed: once reserved, a failed downstream transition requires explicit recovery rather than silent replay.
- No real provider or process execution is introduced by this slice.

## Non-goals

- arbitrary untrusted-code isolation;
- real coding-agent integration;
- live provider evaluation;
- live Google or Apple login;
- external deployment;
- horizontally scaled or multi-region authorization storage;
- EACORE extraction.

## Claim boundary

Passing this specification proves a tenant-scoped, signed-session, replay-safe simulated beta path, a minimal product image, restart persistence, vulnerability scanning, and SBOM/provenance preparation. It does not prove autonomous repair quality, real process safety, external identity, live-provider success, horizontally scaled persistence, external deployment, or production readiness.
