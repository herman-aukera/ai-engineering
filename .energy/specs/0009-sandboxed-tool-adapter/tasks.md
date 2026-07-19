# Spec 0009 — Implementation Tasks

## Phase 1: Spec and contracts

- [ ] T001 — Create `requirements.md`
- [ ] T002 — Create `design.md`
- [ ] T003 — Create `energy-policy.yaml`
- [ ] T004 — Create `acceptance.md`
- [ ] T005 — Create `evidence.jsonl` and `decisions.jsonl`
- [ ] T006 — Create deterministic fixtures

## Phase 2: Red tests (TDD — all failing)

- [ ] T007 — `test_adapter_disabled_by_default`
- [ ] T008 — `test_missing_authorization_for_human_gated_plan`
- [ ] T009 — `test_wrong_plan_hash_rejected`
- [ ] T010 — `test_stale_repository_revision_rejected`
- [ ] T011 — `test_replayed_authorization_rejected`
- [ ] T012 — `test_path_traversal_rejected`
- [ ] T013 — `test_symlink_escape_rejected`
- [ ] T014 — `test_environment_leakage_prevented`
- [ ] T015 — `test_secret_like_stdout_redacted`
- [ ] T016 — `test_bounded_output_truncation`
- [ ] T017 — `test_non_zero_exit_recorded`
- [ ] T018 — `test_timeout_enforced`
- [ ] T019 — `test_cancellation_supported`
- [ ] T020 — `test_process_tree_cleanup`
- [ ] T021 — `test_partial_failure_recorded`
- [ ] T022 — `test_cleanup_failure_fails_closed`
- [ ] T023 — `test_unsupported_executable_rejected`
- [ ] T024 — `test_denied_git_mutation`
- [ ] T025 — `test_evidence_serialization_and_restart`
- [ ] T026 — `test_no_executor_self_approval`
- [ ] T027 — `test_no_commit_push_path`
- [ ] T028 — `test_deterministic_fake_adapter_remains_ci_default`

## Phase 3: Core implementation

- [ ] T029 — Implement `SandboxedToolConfig`
- [ ] T030 — Implement `RealToolResult`
- [ ] T031 — Implement pre-start verifier
- [ ] T032 — Implement environment constructor
- [ ] T033 — Implement path/symlink re-resolver
- [ ] T034 — Implement process creator (`subprocess.Popen`, no shell)
- [ ] T035 — Implement output streamer with redaction and truncation
- [ ] T036 — Implement timeout enforcement and process-tree cleanup
- [ ] T037 — Implement cancellation support
- [ ] T038 — Implement `SandboxedToolAdapter.invoke()`
- [ ] T039 — Implement evidence builder
- [ ] T040 — Implement failure injection adapter

## Phase 4: CLI

- [ ] T041 — Implement `sandboxed_tool_cli.py` with `--live-tool` flag

## Phase 5: Integration

- [ ] T042 — Extend `review_execution()` to accept `SandboxedToolAdapter`
- [ ] T043 — Ensure `FakeToolAdapter` remains CI default
- [ ] T044 — Run ruff fix, ruff check, Python compilation

## Phase 6: Gates

- [ ] T045 — Focused tests green (test_energy_core_sandboxed_tool.py)
- [ ] T046 — Full test suite green
- [ ] T047 — Energy Core boundary check
- [ ] T048 — Canonical full gate
- [ ] T049 — Root smoke
- [ ] T050 — `git diff --check`
- [ ] T051 — Staged diff review
- [ ] T052 — Secret scan
- [ ] T053 — Clean status after commit
- [ ] T054 — Push branch and verify remote CI

## Phase 7: Manual evidence

- [ ] T055 — Manual `--live-tool` smoke with harmless command
- [ ] T056 — Timeout and process-tree cleanup demonstration
- [ ] T057 — Sanitized evidence inspection
- [ ] T058 — Update threat model and claim boundary
- [ ] T059 — Update handoff and rollback instructions
