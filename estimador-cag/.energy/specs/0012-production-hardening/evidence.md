# Spec 0012 — Production Hardening Slice: Evidence

## Evidence status

Validated implementation evidence captured on 2026-08-05.

This document records the implementation head that completed all code and runtime gates. Documentation-only evidence commits follow that implementation head and must not be interpreted as additional runtime functionality.

## Repository coordinates

- Repository: `herman-aukera/ai-engineering`
- Base beta PR: `#20`
- Base beta head: `83a77378d8c5852936a522d8df9d932c8d5715a9`
- Hardening branch: `gg-eacode/production-hardening-slice`
- Hardening draft PR: `#24`
- Validated implementation head: `81780cb1bb82e068d71effb1ab33d0163a1f189c`
- Validated stacked merge ref: `3a785039b91113213f49abbbcd2ebe9683011d69`

## Canonical code gate

GitHub Actions workflow: `CI - Estimador CAG`

- Run: `31037548850`
- Job: `92413414645`
- Checkout: stacked PR merge ref `3a785039b91113213f49abbbcd2ebe9683011d69`
- Ruff: passed
- Python compilation: passed
- Energy Core boundary: passed
- Full pytest: `758 passed in 24.63s`
- Energy Core full gate pytest: `758 passed in 19.14s`
- Energy Core smokes: passed
- Provider pipeline smoke: `22/22 passed`
- Root smoke: passed
- Repository cleanliness: passed
- Final job conclusion: success

## Product-container and supply-chain gate

GitHub Actions workflow: `EACODE container image`

- Run: `31037548636`
- Job: `92413414429`
- Validated source head: `81780cb1bb82e068d71effb1ab33d0163a1f189c`
- Compose configuration: passed
- Dedicated minimal `eacode-api` image: built and started healthy
- Runtime identity: UID `10001`
- Excluded runtime modules: `pytest`, Torch, and Jupyter absent
- Product endpoints: `/health`, `/eacode/status`, and `/eacode/ui` passed
- Unsigned proposal preparation: rejected with HTTP 401
- Signed tenant proposal preparation: passed
- API restart: passed
- Durable signed-session inspection after restart: passed
- Fixed high/critical vulnerability gate: passed
- SPDX SBOM generation: passed
- SPDX SBOM artifact upload: passed
- Isolated runner identity: UID `10002`
- Runner read-only/capability-dropped boundary: passed
- Cleanup: passed
- Image publication: skipped as required for a non-canonical branch
- Final job conclusion: success

## Deterministic security regressions covered

- client-controlled `human_authorization` is rejected;
- unsigned preparation and inspection fail closed;
- viewer/reviewer sessions cannot authorize or execute;
- non-admin sessions cannot inspect or authorize another tenant's proposal;
- admin cross-tenant inspection is explicit;
- automated repair creates a distinct effective proposal revision;
- hard-rejected and unresolved proposals cannot be authorized;
- authorization receipts bind proposal, actor, exact command scope, and expiry;
- replay, actor mismatch, scope mismatch, expiry, and concurrent execution reservation fail closed;
- persisted result tampering is detected;
- expected benchmark labels cannot control actual decisions;
- wildcard CORS is absent;
- the dedicated product composition root excludes estimator and session routes.

## Evidence classification

- Deterministic code and test evidence: L2
- Real container startup, restart, HTTP, persistence, image scan, and SBOM evidence: L3
- Live provider evidence: not performed
- Live external identity evidence: not performed
- Real process execution evidence from the beta API: not performed
- External staging or production telemetry: not performed

## Claim boundary

The validated claim is:

> EACODE Spec 0012 is a tenant-scoped, signed-session, replay-safe simulated beta with a minimal product image, restart persistence, fixed high/critical vulnerability blocking, SPDX SBOM evidence, and isolated runner proof.

The evidence does not prove:

- production readiness;
- real coding-agent integration;
- real process execution from the beta API;
- arbitrary untrusted-code isolation;
- horizontal or multi-region durability;
- live Google or Apple OIDC;
- live provider success;
- external deployment, rollback, SLOs, or production telemetry.

## Merge boundary

PR `#24` remains draft and stacked on PR `#20`. Neither PR is approved for merge by this evidence document. Merge requires explicit user authorization after confirming that the current documentation-only head remains green.
