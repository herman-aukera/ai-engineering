# Tasks

- [x] Add strict authorization scope, authorization, context, decision, and receipt contracts.
- [x] Bind authorization to exact plan hash and exact current revision.
- [x] Add trusted actor, timezone-aware expiry, reason, rollback acknowledgement, and consumed state.
- [x] Add nonce hashing and replay detection.
- [x] Add deterministic verification and one-time consumption.
- [x] Add verify/consume CLI with replay-safe output files.
- [x] Add a separate LangGraph execution-authorization interrupt.
- [x] Persist interrupt/resume across SQLite restart.
- [x] Sanitize raw nonce in graph state and append authorization evidence.
- [x] Preserve `execution_performed=false` after authorization.
- [x] Add focused domain, CLI, replay, cancellation, and graph persistence tests.
- [ ] Add production identity-source integration during deployment engineering.
- [ ] Add a real sandboxed tool adapter in the delegated next phase.
