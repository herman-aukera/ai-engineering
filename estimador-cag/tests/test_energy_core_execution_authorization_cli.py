from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from energy_core.controlled_execution import CommandProposal, build_execution_plan
from energy_core.execution_authorization import scope_for_plan
from energy_core.execution_authorization_cli import main


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    plan = build_execution_plan(
        CommandProposal(
            proposal_id="proposal-cli-auth",
            executable="git",
            arguments=["status", "--short"],
            working_directory=".",
            declared_paths=[],
            requested_mode="fake",
            timeout_seconds=30,
            max_output_chars=512,
            environment_names=[],
            rollback_summary="Read-only operation.",
        ),
        repository_root=tmp_path,
    )
    now = datetime(2026, 7, 17, 20, 0, tzinfo=UTC)
    authorization = {
        "authorization_id": "auth-cli",
        "actor": "gonzalo",
        "plan_hash": plan.plan_hash,
        "expected_revision": 1,
        "accepted_revision": 1,
        "scope": scope_for_plan(plan).model_dump(mode="json"),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "nonce": "nonce-cli-123456",
        "reason": "Reviewed exact plan.",
        "rollback_acknowledged": True,
        "consumed": False,
    }
    context = {
        "current_revision": 1,
        "trusted_actors": ["gonzalo"],
        "consumed_nonce_hashes": [],
        "now": (now + timedelta(minutes=1)).isoformat(),
    }
    plan_path = tmp_path / "plan.json"
    authorization_path = tmp_path / "authorization.json"
    context_path = tmp_path / "context.json"
    plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    context_path.write_text(json.dumps(context), encoding="utf-8")
    return plan_path, authorization_path, context_path


def test_cli_verifies_without_consuming(tmp_path: Path, capsys) -> None:
    plan, authorization, context = _write_inputs(tmp_path)

    result = main(
        [
            "verify",
            "--plan",
            str(plan),
            "--authorization",
            str(authorization),
            "--context",
            str(context),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["decision"]["authorized"] is True
    assert payload["authorization_consumed"] is False
    assert payload["execution_performed"] is False


def test_cli_consumes_and_writes_replay_safe_outputs(tmp_path: Path, capsys) -> None:
    plan, authorization, context = _write_inputs(tmp_path)
    output_dir = tmp_path / "out"

    result = main(
        [
            "consume",
            "--plan",
            str(plan),
            "--authorization",
            str(authorization),
            "--context",
            str(context),
            "--output-dir",
            str(output_dir),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["receipt"]["execution_performed"] is False
    assert json.loads((output_dir / "authorization.json").read_text())["consumed"] is True
    updated_context = json.loads((output_dir / "context.json").read_text())
    assert len(updated_context["consumed_nonce_hashes"]) == 1
    assert (output_dir / "receipt.json").is_file()


def test_cli_returns_two_for_invalid_authorization(tmp_path: Path, capsys) -> None:
    plan, authorization, context = _write_inputs(tmp_path)
    payload = json.loads(authorization.read_text())
    payload["plan_hash"] = "0" * 64
    authorization.write_text(json.dumps(payload), encoding="utf-8")

    result = main(
        [
            "verify",
            "--plan",
            str(plan),
            "--authorization",
            str(authorization),
            "--context",
            str(context),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert result == 2
    assert output["decision"]["authorized"] is False
    assert "plan_hash_mismatch" in output["decision"]["reasons"]
