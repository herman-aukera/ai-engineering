"""Fail-closed CLI tests for secure Spec 0009 live execution."""

from __future__ import annotations  # noqa: I001

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from energy_core.controlled_execution import CommandProposal, ExecutionPlan, build_execution_plan
from energy_core.live_authorization import (
    LiveAuthorizationContext,
    LiveAuthorizationRequest,
    SQLiteLiveAuthorizationStore,
    issue_live_authorization,
    scope_for_live_execution,
)
from energy_core.live_execution_contract import RepositorySnapshot, authorize_live_execution
from energy_core.sandboxed_tool import SandboxedToolAdapter, SandboxedToolConfig
from energy_core.sandboxed_tool_cli import main
from energy_core.secure_execution_service import SecureExecutionService
from energy_core.secure_process_adapter import SecureProcessResult


class StubAdapter:
    def invoke(self, plan: object, receipt: object, intent: object) -> SecureProcessResult:
        del plan, receipt, intent
        return SecureProcessResult(
            stdout="ok\n",
            exit_code=0,
            duration_ms=10,
            process_started=True,
            cleanup_verified=True,
        )


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )


def _fixture(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "EACODE Tests")
    (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-m", "initial")

    plan = build_execution_plan(
        CommandProposal(
            proposal_id="proposal-secure-cli",
            executable="pytest",
            arguments=["-q"],
            working_directory=".",
            requested_mode="fake",
            timeout_seconds=30,
            max_output_chars=1024,
            rollback_summary="Read-only test execution.",
        ),
        repository_root=root,
    )
    snapshot = RepositorySnapshot.capture(root)
    now = datetime.now(UTC)
    database = tmp_path / "authority.db"
    store = SQLiteLiveAuthorizationStore(database)
    receipt = issue_live_authorization(
        plan,
        snapshot,
        LiveAuthorizationRequest(
            authorization_id="live-auth-cli",
            actor="gonzalo",
            plan_hash=plan.plan_hash,
            repository_snapshot_hash=snapshot.snapshot_hash,
            scope=scope_for_live_execution(plan),
            created_at=now - timedelta(seconds=1),
            expires_at=now + timedelta(minutes=5),
            nonce="secure-cli-nonce-123456",
            reason="Authorize one bounded CLI process attempt.",
            rollback_acknowledged=True,
        ),
        LiveAuthorizationContext(
            current_revision=1,
            trusted_actors=["gonzalo"],
            now=now,
        ),
        store,
    )
    live_plan, intent = authorize_live_execution(plan, receipt, snapshot, now=now)
    plan_path = tmp_path / "live-plan.json"
    intent_path = tmp_path / "live-intent.json"
    base_plan_path = tmp_path / "base-plan.json"
    plan_path.write_text(
        json.dumps(live_plan.model_dump(mode="json")),
        encoding="utf-8",
    )
    intent_path.write_text(
        json.dumps(intent.model_dump(mode="json")),
        encoding="utf-8",
    )
    base_plan_path.write_text(
        json.dumps(plan.model_dump(mode="json")),
        encoding="utf-8",
    )
    return {
        "root": root,
        "plan": plan,
        "live_plan": live_plan,
        "intent": intent,
        "receipt": receipt,
        "database": database,
        "plan_path": plan_path,
        "intent_path": intent_path,
        "base_plan_path": base_plan_path,
    }


def _argv(data: dict[str, Any], *, live: bool) -> list[str]:
    values = [
        "--plan",
        str(data["plan_path"]),
        "--intent",
        str(data["intent_path"]),
        "--authorization-db",
        str(data["database"]),
        "--receipt-id",
        data["receipt"].receipt_id,
        "--repository-root",
        str(data["root"]),
        "--run-id",
        "run-secure-cli",
        "--current-revision",
        "1",
        "--trusted-actor",
        "gonzalo",
        "--format",
        "json",
    ]
    if live:
        values.append("--live-tool")
    return values


def test_cli_without_live_flag_refuses_before_reservation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = _fixture(tmp_path)
    called = False

    def executor(**_kwargs: Any) -> object:
        nonlocal called
        called = True
        raise AssertionError("executor must not be called")

    exit_code = main(_argv(data, live=False), executor=executor)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["status"] == "refused"
    assert payload["real_execution_performed"] is False
    assert called is False
    assert SQLiteLiveAuthorizationStore(data["database"]).is_execution_reserved(
        data["receipt"].receipt_id
    ) is False


def test_cli_rejects_base_plan_even_with_live_flag(tmp_path: Path) -> None:
    data = _fixture(tmp_path)
    data["plan_path"] = data["base_plan_path"]

    with pytest.raises(ValidationError):
        main(_argv(data, live=True), executor=lambda **_kwargs: None)


def test_cli_requires_authoritative_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = _fixture(tmp_path)
    args = _argv(data, live=True)
    receipt_index = args.index("--receipt-id") + 1
    args[receipt_index] = "missing-receipt"

    exit_code = main(args, executor=lambda **_kwargs: None)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["status"] == "refused"
    assert payload["error_type"] == "PermissionError"


def test_cli_secure_path_returns_normalized_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data = _fixture(tmp_path)

    def executor(*, plan: object, intent: object, receipt: object, store: object, **_: Any):
        service = SecureExecutionService(adapter=StubAdapter(), receipt_store=store)
        return service.execute(plan, intent, receipt, run_id="run-secure-cli")

    exit_code = main(_argv(data, live=True), executor=executor)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "pass"
    assert payload["real_execution_performed"] is True
    assert payload["evidence"]["authority_completion_verified"] is True
    assert payload["evidence"]["authorization_receipt_id"] == data["receipt"].receipt_id


def test_legacy_real_adapter_is_permanently_disabled(tmp_path: Path) -> None:
    data = _fixture(tmp_path)
    adapter = SandboxedToolAdapter(
        SandboxedToolConfig(
            enabled=True,
            repository_root=str(data["root"]),
            current_revision=1,
            trusted_actors=["gonzalo"],
        )
    )

    with pytest.raises(PermissionError, match="legacy real-process adapter is disabled"):
        adapter.invoke(data["live_plan"], authorization_receipt=data["receipt"])
