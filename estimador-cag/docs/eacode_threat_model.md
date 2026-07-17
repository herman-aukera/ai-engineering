# EACODE Threat Model

Status: active engineering control document  
Current implemented boundary: deterministic judge plus dry-run/fake controlled-execution evidence  
Real command execution: not implemented

## Assets

- repository contents and git history;
- specifications and policies;
- evidence and decision ledgers;
- checkpoint databases;
- human decisions and future execution authorizations;
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

Trusted authority remains deterministic Python policy plus explicit, validated human authorization where required.

## Current threats and controls

| Threat | Current control | Evidence level | Remaining work |
|---|---|---:|---|
| arbitrary shell injection | structured executable plus argument arrays; shell metacharacters denied; no subprocess implementation | L2 after CI | OS sandbox before real execution |
| destructive executable | explicit denylist and unknown-executable denial | L2 after CI | policy packaging and admin review |
| repository path traversal | canonical root-bound resolution | L2 after CI | platform-specific path tests |
| symlink escape | resolved path must remain beneath root | L2 after CI | race-resistant open/execute strategy |
| secret exfiltration through output | value-free environment allowlist, output redaction, bounded excerpts | L2 after CI | broader detectors and secret manager integration |
| environment leakage | only environment variable names are accepted; values are never persisted | L2 after CI | minimal execution environment construction |
| executor self-approval | adapter returns evidence only; policy owns disposition | L2 after CI | independent authorization verifier |
| stale or replayed approval | no execution authorization exists yet | L0 | revision, plan hash, actor, expiry, and one-time nonce in Spec 0008 |
| unbounded runtime or output | policy timeout and output budgets | L2 contract evidence | real process cancellation and process-tree cleanup |
| poisoned tool output | output is evidence, never authority | L2 contract evidence | tool-output injection tests in repair/provider layers |
| checkpoint replay conflict | typed graph state and current SQLite checkpointing | L2 | revision guards around execution transitions |
| unsafe rollback | rollback summary is recorded but not executed | L1/L2 contract | typed rollback plan and rollback evidence |
| malicious provider output | no provider actor in this slice | L0 | strict provider schema, budgets, circuit breaker, fake CI adapter |

## Hard security invariants

- No real command is executed by Spec 0007.
- Dry-run and fake evidence always keep `execution_performed=false`.
- Denied and human-required plans cannot reach the fake adapter.
- No command, adapter, model, or UI may authorize itself.
- No raw environment mapping is accepted or persisted.
- No commit, push, merge, reset, clean, checkout, or force-push execution path exists.
- Fake evidence cannot support a real-execution claim.

## Real-execution prerequisites

A real adapter is blocked until all of the following are implemented and tested:

1. revision-guarded one-time human authorization tied to an exact plan hash;
2. OS-level sandbox or equivalent filesystem/process isolation;
3. safe process creation without shell interpolation;
4. timeout, cancellation, and process-tree cleanup;
5. minimal environment construction;
6. race-resistant path and symlink handling;
7. bounded output streaming and secret redaction;
8. typed rollback plan and evidence;
9. failure-injection and partial-execution tests;
10. manual operator smoke with sanitized artifacts.

## Claim boundary

Current evidence may support: deterministic planning, denial, human-gate classification, dry-run behavior, fake-adapter behavior, path controls, redaction, and graph reevaluation.

Current evidence does not support: safe real shell execution, production sandboxing, provider quality, autonomous repair quality, or production readiness.
