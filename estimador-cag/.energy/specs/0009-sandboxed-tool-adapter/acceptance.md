# Spec 0009 — Acceptance

## Documentation acceptance

- [x] Requirements define 10 functional requirements with hard constraints.
- [x] Design covers architecture, contracts, pre-start verification, process creation, environment, output streaming, timeout/cancellation, process-tree cleanup, evidence, CLI, failure injection, and platform strategy.
- [x] TDD tasks specify 22 red tests matching the handoff.
- [x] Hard invariants match the threat model prerequisites.

## Runtime acceptance — required before implementation may be called complete

### Configuration and safety

- [ ] SandboxedToolAdapter is disabled by default (`enabled=False`).
- [ ] `--live-tool` flag is required for real execution via CLI.
- [ ] Without opt-in, all execution paths raise a clear error.

### Pre-start verification

- [ ] Missing authorization for human-gated plan fails closed.
- [ ] Wrong plan hash fails closed.
- [ ] Stale repository revision fails closed.
- [ ] Replayed or mismatched authorization receipt fails closed.
- [ ] Expired authorization fails closed.
- [ ] Path traversal attempt fails closed.
- [ ] Symlink escape attempt fails closed.
- [ ] Unsupported executable fails closed.
- [ ] Denied git mutation fails closed.

### Process execution

- [ ] No `shell=True` anywhere in the code path.
- [ ] Environment contains only allowlisted names plus PATH and SYSTEMROOT.
- [ ] No API keys, tokens, or secrets in the process environment.
- [ ] Timeout terminates the process tree.
- [ ] Cancellation terminates the process tree.
- [ ] Non-zero exit is recorded correctly.
- [ ] Partial output is collected on timeout/cancellation.

### Output safety

- [ ] Secret-like stdout is redacted.
- [ ] Secret-like stderr is redacted.
- [ ] Output is truncated at the plan's max_output_chars limit.
- [ ] Redaction status and truncation status are recorded in evidence.

### Evidence integrity

- [ ] `execution_performed=true` for real executions.
- [ ] Evidence links to plan hash, authorization receipt, run ID, revision.
- [ ] Evidence serialization round-trips correctly.
- [ ] Evidence is compatible with existing `EvidenceRecord` conversion.

### CI guarantees

- [ ] Deterministic CI uses `FakeToolAdapter` only.
- [ ] No real process execution occurs in CI.
- [ ] All domain, policy, authorization, adapter-contract, failure-injection, and serialization tests pass in CI.

### Manual smoke

- [ ] `--live-tool` executes a harmless command (e.g., `uv run pytest -q`) and prints sanitized evidence.
- [ ] Timeout and process-tree cleanup are demonstrated.
- [ ] No secrets appear in the manual smoke output.
- [ ] No commit or push occurs during manual smoke.

### Git restrictions

- [ ] Every denied git subcommand is rejected.
- [ ] Read-only git commands remain human-gated.
- [ ] No commit, push, merge, reset, clean, checkout, restore, rebase, cherry-pick, or force-push path exists.

### Gates

- [ ] Ruff check passes with no errors.
- [ ] Python compilation succeeds.
- [ ] Focused tests (test_energy_core_sandboxed_tool.py) all pass.
- [ ] Full test suite passes with no regressions.
- [ ] Energy Core boundary check passes.
- [ ] Canonical full gate passes.
- [ ] Remote CI on the branch is green.

## Claim boundary

Until all runtime gates pass:

- Architecture, requirements, design, and acceptance criteria are documented.
- Red tests are written and fail for the correct reasons.
- Implementation exists behind `enabled=False`.
- Deterministic fake adapter remains the only CI path.

After all runtime gates pass:

- EACODE can execute a single validated command under strict policy and authorization.
- Execution evidence is bounded, redacted, typed, and linked to authorization records.
- No real execution path is enabled by default.
- Deterministic CI uses fake adapters only.
- Manual smoke produces sanitized real-execution evidence.
