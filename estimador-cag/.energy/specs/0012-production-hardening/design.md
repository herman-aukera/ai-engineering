# Spec 0012 — Production Hardening Slice: Design

## State transition

```text
signed viewer/reviewer/operator/admin session
  -> tenant-owned CodingProposal
  -> deterministic hard-gate findings
  -> independent deterministic semantic jury
  -> deterministic governor
  -> optional bounded repair
  -> persisted inert effective proposal
  -> signed operator/admin session
  -> exact-scope short-lived receipt
  -> atomic receipt consumption + single execution reservation
  -> simulated bounded execution
  -> effective-proposal reevaluation
  -> persisted completed result
```

## Identity and ownership

`SessionSigner` remains the server-owned authentication boundary. Every proposal record stores `owner_id` from the verified backend session. Non-admin reads and mutations include that owner predicate. Admin sessions deliberately use an unrestricted owner filter for support/audit operations.

The UI may carry a signed token, but it cannot create authority. Server endpoints derive the actor and roles exclusively from the verified token.

## API

### Prepare

`POST /eacode/demo`

- requires viewer, reviewer, operator, or admin role;
- request: strict `CodingProposal`;
- response: inert `BetaDemoResult`;
- persists result with owner ID and integrity hash;
- duplicate proposal IDs return conflict;
- extra client field `human_authorization` is rejected.

### Authorize

`POST /eacode/demo/{proposal_id}/authorize`

- requires operator or admin role;
- verifies tenant ownership unless admin;
- verifies the effective repaired proposal is eligible;
- issues a five-minute receipt bound to proposal, actor, and exact command-scope digest;
- returns only public receipt metadata.

### Execute

`POST /eacode/demo/{proposal_id}/execute`

- requires operator or admin role;
- atomically verifies owner, receipt, actor, scope, expiry, and unused state;
- atomically reserves the proposal's single execution transition;
- performs only simulated execution;
- reevaluates the effective proposal;
- updates the durable result only after reservation.

A reserved transition is intentionally fail-closed. Operational recovery is a separate later slice.

### Inspect

`GET /eacode/demo/{proposal_id}` requires a signed read-capable session, applies tenant ownership, reconstructs the typed result from SQLite, verifies its SHA-256 integrity digest, and fails closed on tampering.

## Persistence

`SQLiteBetaDemoStore` owns:

- `beta_demo_runs`: owner ID, canonical JSON result, digest, execution reservation, and timestamps;
- `beta_demo_authorizations`: actor, proposal, scope digest, nonce digest, expiry, consumption timestamp, and record digest.

SQLite uses WAL mode, foreign keys on each connection, and `BEGIN IMMEDIATE` for serialized writes. This is single-node beta durability, not horizontally scaled production storage.

## Deterministic gates

The beta hard-gate set verifies changed-file scope, safe relative paths, bounded patch size, secret hygiene, test integrity, and a bounded command allowlist. Protected deployment and workflow paths trigger human review. These checks are a beta policy surface, not a general secure-code proof.

## Product image

`app.eacode_main` is the dedicated EACODE composition root. It exposes only EACODE routes, health, and the UI redirect. The `runtime` Docker target installs a pinned minimal dependency set and copies only the composition root, EACODE router, and deterministic `energy_core` package. It runs as UID 10001 with durable state under `/data`.

The repository also retains:

- `full-runtime` for the existing estimator/coursework development stack;
- `test` for deterministic containerized tests;
- the separate UID 10002 read-only runner boundary.

## Runtime and supply-chain proof

The EACODE image workflow:

1. validates Compose;
2. builds and starts only the minimal `eacode-api` product service;
3. tags the exact local image by workflow SHA;
4. fails on fixed high/critical OS or library vulnerabilities;
5. exports an SPDX SBOM artifact;
6. proves UID 10001 and absence of `pytest`, Torch, and Jupyter;
7. proves health, signed tenant preparation, unsigned rejection, restart, and durable inspection;
8. proves the isolated runner boundary;
9. publishes only from canonical `EACODE` using an immutable SHA tag with BuildKit SBOM and provenance.

## Network policy

Both composition roots use an explicit `EACODE_ALLOWED_ORIGINS` allowlist. Wildcard or empty origin policy fails application startup.
