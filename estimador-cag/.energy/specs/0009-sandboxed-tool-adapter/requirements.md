# Spec 0009 — Sandboxed Tool Adapter Requirements

Status: implementation in progress
Product owner: EACODE
Depends on: Spec 0007 (controlled execution evidence), Spec 0008 (execution authorization)

## Operator problem

EACODE can deterministically plan, deny, human-gate, and produce dry-run/fake execution evidence. It can also issue and consume exact revision-guarded one-time execution authorization. But no real process has ever been executed under EACODE control. A real adapter is needed to produce bounded, redacted, typed execution evidence for a previously validated `ExecutionPlan` under the existing policy and authorization boundary — but it must remain disabled by default, never self-approve, and never expose secrets or escape the repository boundary.

## Functional requirements

### REQ-001 — Disabled by default

The real adapter shall be disabled by default. Real execution shall require an explicit opt-in feature flag (`enabled=True`) or explicit CLI flag (`--live-tool`). Without explicit opt-in, the adapter shall refuse to create any process.

### REQ-002 — ToolPort compatibility

The adapter shall implement the existing `ToolPort` protocol or a backward-compatible extension that accepts `ExecutionPlan` and returns structured evidence. Existing `FakeToolAdapter` callers shall continue to work without change.

### REQ-003 — Independent pre-start verification

Immediately before process creation, the adapter shall independently revalidate:

- plan hash matches the supplied plan;
- repository revision matches current authoritative revision;
- plan disposition allows execution (not denied);
- if the plan requires human authorization, a valid consumed `AuthorizationReceipt` is present;
- authorization is not stale, replayed, or expired;
- repository root and working directory resolve correctly;
- all declared paths and path-like arguments are within the repository root;
- no symlink escape exists at time of check.

### REQ-004 — Safe process creation

The adapter shall:

- never use `shell=True` or any shell interpreter;
- pass executable and arguments as a structured sequence;
- never concatenate arguments into a shell command string;
- resolve the executable against an explicit allowlist.

### REQ-005 — Minimal environment construction

The adapter shall:

- build a process environment from an explicit name allowlist only;
- never inherit the complete parent environment;
- never persist raw environment values;
- never expose API keys, tokens, passwords, private keys, proxy credentials, or cloud credentials.

### REQ-006 — Runtime control

The adapter shall:

- enforce a wall-clock timeout;
- support cancellation via an external signal;
- terminate the complete process tree, not only the parent process;
- bound stdout and stderr while streaming;
- avoid deadlock when both output streams are active.

### REQ-007 — Evidence production

The adapter shall:

- redact secret-like output before persistence;
- preserve hashes and bounded excerpts, not unlimited raw output;
- link evidence to plan hash, authorization receipt, run ID, tool version, repository revision, and execution mode;
- record timeout, cancellation, cleanup result, partial output, exit code, duration, and failure class;
- set `execution_performed=true` for real executions.

### REQ-008 — Git restrictions

The adapter shall not execute:

- `git commit`, `git push`, `git merge`, `git rebase`, `git reset`, `git clean`, `git checkout`, `git switch`, `git restore`, `git cherry-pick`, force-push, or branch deletion.

Read-only git commands remain human-gated and shall not be the first manual smoke.

### REQ-009 — Failure injection support

The adapter shall support deterministic failure injection for testing:

- timeout simulation;
- cancellation during execution;
- non-zero exit;
- oversized output;
- secret-like output;
- path race detection;
- unavailable rollback.

### REQ-010 — Deterministic CI compatibility

Deterministic CI shall use `FakeToolAdapter` or equivalent deterministic fakes only. No real process execution shall occur in CI.

## Hard constraints

- No `shell=True`.
- No shell interpreter or arbitrary command string.
- No real execution without explicit opt-in.
- No executor self-approval.
- No commit, push, merge, reset, clean, checkout, restore, rebase, cherry-pick, or force-push.
- No command outside the bounded repository root.
- No raw environment dump or credential value in persisted output.
- No execution without valid consumed authorization for human-gated plans.
- `execution_performed=true` only for real execution with verified authority.
- Fake evidence and authorization evidence cannot support a real-execution claim.

## Non-functional requirements

- Contracts remain JSON serializable and Pydantic strict.
- Adapter is platform-aware (Windows process-tree cleanup via job objects or `taskkill /F /T`; Unix via process groups).
- Tests cover all 22 TDD scenarios from the handoff.
- Secret redaction covers API key patterns, Bearer tokens, private key headers, and key=value credential patterns.
- Time-of-check/time-of-use race is documented honestly; platform limitations are explicit.

## Non-goals

- Production sandboxing (containers, VMs, jails).
- Multi-user authorization service.
- Provider-backed actor generation.
- Autonomous repair execution.
- Network-isolated execution (beyond not inheriting proxy credentials).
- Cross-platform parity beyond what CPython stdlib supports.

## Claim boundary

Allowed after implementation:

- EACODE can execute a single validated command under strict policy and authorization.
- Execution evidence is bounded, redacted, typed, and linked to authorization records.
- No real execution path is enabled by default.
- Deterministic CI uses fake adapters only.

Not allowed after implementation:

- Production readiness.
- Safe execution of arbitrary untrusted commands.
- Multi-tenant isolation.
- Network security guarantees.
