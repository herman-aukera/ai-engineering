# Requirements: Controlled Execution Evidence

## Operator problem

The deterministic EACODE judge can accept or reject a proposed coding step, but accepted steps cannot yet produce bounded execution evidence. A future executor must remain subordinate to deterministic policy, never approve itself, and never expose secrets or escape the repository boundary.

## Functional requirements

- Define strict typed contracts for command proposals, command risk, execution plans, fake tool results, and execution evidence.
- Accept executable and argument arrays only; do not accept arbitrary shell strings.
- Resolve working directories and declared paths against one explicit repository root.
- reject path traversal and symlink escape.
- Classify executables and arguments deterministically as allowed for fake review, human-required, or denied.
- Enforce timeout, output-size, and environment-name budgets.
- Redact secret-like output before it reaches state, traces, ledgers, or reports.
- Produce dry-run evidence without invoking an adapter.
- Produce deterministic fake-tool evidence for CI without real execution.
- Prevent denied or human-gated plans from reaching the adapter.
- Convert execution evidence into the existing EACODE `EvidenceRecord` contract.
- Allow the persistent judge graph to attach preview evidence and reevaluate through the existing Python decider.
- Expose a CLI for dry-run and deterministic fake review.

## Hard constraints

- No `shell=True`.
- No shell interpreter or arbitrary command string.
- No real subprocess execution in this slice.
- No auto-commit, auto-push, force-push, merge, reset, clean, or checkout execution.
- No command outside the bounded repository root.
- No raw environment dump or credential value in persisted output.
- No executor self-approval.
- `execution_performed` remains false for dry-run and fake modes.
- A denied proposal never reaches a tool adapter.
- Human acknowledgement is not execution authorization.

## Non-functional requirements

- Contracts remain JSON serializable and Pydantic strict.
- Plan hashing is deterministic and sensitive to relevant input changes.
- Tests cover denial, human gating, path escape, symlink escape, redaction, truncation, stable hashing, CLI output, and graph integration.
- Deterministic CI remains keyless and network-free.

## Non-goals

- Real shell execution.
- Production command sandboxing.
- Human execution authorization records.
- Provider-backed actors.
- Aider, Cline, or OpenCode adapters.
- Automatic repository mutation.
