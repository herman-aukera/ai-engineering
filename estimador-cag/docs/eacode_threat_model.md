# EACODE Threat Model

Status: active engineering control document  
Current implemented boundary: persistent deterministic judge, dry-run/fake controlled-execution evidence, and revision-guarded one-time execution authorization  
Real command execution: not implemented

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
| arbitrary shell injection | structured executable plus argument arrays; shell metacharacters denied; no subprocess implementation | L2 | OS sandbox before real execution |
| destructive executable | explicit denylist and unknown-executable denial | L2 | policy packaging and admin review |
| repository path traversal | canonical root-bound resolution | L2 | platform-specific path tests during real adapter work |
| symlink escape | resolved path must remain beneath root | L2 | race-resistant pre-start strategy |
| secret exfiltration through output | value-free environment allowlist, output redaction, bounded excerpts | L2 | broader detectors and minimal real environment |
| environment leakage | only names are accepted; values are never persisted | L2 | minimal execution environment construction |
| executor self-approval | adapter returns evidence only; policy and authorization verifier own authority | L2 | independent pre-start verifier in real adapter |
| stale human approval | exact expected and accepted revision must equal current revision | L2 | production revision source |
| replayed approval | one-time nonce hash and consumed authorization/receipt | L2 | durable multi-user replay store when hosted |
| wrong or broadened command scope | exact plan hash and exact scope equality | L2 | immediate pre-start revalidation |
| expired or future authority | explicit replay-safe authorization clock and timezone-aware timestamps | L2 | trusted production clock source |
| unbounded runtime or output | policy timeout and output budgets | L2 contract evidence | real process cancellation and process-tree cleanup |
| poisoned tool output | output is evidence, never authority | L2 contract evidence | tool-output injection tests in repair/provider layers |
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

## Real-execution prerequisites

A real adapter is blocked until all of the following are implemented and tested:

1. valid consumed authorization receipt where policy requires it;
2. independent immediate pre-start verification of plan, revision, scope, expiry, nonce, paths, and execution state;
3. OS-level sandbox or equivalent filesystem/process isolation;
4. safe process creation without shell interpolation;
5. minimal environment construction;
6. timeout, cancellation, and process-tree cleanup;
7. race-resistant path and symlink handling;
8. bounded output streaming and secret redaction;
9. typed rollback plan and rollback evidence;
10. failure-injection and partial-execution tests;
11. disabled-by-default configuration;
12. explicit manual operator smoke with sanitized artifacts.

## Claim boundary

Current evidence supports deterministic command planning, denial, human-gate classification, dry-run/fake behavior, path controls, redaction, exact revision-guarded authorization, replay protection, persisted interrupt/resume, receipts, and graph reevaluation.

Current evidence does not support safe real shell/tool execution, production sandboxing, provider quality, autonomous repair quality, browser product readiness, benchmark superiority, or production readiness.
