# Spec 0012 — Production Hardening Slice: Tasks

- [x] Replace client-controlled authorization Boolean with separate prepare, authorize, and execute endpoints.
- [x] Verify signed backend sessions and require operator/admin role.
- [x] Add short-lived exact-scope one-time receipts.
- [x] Add atomic replay, actor, scope, and expiry rejection.
- [x] Persist typed demo results and receipts in SQLite.
- [x] Add integrity verification and tamper tests.
- [x] Replace empty hard-gate fixture with concrete deterministic findings.
- [x] Make repaired patch the effective proposal revision.
- [x] Reevaluate the effective proposal after simulated execution.
- [x] Replace expected-label benchmark output with evidence-derived policy execution.
- [x] Add poisoned-label regression proving expected labels cannot control actual decisions.
- [x] Split runtime and test Docker stages.
- [x] Remove the development extra from the runtime image.
- [x] Add Compose persistence volume and API health check.
- [x] Add stack startup, restart, persistence, UID, and runner proof to GitHub Actions.
- [ ] Capture successful remote canonical CI and runtime-proof workflow URLs.
- [ ] Perform manual external deployment only after explicit approval.
