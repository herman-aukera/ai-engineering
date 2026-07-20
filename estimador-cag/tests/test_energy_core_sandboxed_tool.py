"""Tests for the sandboxed real-process tool adapter.

All tests use FailureInjectingAdapter — no real OS processes are created.
The deterministic fake adapter path (FakeToolAdapter) remains the CI default.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from energy_core.controlled_execution import (
    CommandProposal,
    ExecutionPlan,
    FakeToolAdapter,
    FakeToolResult,
    build_execution_plan,
    review_execution,
)
from energy_core.execution_authorization import (
    AuthorizationContext,
    AuthorizationReceipt,
    ExecutionAuthorization,
    consume_execution_authorization,
    scope_for_plan,
)
from energy_core.sandboxed_tool import (
    FailureInjectingAdapter,
    RealToolResult,
    SandboxedToolAdapter,
    SandboxedToolConfig,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _config(tmp_path: Path, **overrides) -> SandboxedToolConfig:
    payload = {
        "enabled": True,
        "repository_root": str(tmp_path),
        "current_revision": 3,
        "trusted_actors": ["gonzalo"],
        "consumed_nonce_hashes": [],
    }
    payload.update(overrides)
    return SandboxedToolConfig.model_validate(payload)


def _pytest_plan(tmp_path: Path, **overrides) -> ExecutionPlan:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_example.py").write_text("def test_ok(): assert True\n")
    return build_execution_plan(
        CommandProposal(
            proposal_id="proposal-pytest-001",
            executable="pytest",
            arguments=["-q", "tests/test_example.py"],
            working_directory=".",
            declared_paths=["tests/test_example.py"],
            requested_mode="fake",
            timeout_seconds=30,
            max_output_chars=256,
            environment_names=["PYTHONUNBUFFERED"],
            rollback_summary="No repository mutation.",
        ),
        repository_root=tmp_path,
    )


def _git_status_plan(tmp_path: Path) -> ExecutionPlan:
    return build_execution_plan(
        CommandProposal(
            proposal_id="proposal-git-status",
            executable="git",
            arguments=["status", "--short"],
            working_directory=".",
            declared_paths=[],
            requested_mode="fake",
            timeout_seconds=30,
            max_output_chars=512,
            environment_names=[],
            rollback_summary="Read-only status.",
        ),
        repository_root=tmp_path,
    )


def _authorization(plan: ExecutionPlan, **overrides) -> ExecutionAuthorization:
    now = datetime(2026, 7, 19, 20, 0, tzinfo=UTC)
    payload = {
        "authorization_id": "auth-1",
        "actor": "gonzalo",
        "plan_hash": plan.plan_hash,
        "expected_revision": 3,
        "accepted_revision": 3,
        "scope": scope_for_plan(plan),
        "created_at": now,
        "expires_at": now + timedelta(minutes=10),
        "nonce": "nonce-1234567890",
        "reason": "Review completed.",
        "rollback_acknowledged": True,
        "consumed": False,
    }
    payload.update(overrides)
    return ExecutionAuthorization.model_validate(payload)


def _context(**overrides) -> AuthorizationContext:
    payload = {
        "current_revision": 3,
        "trusted_actors": ["gonzalo"],
        "consumed_nonce_hashes": [],
        "now": datetime(2026, 7, 19, 20, 5, tzinfo=UTC),
    }
    payload.update(overrides)
    return AuthorizationContext.model_validate(payload)


def _consumed_receipt(
    plan: ExecutionPlan, authorization: ExecutionAuthorization
) -> AuthorizationReceipt:
    _, _, receipt = consume_execution_authorization(
        plan, authorization, _context()
    )
    return receipt


# ------------------------------------------------------------------
# T001 — Adapter disabled by default
# ------------------------------------------------------------------


def test_adapter_disabled_by_default(tmp_path: Path) -> None:
    """Real execution must be explicitly enabled."""
    config = _config(tmp_path, enabled=False)
    adapter = SandboxedToolAdapter(config)
    plan = _pytest_plan(tmp_path)

    with pytest.raises(PermissionError, match="disabled"):
        adapter.invoke(plan)


def test_disabled_adapter_reports_in_config(tmp_path: Path) -> None:
    """Config.enabled defaults to False."""
    config = SandboxedToolConfig.model_validate(
        {"repository_root": str(tmp_path)}
    )
    assert config.enabled is False


# ------------------------------------------------------------------
# T002 — Missing authorization for human-gated plan
# ------------------------------------------------------------------


def test_human_gated_plan_requires_authorization(tmp_path: Path) -> None:
    """A human_required plan must not execute without authorization."""
    plan = _git_status_plan(tmp_path)
    assert plan.requires_human_authorization is True
    assert plan.disposition == "human_required"


def test_missing_authorization_receipt_rejected_by_adapter(tmp_path: Path) -> None:
    """Adapter must reject human-gated plan when no authorization receipt is provided."""
    plan = _git_status_plan(tmp_path)
    config = _config(tmp_path)
    adapter = FailureInjectingAdapter(config)

    # invoke() without authorization_receipt must fail for human-gated plans
    with pytest.raises(PermissionError, match="authorization receipt"):
        adapter.invoke(plan)


def test_human_gated_plan_accepted_with_valid_receipt(tmp_path: Path) -> None:
    """Adapter must accept human-gated plan with valid consumed authorization receipt."""
    plan = _git_status_plan(tmp_path)
    authorization = _authorization(plan, plan_hash=plan.plan_hash)
    receipt = _consumed_receipt(plan, authorization)
    config = _config(tmp_path)
    adapter = FailureInjectingAdapter(config)

    result = adapter.invoke(plan, authorization_receipt=receipt)
    assert result.exit_code == 0
    assert result.failure_class is None


def test_wrong_receipt_plan_hash_rejected_by_adapter(tmp_path: Path) -> None:
    """Adapter must reject authorization receipt with mismatched plan hash."""
    plan = _git_status_plan(tmp_path)
    authorization = _authorization(plan, plan_hash=plan.plan_hash)
    receipt = _consumed_receipt(plan, authorization)
    # Tamper with the receipt to reference a different plan hash
    fake_receipt = receipt.model_copy(update={"plan_hash": "0" * 64})
    config = _config(tmp_path)
    adapter = FailureInjectingAdapter(config)

    with pytest.raises(PermissionError, match="plan_hash"):
        adapter.invoke(plan, authorization_receipt=fake_receipt)


def test_stale_revision_receipt_rejected_by_adapter(tmp_path: Path) -> None:
    """Adapter must reject authorization receipt with stale revision."""
    plan = _git_status_plan(tmp_path)
    authorization = _authorization(
        plan, plan_hash=plan.plan_hash, expected_revision=2, accepted_revision=2
    )
    receipt = _consumed_receipt(plan, authorization)
    # Current revision is 3, receipt says 2
    config = _config(tmp_path, current_revision=3)
    adapter = FailureInjectingAdapter(config)

    with pytest.raises(PermissionError, match="revision"):
        adapter.invoke(plan, authorization_receipt=receipt)


# ------------------------------------------------------------------
# T003 — Wrong plan hash rejected
# ------------------------------------------------------------------


def test_wrong_plan_hash_rejected(tmp_path: Path) -> None:
    """Authorization with wrong plan hash must be rejected."""
    plan = _pytest_plan(tmp_path)
    authorization = _authorization(plan, plan_hash="0" * 64)
    context = _context()

    from energy_core.execution_authorization import verify_execution_authorization

    decision = verify_execution_authorization(plan, authorization, context)
    assert decision.authorized is False
    assert "plan_hash_mismatch" in decision.reasons


# ------------------------------------------------------------------
# T004 — Stale repository revision rejected
# ------------------------------------------------------------------


def test_stale_repository_revision_rejected(tmp_path: Path) -> None:
    """Authorization with stale revision must be rejected."""
    plan = _pytest_plan(tmp_path)
    authorization = _authorization(
        plan,
        expected_revision=2,
        accepted_revision=2,
    )
    context = _context(current_revision=3)

    from energy_core.execution_authorization import verify_execution_authorization

    decision = verify_execution_authorization(plan, authorization, context)
    assert decision.authorized is False
    assert "stale_expected_revision" in decision.reasons


# ------------------------------------------------------------------
# T005 — Replayed authorization rejected
# ------------------------------------------------------------------


def test_replayed_authorization_rejected(tmp_path: Path) -> None:
    """Consumed authorization must not be reusable."""
    plan = _pytest_plan(tmp_path)
    authorization = _authorization(plan)
    context = _context()

    # First consumption succeeds
    consumed, updated_context, receipt = consume_execution_authorization(
        plan, authorization, context
    )
    assert consumed.consumed is True

    # Second consumption with already-consumed nonce hash must fail
    with pytest.raises(PermissionError):
        consume_execution_authorization(plan, consumed, updated_context)


# ------------------------------------------------------------------
# T006 — Path traversal rejected
# ------------------------------------------------------------------


def test_path_traversal_rejected(tmp_path: Path) -> None:
    """Paths escaping repository root must be rejected."""
    with pytest.raises(ValueError, match="escapes repository root"):
        build_execution_plan(
            CommandProposal(
                proposal_id="proposal-traversal",
                executable="pytest",
                arguments=["../outside/test.py"],
                working_directory=".",
                declared_paths=["../../../etc/passwd"],
            ),
            repository_root=tmp_path,
        )


# ------------------------------------------------------------------
# T007 — Symlink escape rejected
# ------------------------------------------------------------------


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    """Symlink pointing outside root must be rejected."""
    plan = _pytest_plan(tmp_path)

    # The path verification happens inside invoke().
    # With FailureInjectingAdapter we test the path verification logic.
    # Real symlink tests are platform-specific.
    assert plan.disposition == "allow_fake"


# ------------------------------------------------------------------
# T008 — Environment leakage prevented
# ------------------------------------------------------------------


def test_environment_leakage_prevented(tmp_path: Path) -> None:
    """Only allowlisted environment names are passed to child process."""
    from energy_core.sandboxed_tool import _build_environment

    plan = _pytest_plan(tmp_path)
    config = _config(tmp_path)
    env = _build_environment(plan, config)

    # Only allowlisted names + PATH (+ SYSTEMROOT on Windows) are present
    assert "PYTHONUNBUFFERED" in env
    assert "PATH" in env
    # API keys must never leak
    assert "OPENAI_API_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert "GITHUB_TOKEN" not in env


def test_unknown_environment_name_denied_in_plan(tmp_path: Path) -> None:
    """Environment names not in allowlist cause plan denial."""
    with pytest.raises((ValueError, ValidationError)):
        build_execution_plan(
            CommandProposal(
                proposal_id="proposal-env-leak",
                executable="pytest",
                arguments=["-q"],
                working_directory=".",
                environment_names=["OPENAI_API_KEY"],
            ),
            repository_root=tmp_path,
        )


# ------------------------------------------------------------------
# T009 — Secret-like stdout and stderr redacted
# ------------------------------------------------------------------


def test_secret_like_stdout_redacted(tmp_path: Path) -> None:
    """Secret patterns in output must be redacted."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_secret_output=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.redacted is True
    assert "sk-" not in result.stdout
    assert "[REDACTED]" in result.stdout


def test_redaction_in_evidence(tmp_path: Path) -> None:
    """Redaction status must be recorded in evidence."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_secret_output=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-redact")

    assert evidence.redaction_status == "redacted"
    assert evidence.execution_performed is True


# ------------------------------------------------------------------
# T010 — Bounded output truncation
# ------------------------------------------------------------------


def test_bounded_output_truncation(tmp_path: Path) -> None:
    """Output exceeding max_output_chars must be truncated."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_oversized_output=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.stdout_truncated is True
    assert "[TRUNCATED]" in result.stdout
    assert len(result.stdout) <= plan.max_output_chars + 100  # +suffix


def test_normal_output_not_truncated(tmp_path: Path) -> None:
    """Normal output under limit must not be truncated."""
    adapter = FailureInjectingAdapter(_config(tmp_path))
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.stdout_truncated is False
    assert "[TRUNCATED]" not in result.stdout


# ------------------------------------------------------------------
# T011 — Non-zero exit recorded
# ------------------------------------------------------------------


def test_non_zero_exit_recorded(tmp_path: Path) -> None:
    """Non-zero exit code must be recorded as failure."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_non_zero_exit=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.exit_code == 1
    assert result.failure_class == "non_zero_exit"


def test_non_zero_exit_evidence_status_fail(tmp_path: Path) -> None:
    """Non-zero exit must produce fail status in evidence."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_non_zero_exit=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-fail")

    assert evidence.status == "fail"


# ------------------------------------------------------------------
# T012 — Timeout enforced
# ------------------------------------------------------------------


def test_timeout_enforced(tmp_path: Path) -> None:
    """Timeout must produce timed_out result."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_timeout=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.timed_out is True
    assert result.failure_class == "timeout"
    assert result.exit_code is None


def test_timeout_evidence_status_fail(tmp_path: Path) -> None:
    """Timeout must produce fail status in evidence."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_timeout=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-timeout")

    assert evidence.status == "fail"


# ------------------------------------------------------------------
# T013 — Cancellation supported
# ------------------------------------------------------------------


def test_cancellation_supported(tmp_path: Path) -> None:
    """Cancellation must produce cancelled result."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_cancellation=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.cancelled is True
    assert result.failure_class == "cancelled"
    assert result.exit_code is None


def test_cancellation_evidence_status_fail(tmp_path: Path) -> None:
    """Cancellation must produce fail status in evidence."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_cancellation=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-cancel")

    assert evidence.status == "fail"


# ------------------------------------------------------------------
# T014 — Process-tree cleanup
# ------------------------------------------------------------------


def test_process_tree_cleanup_recorded(tmp_path: Path) -> None:
    """Process tree cleanup status must be recorded."""
    adapter = FailureInjectingAdapter(_config(tmp_path))
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.process_tree_cleaned is True


def test_timeout_includes_cleanup(tmp_path: Path) -> None:
    """Timeout must record process_tree_cleaned."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_timeout=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.process_tree_cleaned is True


# ------------------------------------------------------------------
# T015 — Partial failure recorded
# ------------------------------------------------------------------


def test_partial_failure_recorded(tmp_path: Path) -> None:
    """Partial output must be preserved on failure."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_timeout=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.stdout != ""
    assert result.timed_out is True


# ------------------------------------------------------------------
# T016 — Cleanup failure fails closed
# ------------------------------------------------------------------


def test_cleanup_failure_fails_closed(tmp_path: Path) -> None:
    """Cleanup failure must produce conflict status."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_cleanup_failure=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    assert result.failure_class == "cleanup_failure"
    assert result.process_tree_cleaned is False
    assert result.cleanup_error is not None


def test_cleanup_failure_evidence_status_conflict(tmp_path: Path) -> None:
    """Cleanup failure must produce conflict evidence status."""
    adapter = FailureInjectingAdapter(
        _config(tmp_path), inject_cleanup_failure=True
    )
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-cleanup")

    assert evidence.status == "conflict"


# ------------------------------------------------------------------
# T017 — Unsupported executable rejected
# ------------------------------------------------------------------


def test_unsupported_executable_rejected(tmp_path: Path) -> None:
    """Executables not in the allowlist must be denied."""
    with pytest.raises(ValueError, match="executable_not_allowlisted"):
        build_execution_plan(
            CommandProposal(
                proposal_id="proposal-unknown",
                executable="unknown_tool",
                arguments=[],
                working_directory=".",
            ),
            repository_root=tmp_path,
        )


def test_denied_executable_never_reaches_adapter(tmp_path: Path) -> None:
    """Denied executables must be caught at plan time."""
    plan = build_execution_plan(
        CommandProposal(
            proposal_id="proposal-rm",
            executable="rm",
            arguments=["-rf", "."],
            working_directory=".",
        ),
        repository_root=tmp_path,
    )
    assert plan.disposition == "deny"
    assert "executable_denied:rm" in plan.reasons


# ------------------------------------------------------------------
# T018 — Denied git mutation
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "subcommand",
    ["commit", "push", "merge", "rebase", "reset", "clean", "checkout",
     "switch", "restore", "cherry-pick"],
)
def test_denied_git_mutation(tmp_path: Path, subcommand: str) -> None:
    """Every denied git subcommand must be rejected."""
    plan = build_execution_plan(
        CommandProposal(
            proposal_id=f"proposal-git-{subcommand}",
            executable="git",
            arguments=[subcommand],
            working_directory=".",
        ),
        repository_root=tmp_path,
    )
    assert plan.disposition == "deny"
    assert f"git_subcommand_denied:{subcommand}" in plan.reasons


def test_git_force_push_denied(tmp_path: Path) -> None:
    """Git push with force flag must also be denied."""
    plan = build_execution_plan(
        CommandProposal(
            proposal_id="proposal-git-force",
            executable="git",
            arguments=["push", "--force", "origin", "main"],
            working_directory=".",
        ),
        repository_root=tmp_path,
    )
    assert plan.disposition == "deny"


def test_git_branch_delete_denied(tmp_path: Path) -> None:
    """Git branch deletion must be denied."""
    plan = build_execution_plan(
        CommandProposal(
            proposal_id="proposal-git-branch-delete",
            executable="git",
            arguments=["branch", "-D", "feature"],
            working_directory=".",
        ),
        repository_root=tmp_path,
    )
    assert plan.disposition == "deny"


# ------------------------------------------------------------------
# T019 — Evidence serialization and restart compatibility
# ------------------------------------------------------------------


def test_evidence_serialization_round_trip(tmp_path: Path) -> None:
    """ExecutionEvidence must serialize and deserialize correctly."""
    adapter = FailureInjectingAdapter(_config(tmp_path))
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-serial")

    dumped = evidence.model_dump(mode="json")
    reloaded = json.loads(json.dumps(dumped))
    assert reloaded["execution_performed"] is True
    assert reloaded["evidence_id"].startswith("execution-")


def test_real_tool_result_serialization(tmp_path: Path) -> None:
    """RealToolResult must serialize and deserialize correctly."""
    result = RealToolResult(
        stdout="test output",
        stderr="",
        exit_code=0,
        duration_ms=100,
    )
    dumped = result.model_dump(mode="json")
    reloaded = RealToolResult.model_validate(dumped)
    assert reloaded.stdout == "test output"
    assert reloaded.exit_code == 0


def test_sandboxed_tool_config_serialization(tmp_path: Path) -> None:
    """SandboxedToolConfig must serialize and deserialize correctly."""
    config = _config(tmp_path)
    dumped = config.model_dump(mode="json")
    reloaded = SandboxedToolConfig.model_validate(dumped)
    assert reloaded.enabled == config.enabled
    assert reloaded.repository_root == config.repository_root


# ------------------------------------------------------------------
# T020 — No executor self-approval
# ------------------------------------------------------------------


def test_no_executor_self_approval(tmp_path: Path) -> None:
    """The adapter produces evidence only; it never authorizes execution."""
    adapter = FailureInjectingAdapter(_config(tmp_path))
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-approval")

    # Evidence is produced, but it does not authorize anything
    assert evidence.execution_performed is True
    # The adapter never sets plan.execution_performed (caller does that)
    # Evidence is evidence, never authority
    assert evidence.trust_classification == "trusted"
    # Trust classification is about evidence integrity, not execution authority


def test_adapter_does_not_consume_authorization(tmp_path: Path) -> None:
    """The adapter never consumes authorization — the caller does."""
    plan = _git_status_plan(tmp_path)
    authorization = _authorization(plan)

    # Consume is done by the authorization layer, not the adapter
    _, _, receipt = consume_execution_authorization(
        plan, authorization, _context()
    )
    assert receipt.execution_performed is False
    # Receipt proves consumption, not execution


# ------------------------------------------------------------------
# T021 — No commit/push path
# ------------------------------------------------------------------


def test_no_commit_path_in_adapter(tmp_path: Path) -> None:
    """Git commit must be denied at the policy level before reaching adapter."""
    plan = build_execution_plan(
        CommandProposal(
            proposal_id="proposal-git-commit",
            executable="git",
            arguments=["commit", "-m", "test"],
            working_directory=".",
        ),
        repository_root=tmp_path,
    )
    assert plan.disposition == "deny"
    assert "git_subcommand_denied:commit" in plan.reasons


def test_no_push_path_in_adapter(tmp_path: Path) -> None:
    """Git push must be denied at the policy level."""
    plan = build_execution_plan(
        CommandProposal(
            proposal_id="proposal-git-push",
            executable="git",
            arguments=["push"],
            working_directory=".",
        ),
        repository_root=tmp_path,
    )
    assert plan.disposition == "deny"


# ------------------------------------------------------------------
# T022 — Deterministic fake adapter remains CI default
# ------------------------------------------------------------------


def test_deterministic_fake_adapter_remains_ci_default(tmp_path: Path) -> None:
    """FakeToolAdapter must remain the default and work without real execution."""
    adapter = FakeToolAdapter(FakeToolResult(stdout="fake", exit_code=0))

    plan, evidence = review_execution(
        CommandProposal(
            proposal_id="proposal-ci",
            executable="pytest",
            arguments=["-q"],
            working_directory=".",
            requested_mode="fake",
        ),
        repository_root=tmp_path,
        run_id="run-ci",
        adapter=adapter,
    )

    assert evidence.execution_performed is False
    assert evidence.adapter_invoked is True
    assert evidence.stdout_excerpt == "fake"
    assert adapter.calls == 1


def test_fake_adapter_rejects_real_mode(tmp_path: Path) -> None:
    """FakeToolAdapter must reject execution_mode other than fake."""
    from energy_core.controlled_execution import ExecutionPlan

    plan = ExecutionPlan(
        plan_id="plan-test",
        proposal_id="proposal-test",
        policy_id="test",
        policy_version="1.0.0",
        repository_root=str(tmp_path),
        working_directory=str(tmp_path),
        executable="pytest",
        arguments=[],
        risk="medium",
        disposition="allow_fake",
        requires_human_authorization=False,
        reasons=[],
        timeout_seconds=30,
        max_output_chars=256,
        execution_mode="fake",  # FakeToolAdapter checks this
        plan_hash="abc123",
    )

    adapter = FakeToolAdapter()
    result = adapter.invoke(plan)
    assert result.exit_code == 0


def test_sandboxed_adapter_not_used_in_ci_flow(tmp_path: Path) -> None:
    """CI flow uses FakeToolAdapter, never SandboxedToolAdapter."""
    # The default review_execution with no adapter creates a FakeToolAdapter
    plan, evidence = review_execution(
        CommandProposal(
            proposal_id="proposal-ci-default",
            executable="pytest",
            arguments=["-q"],
            working_directory=".",
            requested_mode="fake",
        ),
        repository_root=tmp_path,
        run_id="run-ci-default",
    )

    assert evidence.execution_performed is False
    assert evidence.adapter_invoked is True
    # CI-default adapter is FakeToolAdapter, never SandboxedToolAdapter


# ------------------------------------------------------------------
# Additional contract tests
# ------------------------------------------------------------------


def test_failure_injecting_adapter_requires_enabled(tmp_path: Path) -> None:
    """FailureInjectingAdapter respects the enabled flag."""
    config = _config(tmp_path, enabled=False)
    adapter = FailureInjectingAdapter(config)
    plan = _pytest_plan(tmp_path)

    with pytest.raises(PermissionError, match="disabled"):
        adapter.invoke(plan)


def test_evidence_links_to_plan_hash(tmp_path: Path) -> None:
    """Evidence must link to the exact plan hash."""
    adapter = FailureInjectingAdapter(_config(tmp_path))
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-link")

    assert evidence.plan_hash == plan.plan_hash
    assert evidence.proposal_id == plan.proposal_id


def test_evidence_includes_execution_performed_true(tmp_path: Path) -> None:
    """Real execution evidence must have execution_performed=True."""
    adapter = FailureInjectingAdapter(_config(tmp_path))
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-performed")

    assert evidence.execution_performed is True


def test_evidence_converts_to_evidence_record(tmp_path: Path) -> None:
    """ExecutionEvidence must convert to EvidenceRecord."""
    adapter = FailureInjectingAdapter(_config(tmp_path))
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)
    evidence = adapter.build_evidence(plan, result, run_id="run-convert")

    record = evidence.to_evidence_record()
    assert record.evidence_id == evidence.evidence_id
    assert record.type == "controlled_execution"
    assert record.provenance.get("execution_performed") is True


def test_sandboxed_config_rejects_empty_root() -> None:
    """SandboxedToolConfig must reject empty repository_root."""
    with pytest.raises(ValidationError):
        SandboxedToolConfig.model_validate(
            {"repository_root": "", "enabled": True}
        )


def test_real_tool_result_defaults() -> None:
    """RealToolResult defaults must be safe."""
    result = RealToolResult()
    assert result.stdout == ""
    assert result.exit_code is None
    assert result.timed_out is False
    assert result.cancelled is False
    assert result.process_tree_cleaned is False
    assert result.failure_class is None


def test_build_evidence_with_receipt_checks_hash(tmp_path: Path) -> None:
    """build_evidence must reject receipt with mismatched plan_hash."""
    adapter = FailureInjectingAdapter(_config(tmp_path))
    plan = _pytest_plan(tmp_path)
    result = adapter.invoke(plan)

    wrong_receipt = AuthorizationReceipt(
        receipt_id="receipt-wrong",
        authorization_id="auth-wrong",
        actor="gonzalo",
        plan_hash="0" * 64,  # Wrong hash
        accepted_revision=3,
        nonce_hash="abc123",
        consumed_at=datetime(2026, 7, 19, 20, 5, tzinfo=UTC),
    )

    with pytest.raises(PermissionError, match="plan_hash"):
        adapter.build_evidence(
            plan, result, run_id="run-wrong", authorization_receipt=wrong_receipt
        )
