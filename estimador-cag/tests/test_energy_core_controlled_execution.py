from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from energy_core.controlled_execution import (
    CommandProposal,
    FakeToolAdapter,
    FakeToolResult,
    build_execution_plan,
    review_execution,
)


def _can_symlink() -> bool:
    """Return True if symlink creation is permitted on this platform."""
    if sys.platform != "win32":
        return True
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src"
            src.write_text("test")
            link = Path(td) / "link"
            os.symlink(str(src), str(link))
            return True
    except OSError:
        return False


_can_symlink_skip = pytest.mark.skipif(
    not _can_symlink(), reason="Symlink creation requires admin/Developer Mode on Windows"
)


def _proposal(**overrides):
    payload = {
        "proposal_id": "proposal-1",
        "executable": "pytest",
        "arguments": ["-q", "tests/test_example.py"],
        "working_directory": ".",
        "declared_paths": ["tests/test_example.py"],
        "requested_mode": "dry_run",
        "timeout_seconds": 30,
        "max_output_chars": 256,
        "environment_names": ["PYTHONUNBUFFERED"],
        "rollback_summary": "No repository mutation is performed.",
    }
    payload.update(overrides)
    return CommandProposal.model_validate(payload)


def test_contract_rejects_shell_path_executable() -> None:
    with pytest.raises(ValidationError):
        _proposal(executable="/bin/bash")


def test_dry_run_validates_and_does_not_invoke_adapter(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_ok(): assert True\n")
    adapter = FakeToolAdapter()

    plan, evidence = review_execution(
        _proposal(),
        repository_root=tmp_path,
        run_id="run-1",
        adapter=adapter,
    )

    assert plan.disposition == "allow_fake"
    assert plan.execution_performed is False
    assert evidence.status == "pass"
    assert evidence.adapter_invoked is False
    assert evidence.execution_performed is False
    assert adapter.calls == 0


def test_denied_command_never_reaches_adapter(tmp_path: Path) -> None:
    adapter = FakeToolAdapter()
    plan, evidence = review_execution(
        _proposal(executable="rm", arguments=["-rf", "."], declared_paths=[]),
        repository_root=tmp_path,
        run_id="run-denied",
        adapter=adapter,
    )

    assert plan.disposition == "deny"
    assert plan.risk == "denied"
    assert evidence.status == "fail"
    assert evidence.adapter_invoked is False
    assert adapter.calls == 0


def test_git_mutation_is_denied_not_merely_human_gated(tmp_path: Path) -> None:
    plan = build_execution_plan(
        _proposal(
            executable="git",
            arguments=["push", "origin", "EACODE"],
            declared_paths=[],
        ),
        repository_root=tmp_path,
    )

    assert plan.disposition == "deny"
    assert "git_subcommand_denied:push" in plan.reasons


def test_read_only_git_plan_requires_human_and_never_invokes_adapter(tmp_path: Path) -> None:
    adapter = FakeToolAdapter()
    plan, evidence = review_execution(
        _proposal(
            executable="git",
            arguments=["status", "--short"],
            declared_paths=[],
            requested_mode="fake",
        ),
        repository_root=tmp_path,
        run_id="run-human",
        adapter=adapter,
    )

    assert plan.disposition == "human_required"
    assert plan.requires_human_authorization is True
    assert evidence.status == "missing"
    assert adapter.calls == 0


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside")

    with pytest.raises(ValueError, match="escapes repository root"):
        build_execution_plan(
            _proposal(arguments=[], declared_paths=[str(outside)]),
            repository_root=tmp_path,
        )


@_can_symlink_skip
def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    outside_dir = tmp_path.parent / "outside-dir"
    outside_dir.mkdir(exist_ok=True)
    link = tmp_path / "linked"
    link.symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes repository root"):
        build_execution_plan(
            _proposal(arguments=[], declared_paths=["linked/secret.txt"]),
            repository_root=tmp_path,
        )


def test_non_allowlisted_environment_denies_plan(tmp_path: Path) -> None:
    plan = build_execution_plan(
        _proposal(arguments=[], declared_paths=[], environment_names=["DEEPSEEK_API_KEY"]),
        repository_root=tmp_path,
    )

    assert plan.disposition == "deny"
    assert any(reason.startswith("environment_not_allowlisted:") for reason in plan.reasons)


def test_fake_adapter_redacts_and_truncates_output(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_ok(): assert True\n")
    secret = "sk-" + "A" * 24
    adapter = FakeToolAdapter(
        FakeToolResult(
            stdout=f"token={secret}\n" + ("x" * 500),
            stderr="",
            exit_code=0,
            duration_ms=7,
        )
    )

    plan, evidence = review_execution(
        _proposal(requested_mode="fake", max_output_chars=128),
        repository_root=tmp_path,
        run_id="run-fake",
        adapter=adapter,
    )

    assert plan.disposition == "allow_fake"
    assert evidence.status == "pass"
    assert evidence.adapter_invoked is True
    assert evidence.execution_performed is False
    assert secret not in evidence.stdout_excerpt
    assert "[REDACTED]" in evidence.stdout_excerpt
    assert evidence.output_truncated is True
    assert evidence.redaction_status == "redacted"
    assert evidence.artifact_hash
    assert adapter.calls == 1


def test_plan_hash_is_stable_and_argument_sensitive(tmp_path: Path) -> None:
    first = build_execution_plan(
        _proposal(arguments=["-q"], declared_paths=[]),
        repository_root=tmp_path,
    )
    same = build_execution_plan(
        _proposal(arguments=["-q"], declared_paths=[]),
        repository_root=tmp_path,
    )
    changed = build_execution_plan(
        _proposal(arguments=["-x"], declared_paths=[]),
        repository_root=tmp_path,
    )

    assert first.plan_hash == same.plan_hash
    assert first.plan_hash != changed.plan_hash


def test_execution_evidence_converts_to_existing_evidence_contract(tmp_path: Path) -> None:
    _, evidence = review_execution(
        _proposal(arguments=[], declared_paths=[]),
        repository_root=tmp_path,
        run_id="run-record",
    )

    record = evidence.to_evidence_record()

    assert record.type == "controlled_execution"
    assert record.command_hash == evidence.plan_hash
    assert record.provenance["execution_performed"] is False
