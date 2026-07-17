# Tasks

- [x] Add strict `CommandProposal`, `CommandPolicy`, `ExecutionPlan`, `FakeToolResult`, and `ExecutionEvidence` contracts.
- [x] Add deterministic executable, argument, timeout, output, and environment policy.
- [x] Add repository-root, working-directory, path-normalization, traversal, and symlink-escape checks.
- [x] Add deterministic plan hashing.
- [x] Add secret redaction and output truncation.
- [x] Add `ToolPort` and deterministic `FakeToolAdapter`.
- [x] Add dry-run and fake evidence generation with `execution_performed=false`.
- [x] Convert execution evidence into the existing `EvidenceRecord` contract.
- [x] Add a non-executing CLI.
- [x] Add optional judge-graph preview and deterministic reevaluation.
- [x] Add focused contract, CLI, security, and graph tests.
- [ ] Add revision-guarded one-time human execution authorization in Spec 0008.
- [ ] Add a real sandboxed tool adapter only after Spec 0008 is green.
- [ ] Add provider-neutral bounded repair after controlled execution evidence is stable.
