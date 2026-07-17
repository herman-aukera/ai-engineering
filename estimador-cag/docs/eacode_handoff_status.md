# EACODE Handoff Status

Date: 2026-07-17  
Repository: `herman-aukera/ai-engineering`  
Branch: `EACODE`  
PR: #4, open draft, do not merge as routine coursework

## Current maturity

- Phase 0: audit and product completion plan — complete.
- Phase 1: versioned trust, hashing, recovery, retention, manifests — complete.
- Phase 2: persistent deterministic LangGraph judge, SQLite restart, human clarification/escalation — complete.
- Phase 3A / Spec 0007: controlled planning plus dry-run/fake execution evidence — complete and L2 validated.
- Phase 3B / Spec 0008: revision-guarded one-time execution authorization — complete and L2 validated.
- Phase 3C: real sandboxed tool adapter — not implemented; delegation target.
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

## Validation evidence

Remote CI run `29610086661` validated final head `f7f168acf68323dc1fc34ab5aaba66a1ba1196d3` and passed:

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
- The controlled-execution and authorization boundary is remotely CI validated.

Not allowed:

- safe real shell/tool execution;
- production sandboxing;
- provider integration;
- autonomous repair quality;
- benchmark superiority;
- browser product readiness;
- production readiness.

## Delegated next slice

Phase 3C — Real Sandboxed Tool Adapter.

The delegated implementation must:

1. preserve the current `ToolPort` and all strict Spec 0007/0008 contracts;
2. require a valid consumed authorization receipt for human-gated plans;
3. never use `shell=True` or shell interpolation;
4. construct a minimal allow-listed environment;
5. revalidate repository root, working directory, paths, and symlinks immediately before process start;
6. enforce timeout, cancellation, and process-tree cleanup;
7. stream bounded output through redaction before persistence;
8. record partial failure, exit code, duration, hashes, truncation, rollback availability, and authorization references;
9. remain disabled by default and absent from deterministic CI execution;
10. use fake tools in CI and a separate explicit manual `--live-tool` smoke for real process proof;
11. implement failure injection for timeout, cancellation, non-zero exit, oversized output, secret-like output, path race, and unavailable rollback;
12. add no commit, push, merge, reset, clean, checkout, or force-push capability.

This slice requires a local coding agent because it needs operating-system process control, filesystem race inspection, repeated local tests, and manual sanitized tool evidence.

## Resume commands

```text
git fetch origin
git switch EACODE
git pull --ff-only
git status --short -uall
git log --oneline --decorate -20
```

Run the canonical deterministic full gate, confirm the current remote CI is green, then start the delegated adapter on a new local branch or worktree. Do not work directly on `EACODE` with an autonomous agent.
