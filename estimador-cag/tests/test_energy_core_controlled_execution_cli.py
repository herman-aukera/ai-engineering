from __future__ import annotations

import json
from pathlib import Path

from energy_core.controlled_execution_cli import main


def _write_proposal(path: Path, *, executable: str = "pytest") -> None:
    path.write_text(
        json.dumps(
            {
                "proposal_id": "proposal-cli",
                "executable": executable,
                "arguments": [],
                "working_directory": ".",
                "declared_paths": [],
                "requested_mode": "dry_run",
                "timeout_seconds": 10,
                "max_output_chars": 256,
                "environment_names": [],
            }
        ),
        encoding="utf-8",
    )


def test_cli_emits_json_without_real_execution(tmp_path: Path, capsys) -> None:
    proposal = tmp_path / "proposal.json"
    _write_proposal(proposal)

    result = main(
        [
            "--proposal",
            str(proposal),
            "--repository-root",
            str(tmp_path),
            "--run-id",
            "run-cli",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 0
    assert payload["plan"]["disposition"] == "allow_fake"
    assert payload["evidence"]["execution_performed"] is False
    assert payload["real_execution_supported"] is False


def test_cli_fail_on_deny_returns_two(tmp_path: Path, capsys) -> None:
    proposal = tmp_path / "proposal.json"
    _write_proposal(proposal, executable="rm")

    result = main(
        [
            "--proposal",
            str(proposal),
            "--repository-root",
            str(tmp_path),
            "--run-id",
            "run-cli-denied",
            "--fail-on-deny",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert result == 2
    assert payload["plan"]["disposition"] == "deny"
    assert payload["evidence"]["adapter_invoked"] is False
