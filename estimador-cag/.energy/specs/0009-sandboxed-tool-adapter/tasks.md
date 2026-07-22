# Spec 0009 — Implementation Tasks

Status: deterministic implementation complete; manual host evidence open

## SDD and recovery

- [x] Requirements, design, policy, acceptance, decisions, evidence, and fixtures exist.
- [x] Rescue audit identified fake-to-live promotion, incomplete snapshot authority, receipt provenance, cleanup, cancellation, truncation, and redaction defects.
- [x] Repair was developed on an isolated branch and draft PR.

## Typed authority and snapshot

- [x] Add typed live plan and intent.
- [x] Prove fake and dry-run plans cannot invoke real processes.
- [x] Capture HEAD, tree, staged diff, unstaged diff, and untracked-state digest.
- [x] Bind plan, intent, receipt, executable, arguments, working directory, environment names, timeout, output budget, and snapshot hashes.
- [x] Add authoritative pre-start verifier.

## Persistent one-time authorization

- [x] Add SQLite live-authorization request and receipt contracts.
- [x] Add trusted actors, expiry, scope, reason, and rollback acknowledgement.
- [x] Add nonce replay protection.
- [x] Add record integrity verification and tamper detection.
- [x] Prove restart persistence.
- [x] Add atomic pre-start reservation.
- [x] Add one-time execution completion.
- [x] Reject fabricated, stale, mismatched, replayed, reserved, or completed receipts.

## Secure process lifecycle

- [x] Create argument-list process with `shell=False`.
- [x] Restrict environment inheritance.
- [x] Start platform-appropriate process group/session.
- [x] Poll cancellation while running.
- [x] Enforce timeout.
- [x] Verify process-tree cleanup.
- [x] Fail closed on cleanup uncertainty.
- [x] Distinguish process-creation, timeout, cancellation, cleanup, exit, and stream failures.

## Output and evidence

- [x] Bound stdout and stderr.
- [x] Record accurate truncation.
- [x] Redact split secrets through final assembled-output sanitation.
- [x] Normalize execution evidence.
- [x] Preserve authority reservation and completion separately.
- [x] Return evidence for critic/decider reevaluation without executor self-approval.

## CLI and compatibility

- [x] Secure CLI requires typed live artifacts, authority database, receipt ID, actor, revision, repository root, and `--live-tool`.
- [x] Refusal occurs before authority reservation when opt-in is absent.
- [x] Historical real-process adapter is permanently disabled.
- [x] Deterministic failure-injection compatibility is preserved.

## Deterministic validation

- [x] Red tests failed for the intended missing contracts.
- [x] Focused tests pass.
- [x] Full tests pass.
- [x] Ruff passes.
- [x] Python compilation passes.
- [x] Energy Core boundary passes.
- [x] Every smoke and canonical full gate pass.
- [x] Root smoke passes.
- [x] Repository cleanliness passes.
- [x] Temporary diagnostic workflows are removed.
- [x] Remote branch CI is green.

## Manual host evidence

- [ ] Run harmless secure CLI command on the target host.
- [ ] Demonstrate timeout and process-tree cleanup on Windows.
- [ ] Demonstrate prompt cancellation on Windows.
- [ ] Inspect sanitized evidence and confirm no secrets.
- [ ] Update evidence ledger with manual artifact hashes.
