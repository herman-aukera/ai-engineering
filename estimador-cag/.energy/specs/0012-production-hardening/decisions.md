# Spec 0012 — Decisions

## D-001 — Stack this slice on Spec 0011

The branch starts at PR #20 head `83a77378d8c5852936a522d8df9d932c8d5715a9`. The hardening PR targets the beta branch so the security and persistence delta remains independently reviewable.

## D-002 — Reuse signed local sessions

The existing `SessionSigner` and role contracts remain the authentication boundary. This avoids creating a second identity abstraction before live OIDC is proven.

## D-003 — Use SQLite for this beta slice

SQLite supplies deterministic local durability, WAL mode, atomic single-node receipt consumption, and restart evidence without claiming multi-node production readiness. PostgreSQL migration remains a later deployment slice.

## D-004 — Keep execution simulated

Hardening authority and evidence does not justify silently enabling real process execution. Real execution remains behind the separately specified secure adapter and manual host proof.

## D-005 — Separate runtime and test images

The runtime image omits the development extra; the `test` target preserves deterministic containerized tests. This keeps release claims precise without breaking the existing test profile.

## D-006 — Prefer stacked PR review

The hardening branch is based on PR #20 and should be reviewed as a stacked draft PR before either branch is merged.
