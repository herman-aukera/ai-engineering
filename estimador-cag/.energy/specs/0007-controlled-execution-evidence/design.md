# Design: Controlled Execution Evidence

## Architecture

```text
Accepted Candidate
  -> CommandProposal
  -> deterministic CommandPolicy
  -> ExecutionPlan
       -> deny
       -> human_required
       -> allow_fake
  -> dry-run or FakeToolAdapter
  -> ExecutionEvidence
  -> existing EvidenceRecord
  -> existing deterministic decider reevaluation
```

The domain module owns contracts, risk classification, path boundaries, budgets, redaction, deterministic hashing, and evidence conversion. It has no subprocess dependency.

The CLI is a thin adapter that reads JSON and renders JSON or text. It cannot enable real execution.

The LangGraph judge accepts an optional command proposal only after the candidate decision is `accept`. It builds preview evidence, appends the normalized evidence record, and reevaluates with the existing Python decider. Candidate acceptance and execution authorization remain separate facts.

## Risk policy

- `pytest` and `ruff` are low-risk fake-preview executables.
- `python`, `python3`, and `uv` are medium-risk fake-preview executables.
- read-only `git` proposals require a future human execution authorization.
- repository-mutating git subcommands are denied.
- shell interpreters, destructive utilities, network transfer tools, and unknown executables are denied.
- shell metacharacters are denied even though arguments are structured, preventing later adapters from reassembling unsafe shell strings.

## Boundary model

The repository root must exist. Working directories resolve strictly beneath that root. Declared paths and path-like arguments resolve canonically. Existing symlinks are followed during resolution, so symlink escape fails the same root-boundary check.

## Evidence model

Dry-run evidence records that policy and boundaries passed without adapter invocation. Fake evidence records deterministic fixture output, exit code, duration, plan hash, output hash, truncation, redaction status, and rollback availability. Both modes keep `execution_performed=false`.

Fake evidence proves the supervision path, not real command behavior.

## Migration and compatibility

The change is additive. Existing `CandidateState`, `EnergyDecision`, ledgers, SQLite checkpoints, and no-command graph traces remain valid. Optional graph fields do not alter runs without a command proposal. `GRAPH_VERSION` remains `1.0.0` because the added state is optional and existing checkpoints remain structurally compatible.

## Rollback

Revert the controlled-execution modules, tests, spec packet, and optional graph nodes. Existing judge runs without command proposals continue through the original route. No persisted ledger or database migration is required.

## Security boundary

No real executor exists in this slice. A future real adapter must implement the same `ToolPort`, add OS-level sandboxing, use revision-guarded one-time authorization, and prove timeout, cancellation, process-tree cleanup, filesystem isolation, and rollback before it can be enabled.
