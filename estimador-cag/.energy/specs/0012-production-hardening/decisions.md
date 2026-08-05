# Spec 0012 — Decisions

## D-001 — Stack this slice on Spec 0011

The branch starts at PR #20 head `83a77378d8c5852936a522d8df9d932c8d5715a9`. The hardening PR targets the beta branch so the security, persistence, and runtime delta remains independently reviewable.

## D-002 — Reuse signed local sessions

The existing `SessionSigner` and role contracts remain the authentication boundary. This avoids creating a second identity abstraction before live OIDC is proven.

## D-003 — Add tenant ownership before external identity

Every proposal is bound to the verified backend user ID. Non-admin access includes that owner predicate; admin access is an explicit support/audit exception. This prevents anonymous or cross-user patch disclosure without claiming live OIDC.

## D-004 — Use SQLite for this beta slice

SQLite supplies deterministic single-node durability, WAL mode, atomic receipt consumption, execution reservation, and restart evidence without claiming horizontally scaled production readiness. PostgreSQL migration remains a later deployment slice.

## D-005 — Reserve before simulated execution

Receipt consumption and proposal execution reservation occur in one immediate transaction. Once reserved, the transition cannot be silently replayed. A failed downstream transition requires explicit recovery, preserving fail-closed semantics.

## D-006 — Keep execution simulated

Hardening authority and evidence does not justify silently enabling real process execution. Real execution remains behind the separately specified secure adapter and manual host proof.

## D-007 — Use a dedicated product composition root

The production-shaped EACODE image uses `app.eacode_main`, not the estimator/coursework composition root. PostgreSQL, Redis, estimation routes, notebook tooling, ML runtimes, and test tooling are excluded because this beta product path does not use them.

## D-008 — Pin a minimal product dependency set

The EACODE runtime uses a small exact-version requirements file. The existing project lock remains authoritative for development and tests. A future packaging split may replace this interim runtime manifest.

## D-009 — Treat image security evidence as a release gate

The workflow blocks fixed high/critical vulnerabilities, exports an SPDX SBOM, and publishes only immutable SHA-tagged images from canonical `EACODE` with BuildKit SBOM and provenance.

## D-010 — Keep the PR stacked and draft

The hardening branch is based on PR #20 and remains a stacked draft PR. Neither PR is merged without explicit user approval and green current-head evidence.
