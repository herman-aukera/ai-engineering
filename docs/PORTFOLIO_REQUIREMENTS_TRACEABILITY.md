# Energy-Aware Portfolio Requirements Traceability

Status: canonical zero-gap certification matrix

Machine source: `docs/portfolio_requirements_traceability.json` (canonical v2 composition over the preserved v1 base)

Validator: `estimador-cag/scripts/verify_portfolio_requirements.py`

## Purpose

This document is the human index for the machine-validated Energy-Aware portfolio requirements traceability matrix. The JSON file is authoritative for row-level certification and is executed by the hosted portfolio final gate against the exact canonical heads of `main`, `EACHAT`, and `EACODE`.

The matrix preserves the three-product topology:

- `main` — Energy-Aware Estimator;
- `EACHAT` — Energy-Aware Chat;
- `EACODE` — Energy-Aware Code.

It does not authorize merging the peer branches or physically extracting repositories.

## Accounting

| Classification | Rows |
|---|---:|
| Total | 185 |
| PASS | 177 |
| N/A | 0 |
| BLOCKED_EXTERNAL | 8 |
| FAIL | 0 |

The validator cross-checks this human accounting table against the composed machine RTM. A final hosted certificate counts only when both representations agree and the validator reports the same zero-failure accounting against the exact branch heads captured by that run.

## Requirement families

| Family | Scope |
|---|---|
| `PORT-*` | portfolio topology, lifecycle, deterministic CI, release, documentation, split-readiness |
| `PROTO-*` | neutral Energy-Aware protocol and compatibility semantics |
| `AUTH-*` | deterministic authority, human authority, provider evidence boundaries, budgets |
| `MAIN-*` | Estimator definition of done |
| `CHAT-*` | EACHAT definition of done |
| `CODE-*` | EACODE definition of done |
| `AI-*` | provider abstraction, structured output, prompt/evidence safety, evaluation |
| `RES-*` | resilience, persistence, restart, Spot preparation, repository split contracts |
| `SC-*` | immutable Actions, immutable executable images/tools, anti-regression scanners, Dependabot |
| `EXT-*` | approved genuinely external completion work only |

## Evidence model

Every repository-controlled `PASS` row resolves an evidence bundle containing:

1. implementation paths;
2. executable tests or validation scripts;
3. hosted CI evidence locations.

The final gate supplies all three checked-out repository roots to the validator. Branch-qualified evidence paths are therefore checked for existence against the exact `main`, `EACHAT`, and `EACODE` heads captured by the same run.

A repository-controlled row may not resolve to `N/A` or `BLOCKED_EXTERNAL`.

## Approved external categories

Only these categories may use `BLOCKED_EXTERNAL`:

- `LOCAL_MANUAL_TEST`;
- `TEMPORARY_PUBLIC_STAGING`;
- `AWS_SPOT_RDS`;
- `LIVE_PROVIDER`;
- `REAL_OIDC`;
- `GITHUB_ADMINISTRATION`;
- `REPOSITORY_EXTRACTION`;
- `REAL_TRAFFIC_SLO`.

Anything repository-controlled must be repaired until it is `PASS`.

## Zero-gap validator contract

`verify_portfolio_requirements.py` fails when any of the following is true:

- an unknown status is present;
- a requirement ID is duplicated;
- a required row field is missing;
- a repository-controlled row is not `PASS`;
- a `PASS` row lacks implementation, test, or CI evidence;
- a referenced branch-qualified evidence path is missing when exact branch roots are supplied;
- a `PASS` row carries an external blocker;
- `BLOCKED_EXTERNAL` uses a category outside the approved list;
- this human accounting table diverges from the composed canonical machine RTM.

The strengthened portfolio final gate also executes the Action-pin, image-pin, tool-pin, Dependabot, protocol, documentation-truth, dependency, smoke, production-contract, Docker, non-root, secret, clean-tree, and split-dry-run contracts.

## Certification boundary

This matrix certifies repository-controlled readiness only. It does not claim that manual local validation, public staging, AWS Spot/RDS interruption behavior, live-provider operation, real OIDC, GitHub administrative rules, physical repository extraction, or real-traffic SLO evidence has already occurred.
