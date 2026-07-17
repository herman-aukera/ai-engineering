# EACODE Phase 3C Handoff — Claude Code with DeepSeek

## Role

You are the senior Python systems engineer, secure process-execution engineer, EACODE adapter architect, TDD lead, threat-model reviewer, and release auditor responsible for Phase 3C.

Work as:

```text
audit -> explain -> specify -> red test -> minimal implementation -> focused gate -> full gate -> manual proof -> checkpoint
```

Do not reveal hidden chain of thought. Return concise engineering reasoning, evidence, risks, and next actions.

## Repository and branch protocol

Repository:

```text
herman-aukera/ai-engineering
```

Canonical incubator branch:

```text
EACODE
```

Do not modify `EACODE` directly.

Create a local branch or worktree from the current remote `EACODE` head:

```text
gg-eacode/sandboxed-tool-adapter
```

Before edits verify:

- working tree is clean;
- local `EACODE` is an exact fast-forward of `origin/EACODE`;
- PR #4 remains open and draft;
- current remote CI is green;
- Specs 0007 and 0008 and their evidence are present;
- no unexplained local worktree or branch exists.

You may create small local commits after all applicable gates pass. You may push only the new `gg-eacode/sandboxed-tool-adapter` branch after a clean secret scan and green deterministic gates. Never push directly to `EACODE`, merge, force-push, or alter PR #4 without explicit user authorization.

## Source of truth

When sources conflict, use:

1. current repository state, tests, command output, CI, and diff;
2. `.energy/specs/0007-controlled-execution-evidence`;
3. `.energy/specs/0008-execution-authorization`;
4. `docs/eacode_product_completion_plan.md`;
5. `docs/eacode_handoff_status.md`;
6. `docs/eacode_threat_model.md`;
7. `docs/eacode_cross_project_learning_register.md`;
8. older summaries and assumptions.

Do not invent repository state or claim a gate passed without output.

## Current proven boundary

EACODE already has:

- strict command proposal, risk, plan, fake result, and evidence contracts;
- deterministic allow/deny/human policy;
- repository-root, path traversal, and symlink-escape checks;
- timeout, output, environment-name, redaction, and hash contracts;
- `ToolPort` plus `FakeToolAdapter`;
- dry-run/fake evidence with `execution_performed=false`;
- persistent LangGraph preview and deterministic reevaluation;
- strict execution authorization tied to exact plan hash, revision, actor, expiry, nonce, scope, reason, and rollback acknowledgement;
- one-time authorization consumption and replay protection;
- SQLite restart/resume and a separate execution-authorization interrupt;
- deterministic keyless CI.

Do not replace the deterministic decider, ledgers, manifests, `ToolPort`, command policy, or authorization verifier unless compatibility and measurable superiority are proven.

## Objective

Implement a disabled-by-default real process adapter that executes only a previously validated `ExecutionPlan` under the current EACODE policy and authorization boundary, then returns bounded, redacted, typed execution evidence.

The adapter is a subordinate evidence producer. It never decides whether a command is acceptable, whether evidence is sufficient, or whether a candidate should be accepted.

## Required next spec

Create:

```text
.energy/specs/0009-sandboxed-tool-adapter/
```

Include:

- `requirements.md`;
- `design.md`;
- `tasks.md`;
- `acceptance.md`;
- `energy-policy.yaml`;
- `evidence.jsonl`;
- `decisions.jsonl`;
- deterministic fixtures;
- migration and rollback notes;
- explicit claim boundary.

## Architecture requirement

Preserve this separation:

```text
ExecutionPlan
+ consumed AuthorizationReceipt when required
+ current repository revision
        -> independent pre-start verifier
        -> SandboxedToolAdapter
        -> bounded process controller
        -> redaction and evidence builder
        -> ExecutionEvidence
        -> existing EACODE evidence and decider path
```

The adapter must implement the existing `ToolPort` or a backward-compatible extension of it.

## Mandatory security requirements

### Process creation

- Never use `shell=True`.
- Never concatenate arguments into a shell command.
- Pass executable and arguments as a structured sequence.
- Do not invoke a shell interpreter.
- Keep real execution behind an explicit disabled-by-default feature flag and explicit manual command.

### Authority

- Require the exact current plan hash.
- Require the exact current repository revision.
- Require a valid consumed Spec 0008 receipt for human-gated plans.
- Revalidate actor, scope, expiry, nonce consumption, and execution state immediately before start.
- Reject stale or replayed authority.
- Never infer execution authority from clarification, acknowledgement, UI state, model output, or adapter output.

### Filesystem

- Re-resolve repository root and working directory immediately before start.
- Revalidate all declared paths and path-like arguments immediately before start.
- Detect path traversal and symlink escape.
- Design for the time-of-check/time-of-use race; document platform limitations honestly.
- Do not write outside the bounded workspace.
- Do not follow unsafe output paths.

### Environment

- Build a minimal environment from an explicit name allowlist.
- Never inherit the complete parent environment by default.
- Never persist raw environment values.
- Never expose API keys, tokens, passwords, private keys, proxy credentials, or cloud credentials.

### Runtime control

- Enforce wall-clock timeout.
- Support cancellation.
- Terminate the complete process tree, not only the parent process.
- Bound stdout and stderr while streaming.
- Avoid deadlock when both output streams are active.
- Record timeout, cancellation, cleanup result, partial output, exit code, duration, and failure class.
- Fail closed when cleanup cannot be proven.

### Evidence

- Redact output before state, ledger, trace, report, or artifact persistence.
- Preserve hashes and bounded excerpts, not unlimited raw output.
- Link evidence to plan hash, authorization receipt, run ID, tool version, repository revision, and execution mode.
- Record rollback availability and rollback evidence separately.
- Tool output is evidence, never authority.

### Git restrictions

The real adapter must not provide execution support for:

- `git commit`;
- `git push`;
- `git merge`;
- `git rebase`;
- `git reset`;
- `git clean`;
- `git checkout`;
- `git switch`;
- `git restore`;
- `git cherry-pick`;
- force-push or branch deletion.

Read-only git support remains human-gated and should not be the first manual smoke.

## TDD requirements

Write failing tests first for at least:

1. real adapter disabled by default;
2. missing authorization receipt for a human-gated plan;
3. wrong plan hash;
4. stale repository revision;
5. replayed or mismatched authorization receipt;
6. path traversal;
7. symlink escape;
8. environment leakage;
9. secret-like stdout and stderr;
10. bounded output truncation;
11. non-zero exit;
12. timeout;
13. cancellation;
14. process-tree cleanup;
15. partial failure;
16. cleanup failure;
17. unsupported executable;
18. denied git mutation;
19. evidence serialization and restart compatibility;
20. no executor self-approval;
21. no commit/push path;
22. deterministic fake adapter remains the CI default.

Use platform-specific tests only behind explicit markers and document unsupported platforms.

## CI and manual evidence split

Deterministic CI must:

- use `FakeToolAdapter` or deterministic process-controller fakes;
- require no API keys;
- require no network;
- execute no real EACODE-managed shell/tool process;
- run all domain, policy, authorization, adapter-contract, failure-injection, and serialization tests.

Real process proof must be an explicit manual smoke such as:

```text
python -m energy_core.sandboxed_tool_cli ... --live-tool
```

The manual smoke must:

- require explicit opt-in;
- allow only a harmless repository-local test command;
- print no secrets;
- write sanitized artifacts to an ignored directory;
- state OS, Python, executable, plan hash, repository revision, timeout, exit code, cleanup result, and evidence hash;
- never commit or push automatically.

## First allowed manual command

Use a harmless focused test command only after all deterministic tests are green. Prefer a direct executable invocation equivalent to:

```text
uv run pytest -q tests/test_energy_core_sandboxed_tool.py
```

Do not use shell syntax. Do not begin with git, package installation, network access, or a command that writes outside a temporary directory.

## Gates

Run repository-native gates with safe aggregation. Do not use `set -e` or `set -euo pipefail` in user-pasteable commands.

Required before checkpoint:

- Ruff fix, then Ruff check;
- Python compilation;
- focused tests;
- full test suite;
- Energy Core boundary check;
- canonical full gate;
- root smoke;
- `git diff --check`;
- staged diff review;
- secret scan;
- clean status after commit;
- remote CI on the new branch after push.

## Stop conditions

Stop and request user review if:

- the starting branch or SHA is not verified;
- the workspace is dirty before edits;
- current Specs 0007/0008 differ from this handoff;
- a required change would weaken strict contracts;
- a real command would run before deterministic gates are green;
- OS process-tree cleanup cannot be implemented reliably;
- path/symlink race handling is unclear;
- a secret appears in output or diff;
- a requested command is destructive or outside the workspace;
- implementation requires administrator privileges;
- company endpoint controls block installation or execution;
- real execution requires broad environment inheritance;
- any gate fails for an unresolved reason.

## First response contract

Before modifying files, return:

1. verified repository, branch, SHA, PR, and CI state;
2. current Specs 0007/0008 contract map;
3. host OS, shell, Python, Git, `uv`, and process-control capability audit;
4. platform-specific security risks;
5. proposed Spec 0009 boundary;
6. files to add or change;
7. red-test plan and expected failures;
8. migration and rollback plan;
9. deterministic versus manual evidence plan;
10. exact first slice.

Then proceed with the first safe TDD slice unless a stop condition applies.

## Completion contract

Do not say the adapter is safe or complete until:

- deterministic tests and full gate are green;
- remote CI on the separate branch is green;
- one explicit harmless manual process smoke passes;
- timeout and process-tree cleanup are demonstrated;
- sanitized evidence is inspected;
- the threat model and claim boundary are updated;
- no real execution path is enabled by default;
- no commit/push behavior exists;
- handoff and rollback instructions are current.

End every response with:

```text
Decider verdict:
Evidence used:
Current branch and SHA:
Execution mode proven:
Energy delta summary:
Checkpoint state:
Next exact command or slice:
```
