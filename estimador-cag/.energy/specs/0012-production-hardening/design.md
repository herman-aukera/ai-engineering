# Spec 0012 — Production Hardening Slice: Design

## State transition

```text
CodingProposal
  -> deterministic hard-gate findings
  -> independent deterministic semantic jury
  -> deterministic governor
  -> optional bounded repair
  -> persisted inert BetaDemoResult
  -> signed operator/admin session
  -> one-time exact-scope receipt
  -> atomic receipt consumption
  -> simulated bounded execution
  -> effective-proposal reevaluation
  -> persisted completed result
```

## API

### Prepare

`POST /eacode/demo`

- request: `CodingProposal`;
- response: inert `BetaDemoResult`;
- persists result in SQLite;
- duplicate proposal IDs return conflict;
- extra field `human_authorization` is rejected by the typed model.

### Authorize

`POST /eacode/demo/{proposal_id}/authorize`

- requires `Authorization: Bearer <signed backend session>`;
- accepts only `operator` or `admin`;
- verifies the effective proposal is eligible;
- issues a five-minute one-time receipt;
- returns only public receipt metadata.

### Execute

`POST /eacode/demo/{proposal_id}/execute`

- requires the same authenticated actor;
- consumes an exact proposal/actor/scope receipt atomically;
- performs only simulated execution;
- reevaluates the effective proposal;
- updates the durable result.

### Inspect

`GET /eacode/demo/{proposal_id}` reconstructs the typed result from SQLite, verifies its SHA-256 integrity digest, and fails closed on tampering.

## Persistence

`SQLiteBetaDemoStore` owns:

- `beta_demo_runs`: canonical JSON result, digest, created and updated timestamps;
- `beta_demo_authorizations`: actor, proposal, scope digest, nonce digest, expiry, consumption timestamp, and record digest.

SQLite uses WAL mode and `BEGIN IMMEDIATE` for serialized writes.

## Deterministic gates

The beta hard-gate set verifies changed-file scope, safe relative paths, bounded patch size, secret hygiene, test integrity, and a bounded command allowlist. Protected deployment and workflow paths trigger human review. These checks are a beta policy surface, not a general secure-code proof.

## Image and runtime

The Dockerfile has independent `test` and `runtime` targets. The runtime installs only default dependencies, copies runtime application directories, runs as UID 10001, and stores beta state at `/data/eacode-demo.sqlite3`.

## CI proof

The image workflow validates Compose, starts the database/Redis/API stack, proves health and UID, proves `pytest` is absent from runtime, creates durable state, restarts the API, retrieves the same state, then proves the isolated UID 10002 runner boundary. Image publication occurs only after this proof succeeds.
