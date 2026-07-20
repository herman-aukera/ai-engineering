# EACODE Handoff Status

Date: 2026-07-20  
Repository: `herman-aukera/ai-engineering`  
Branch: `EACODE`  
PR: #4 (EACODE deterministic judge, open draft), #12 (Spec 0009 sandboxed tool adapter, open draft)  
Do not merge as routine coursework

## Current maturity

- Phase 0: audit and product completion plan — complete.
- Phase 1: versioned trust, hashing, recovery, retention, manifests — complete.
- Phase 2: persistent deterministic LangGraph judge, SQLite restart, human clarification/escalation — complete.
- Phase 3A / Spec 0007: controlled planning plus dry-run/fake execution evidence — complete and L2 validated.
- Phase 3B / Spec 0008: revision-guarded one-time execution authorization — complete and L2 validated.
- Phase 3C / Spec 0009: disabled-by-default sandboxed real-process tool adapter — implemented, CI-validated (L3); manual smoke pending local Python/uv.
- Provider actors and autonomous repair — not implemented.

## Completed deterministic boundary

### Spec 0007

- strict command proposal, policy, plan, fake result, and evidence contracts;
- deterministic executable and argument policy;
- root, working-directory, path traversal, and symlink escape checks;
- timeout, output, and environment-name budgets;
- deterministic plan hashing;
- secret redaction and output truncation;
- fake tool port and adapter;
- dry-run and fake evidence with `execution_performed=false`;
- conversion to the existing `EvidenceRecord`;
- controlled-execution preview CLI;
- optional judge-graph preview, evidence append, and deterministic reevaluation.

### Spec 0008

- strict authorization scope, authorization, context, decision, and receipt contracts;
- exact plan-hash and revision binding;
- explicit trusted actors;
- timezone-aware creation and expiry;
- one-time nonce hashing and replay rejection;
- exact scope and rollback-acknowledgement checks;
- deterministic verify and consume operations;
- verify/consume CLI with replay-safe artifacts;
- separate execution-authorization LangGraph interrupt;
- SQLite restart/resume proof;
- sanitized consumed authorization, receipt, and normalized evidence;
- cancellation and fail-closed paths;
- `execution_authorized` and `execution_performed` preserved as distinct facts.

### Spec 0009

- SandboxedToolConfig with enabled=False by default; explicit opt-in required for real execution;
- independent pre-start verifier re-validates plan disposition, authorization receipt (plan_hash, revision, execution_performed), executable allowlist/denylist, and git subcommand restrictions;
- safe process creation via subprocess.Popen with args list, shell=False, stdin=DEVNULL;
- minimal environment construction from name allowlist only (plus PATH and SYSTEMROOT);
- threaded concurrent stdout/stderr streaming with per-chunk redaction and per-stream output budget tracking;
- wall-clock timeout enforcement with process-tree cleanup (taskkill on Windows, killpg on Unix);
- cancellation support via threading.Event;
- RealToolResult recording exit_code, duration_ms, timed_out, cancelled, process_tree_cleaned, cleanup_error, failure_class, stdout_truncated, stderr_truncated, redacted;
- ExecutionEvidence with execution_performed=True for real executions;
- FailureInjectingAdapter for deterministic CI with 6 injection modes (timeout, cancellation, non_zero_exit, oversized_output, secret_output, cleanup_failure);
- SandboxedToolAdapter implements ToolPort-compatible invoke(plan, authorization_receipt=None) -> RealToolResult;
- CLI with --live-tool gate and --authorization-receipt support;
- 52 deterministic tests covering all 22 TDD scenarios;
- 11 git subcommands denied; no commit, push, merge, reset, clean, checkout, restore, rebase, cherry-pick, or force-push path.

## Validation evidence

Spec 0009 CI (PR #12) validated head `6342a39` and passed:
- Ruff;
- Python compilation;
- Energy Core boundary check;
- full test suite, including all 52 sandboxed-tool-adapter tests and all existing Spec 0007/0008 tests;
- canonical Energy Core full gate.

Earlier EACODE baseline CI run `29610664941` validated head `3c136659bba9612e27a5a9e97957b0c13f0fa70d` and passed:

- Ruff;
- Python compilation;
- Energy Core boundary check;
- full test suite, including Spec 0007 and Spec 0008 domain, CLI, security, replay, SQLite, and graph tests;
- every existing smoke script;
- canonical Energy Core full gate;
- root compatibility smoke;
- repository cleanliness.

## Claim boundary

Allowed:

- EACODE can deterministically plan, deny, or human-gate structured command proposals.
- EACODE can produce bounded dry-run and fake execution evidence.
- EACODE can consume one exact trusted authorization tied to plan hash, revision, scope, actor, expiry, nonce, reason, and rollback acknowledgement.
- EACODE persists authorization interrupts and resumes across SQLite process restart.
- EACODE reevaluates normalized evidence through the existing Python decider.
- EACODE can execute a single validated command under strict policy and authorization, producing bounded, redacted, typed execution evidence (Spec 0009, disabled by default).
- The controlled-execution, authorization, and sandboxed-execution boundary is remotely CI validated.

Not allowed:

- production sandboxing (containers, VMs, jails);
- guaranteed process-tree cleanup on all platforms;
- elimination of TOCTOU path races;
- provider integration;
- autonomous repair quality;
- benchmark superiority;
- browser product readiness;
- production readiness.

## Delegated next slice

The Spec 0009 implementation is CI-validated. Remaining work:

1. Manual `--live-tool` smoke with harmless repository-local command (blocked: Python/uv not installed locally);
2. Timeout and process-tree cleanup demonstration on real OS processes;
3. Provider capability registry and selector (Spec 0010 runtime);
4. Context compaction contracts and deterministic fixtures (Spec 0010 runtime).

## Resume commands

```text
git fetch origin
git switch EACODE
git pull --ff-only
git status --short -uall
git log --oneline --decorate -20
```

Run the canonical deterministic full gate, confirm the current remote CI is green, then start the delegated adapter on a new local branch or worktree. Do not work directly on `EACODE` with an autonomous agent.
