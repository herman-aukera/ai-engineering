# EACODE Threat Model

Status: active engineering control document  
Current implemented boundary: persistent deterministic judge, dry-run/fake controlled-execution evidence, revision-guarded one-time execution authorization, and disabled-by-default sandboxed real-process tool adapter (Spec 0009)  
Real command execution: implemented behind disabled-by-default feature flag; not enabled in CI

## Assets

- repository contents and git history;
- specifications and policies;
- evidence and decision ledgers;
- checkpoint databases;
- human decisions and execution-authorization receipts;
- provider credentials and environment values;
- generated plans, patches, reports, and audit exports.

## Trust boundaries

Untrusted inputs include:

- model and coding-agent output;
- repository text and instructions;
- command proposals and arguments;
- tool stdout and stderr;
- external adapter payloads;
- human-entered free text;
- stale checkpoints and copied approval records.

Trusted authority remains deterministic Python policy plus explicit, exact, independently verified human authorization where required.

## Current threats and controls

| Threat | Current control | Evidence level | Remaining work |
|---|---|---:|---|
| arbitrary shell injection | structured executable plus argument arrays; shell metacharacters denied; subprocess.Popen with shell=False; no shell interpreter | L3 | production container/jail sandbox |
| destructive executable | explicit denylist and unknown-executable denial; config-driven allowed_executables in SandboxedToolConfig | L3 | policy packaging and admin review |
| repository path traversal | canonical root-bound resolution plus immediate pre-start re-validation of all declared paths | L3 | TOCTOU race documented but not eliminated (requires OS sandbox) |
| symlink escape | resolved path must remain beneath root; Path.resolve() called immediately before process start | L3 | TOCTOU race documented but not eliminated (requires OS sandbox) |
| secret exfiltration through output | value-free environment allowlist; per-chunk output redaction before persistence; bounded excerpts in evidence | L3 | broader detectors for credential-like patterns |
| environment leakage | name allowlist only; values never persisted; PATH + SYSTEMROOT only additions | L3 | per-executable environment profiles |
| executor self-approval | adapter returns evidence only; independent _verify_pre_start re-validates plan hash, revision, paths, executable, and authorization before every execution; no self-authorization path | L3 | multi-party authorization for production |
| stale human approval | authorization receipt accepted_revision checked against config.current_revision in pre-start verifier; mismatched revision fails closed | L3 | production revision source |
| replayed approval | one-time nonce hash and consumed authorization/receipt; authorization receipt presence enforced for human-gated plans in pre-start verifier | L3 | durable multi-user replay store when hosted |
| wrong or broadened command scope | exact plan hash and authorization receipt plan_hash match enforced in pre-start verifier and build_evidence | L3 | per-argument scope constraints |
| expired or future authority | explicit replay-safe authorization clock and timezone-aware timestamps; authorization receipt execution_performed flag checked before start | L3 | trusted production clock source |
| unbounded runtime or output | policy timeout enforced via process.wait(timeout); wall-clock timeout with process-tree cleanup; output bounded per-chunk with truncation | L3 | per-command timeout profiles and streaming output budgets |
| poisoned tool output | output is evidence, never authority; all output goes through _redact before persistence | L3 contract evidence | tool-output injection tests in repair/provider layers |
| checkpoint replay conflict | typed graph state, SQLite persistence, revision and nonce guards | L2 | production transaction isolation |
| unsafe rollback | rollback acknowledgement is required; execution rollback is not implemented | L2 contract | typed rollback plan and rollback evidence |
| malicious provider output | no provider actor in current boundary | L0 | strict provider schema, budgets, circuit breaker, fake CI adapter |

## Hard security invariants

- No real command is executed by Specs 0007 or 0008.
- Dry-run, fake evidence, and authorization receipts always keep `execution_performed=false`.
- Denied plans cannot reach an adapter.
- Human-required plans cannot become authorized without exact plan hash, revision, actor, expiry, scope, nonce, reason, and rollback acknowledgement.
- Clarification acknowledgement is never execution authorization.
- No command, adapter, model, or UI may authorize itself.
- No raw environment mapping is accepted or persisted.
- No commit, push, merge, reset, clean, checkout, restore, rebase, cherry-pick, or force-push execution path exists.
- Fake evidence and authorization evidence cannot support a real-execution claim.
- No real process execution without explicit opt-in (SandboxedToolConfig.enabled=True or --live-tool).
- No real process execution in deterministic CI (FailureInjectingAdapter and FakeToolAdapter only).
- Human-gated plans require a valid consumed AuthorizationReceipt verified in _verify_pre_start before process creation.
- All process output is redacted and truncated before evidence persistence.

## Real-execution prerequisites

A real adapter is blocked until all of the following are implemented and tested:

1. [x] valid consumed authorization receipt where policy requires it — _verify_pre_start enforces receipt presence, plan_hash match, revision match, and execution_performed check for human-gated plans;
2. [x] independent immediate pre-start verification of plan, revision, scope, expiry, nonce, paths, and execution state — _verify_pre_start re-validates disposition, authorization, executable, paths, and git subcommands immediately before Popen;
3. [ ] OS-level sandbox or equivalent filesystem/process isolation — current implementation uses process-level controls (no shell, minimal env, path containment, timeout/cleanup) but does not provide container, VM, or jail isolation;
4. [x] safe process creation without shell interpolation — subprocess.Popen with args list, shell=False, stdin=DEVNULL;
5. [x] minimal environment construction — _build_environment passes only allowlisted names plus PATH and SYSTEMROOT; no parent environment inheritance;
6. [x] timeout, cancellation, and process-tree cleanup — process.wait(timeout), _CancelEvent with threading.Event, _kill_process_tree via taskkill (Windows) or killpg (Unix);
7. [~] race-resistant path and symlink handling — paths are re-resolved immediately before process start narrowing the TOCTOU window; the race is not eliminated (requires OS-level sandbox);
8. [x] bounded output streaming and secret redaction — threaded concurrent stdout/stderr reads with per-chunk _redact and per-stream output budget tracking with truncation;
9. [~] typed rollback plan and rollback evidence — rollback_summary is present in ExecutionPlan and ExecutionEvidence records rollback_available; actual rollback execution is not implemented (out of scope);
10. [x] failure-injection and partial-execution tests — FailureInjectingAdapter with inject_timeout, inject_cancellation, inject_non_zero_exit, inject_oversized_output, inject_secret_output, inject_cleanup_failure; partial output preserved on timeout/cancellation;
11. [x] disabled-by-default configuration — SandboxedToolConfig.enabled defaults to False; CLI requires explicit --live-tool flag;
12. [ ] explicit manual operator smoke with sanitized artifacts — blocked on local Python/uv installation; CI validates all deterministic tests.

## Spec 0009 — Sandboxed tool adapter threat additions

### New threats introduced

| Threat | Control | Evidence level | Remaining work |
|---|---|---|---|
| process creation failure | Popen wrapped in try/except; returns cleanup_failure result | L3 | retry/fallback policy |
| child process escape via environment | environment built from explicit name allowlist only; no parent env inheritance; no credential-bearing names | L3 | per-executable environment profiles |
| TOCTOU path race between re-check and Popen | paths re-resolved immediately before process start; documented honestly | L2 | OS-level sandbox (containers, jails) |
| orphaned child processes on adapter crash | process-tree cleanup on timeout/cancellation; best-effort taskkill/killpg | L2 | job objects (Windows) or cgroups (Linux) for guaranteed cleanup |
| authorization receipt tampering | receipt plan_hash, accepted_revision, and execution_performed checked in pre-start verifier | L3 | cryptographic signature on receipts |
| stdout/stderr deadlock | threaded concurrent reads of both streams | L3 | asyncio-based streaming for very large outputs |

### New invariants

- SandboxedToolAdapter.config.enabled defaults to False; no code path executes a real process without explicit opt-in.
- _verify_pre_start is called at the top of every invoke() before any process is created.
- Human-gated plans cannot reach Popen without a valid consumed AuthorizationReceipt whose plan_hash matches, revision matches, and execution_performed is False.
- All output chunks pass through _redact before joining; secrets never reach persisted evidence.
- process.wait(timeout) is enforced on every execution; timeout triggers _kill_process_tree.
- FailureInjectingAdapter is the test harness; no real OS process is created during deterministic CI.
- FakeToolAdapter remains the default adapter in review_execution; Spec 0009 adapter is opt-in only.

## Claim boundary

### Spec 0011 additions

- Semantic judges and the optional meta-judge emit typed evidence but have no authorization field.
- Deterministic hard failures remain vetoes; the action governor owns final disposition.
- Coding proposals are inert data and cannot silently execute.
- Demo execution is explicitly simulated and requires a separate human-authorization record.
- Backend sessions are signed and expiring; OIDC configuration tests do not establish live SSO.
- The API container receives no Docker socket, and the runner container is not claimed as a hostile-code sandbox.

Current evidence supports:

- deterministic command planning, denial, human-gate classification, dry-run/fake behavior, path controls, redaction, exact revision-guarded authorization, replay protection, persisted interrupt/resume, receipts, and graph reevaluation (Specs 0007, 0008);
- disabled-by-default real process execution under the same policy and authorization boundary, with safe process creation (no shell), minimal environment, bounded/redacted output, timeout/cancellation/cleanup, and authorization receipt enforcement (Spec 0009).

Current evidence does not support:

- OS-level sandboxing (containers, VMs, jails);
- guaranteed process-tree cleanup on all platforms;
- elimination of TOCTOU path races;
- production readiness;
- provider quality or autonomous repair;
- browser product readiness;
- benchmark superiority.
