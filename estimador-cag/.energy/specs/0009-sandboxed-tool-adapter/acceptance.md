# Spec 0009 — Acceptance

Status: deterministic implementation accepted; manual host evidence pending

## Documentation and SDD

- [x] Requirements define the governed live-tool boundary and hard constraints.
- [x] Design covers authority, full repository snapshot, pre-start verification, process lifecycle, output safety, evidence, CLI, failure injection, and rollback.
- [x] Tasks follow red-green TDD and map to tests.
- [x] Decisions and evidence record the security repair and claim boundary.

## Configuration and authority

- [x] Real execution is disabled by default.
- [x] Secure CLI requires explicit `--live-tool`.
- [x] Fake and dry-run plans cannot become live execution.
- [x] Real execution requires typed `LiveExecutionPlan` and `LiveExecutionIntent`.
- [x] Authority binds to exact plan hash and repository snapshot.
- [x] Snapshot includes HEAD, tree, staged diff, unstaged diff, and untracked-state digest.
- [x] SQLite authority records have integrity checking and restart persistence.
- [x] Nonce replay and receipt reuse fail closed.
- [x] Authority is atomically reserved before process creation and completed once.
- [x] Fabricated or non-authoritative receipts fail closed.
- [x] Expired, stale, mismatched, or untrusted authority fails closed.

## Pre-start verification

- [x] Repository snapshot is recomputed immediately before process creation.
- [x] Executable, arguments, working directory, environment names, timeout, and output budgets are bound to the live contract.
- [x] Path traversal, symlink escape, unsupported executables, and denied Git mutations fail closed.
- [x] Historical real-process adapter is permanently disabled.

## Process lifecycle

- [x] Process creation uses argument lists and `shell=False`.
- [x] Environment is restricted to approved names plus platform essentials.
- [x] API keys and unrelated secrets are not inherited.
- [x] Unix uses a dedicated session/process-group contract.
- [x] Windows uses explicit process-group creation flags.
- [x] Cancellation is polled while the process is active.
- [x] Timeout and cancellation trigger process-tree cleanup.
- [x] Cleanup result is verified rather than assumed.
- [x] Cleanup uncertainty fails closed.
- [x] Process-creation, timeout, cancellation, cleanup, exit, and stream failures remain distinguishable.

## Output and evidence

- [x] stdout and stderr are bounded.
- [x] Truncation flags reflect actual truncation.
- [x] Cross-chunk secrets are detected by final assembled-output redaction.
- [x] Raw unredacted output is not persisted by the secure service.
- [x] `execution_performed=true` is set only after a process starts.
- [x] Evidence links run, plan, intent, repository snapshot, and authorization receipt.
- [x] Authority reservation and completion are recorded separately.
- [x] Evidence serializes and round-trips.
- [x] Executor returns evidence and never accepts the candidate.

## CLI and compatibility

- [x] CLI requires typed live plan, intent, authority database, receipt ID, repository root, trusted actor, and `--live-tool`.
- [x] CLI refusal occurs before receipt reservation when opt-in is absent.
- [x] Legacy fake/failure-injection contracts remain compatible for deterministic CI.
- [x] Legacy adapter cannot call `Popen`.

## CI guarantees

- [x] Ruff passes.
- [x] Python compilation passes.
- [x] Focused Spec 0009 tests pass.
- [x] Full test suite passes.
- [x] Energy Core boundary passes.
- [x] Every smoke and canonical full gate pass.
- [x] Root smoke passes.
- [x] Repository remains clean after CI.
- [x] Deterministic CI makes no real process or provider call.

## Manual host evidence

- [ ] Secure CLI executes one harmless authorized command on the target host.
- [ ] Timeout and child-process cleanup are demonstrated on Windows.
- [ ] Cancellation responsiveness is demonstrated on Windows.
- [ ] Sanitized evidence contains no secret material.
- [ ] No commit, push, merge, reset, or destructive operation occurs during smoke.

## Claim boundary

Allowed:

- Spec 0009 implementation is deterministic-CI accepted.
- Real execution is explicit, disabled by default, snapshot-bound, one-time-authorized, bounded, sanitized, and evidence-producing.
- Fake and injected paths remain the only CI execution modes.

Blocked until manual evidence:

- complete host-level cleanup proof;
- arbitrary untrusted-code safety;
- VM, container, kernel, or production sandbox isolation;
- production readiness.
