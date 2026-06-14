from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from energy_core.ledger_integrity import (
    build_ledger_integrity,
    format_ledger_integrity_markdown,
)
from energy_core.models import EnergyDecision


def _decision(candidate_id: str = "candidate-1", energy_delta: int = 0) -> EnergyDecision:
    return EnergyDecision(
        policy_id="energy-code-default",
        candidate_id=candidate_id,
        decision="accept",
        energy_before=0,
        energy_after=0,
        energy_delta=energy_delta,
        hard_reject_violations=[],
        hard_repair_violations=[],
        soft_violations=[],
        missing_evidence=[],
        evidence_refs=["pytest-output"],
        required_repairs=[],
        reasoning_summary="ok",
        next_action="stop",
    )


def test_empty_ledger_is_complete(tmp_path: Path) -> None:
    ledger = tmp_path / "decisions.jsonl"
    ledger.write_text("", encoding="utf-8")

    report = build_ledger_integrity(ledger)

    assert report["exists"] is True
    assert report["complete"] is True
    assert report["valid_record_total"] == 0
    assert report["invalid_record_total"] == 0


def test_valid_ledger_reports_decision_counts(tmp_path: Path) -> None:
    ledger = tmp_path / "decisions.jsonl"
    ledger.write_text(
        "\n".join(
            [
                _decision("candidate-1").model_dump_json(),
                _decision("candidate-2").model_dump_json(),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_ledger_integrity(ledger)
    markdown = format_ledger_integrity_markdown(report)

    assert report["complete"] is True
    assert report["decision_counts"] == {"accept": 2}
    assert "# Energy Aware Code Ledger Integrity" in markdown
    assert "- accept: 2" in markdown


def test_invalid_json_marks_report_incomplete(tmp_path: Path) -> None:
    ledger = tmp_path / "decisions.jsonl"
    ledger.write_text('{"candidate_id": "broken"\n', encoding="utf-8")

    report = build_ledger_integrity(ledger)

    assert report["complete"] is False
    assert report["invalid_record_total"] == 1
    assert "invalid JSON" in report["invalid_records"][0]["error"]


def test_energy_delta_mismatch_marks_report_incomplete(tmp_path: Path) -> None:
    ledger = tmp_path / "decisions.jsonl"
    ledger.write_text(_decision(energy_delta=99).model_dump_json() + "\n", encoding="utf-8")

    report = build_ledger_integrity(ledger)

    assert report["complete"] is False
    assert report["energy_delta_mismatches"] == [
        {
            "line": 1,
            "candidate_id": "candidate-1",
            "expected_delta": 0,
            "actual_delta": 99,
        }
    ]


def test_cli_outputs_json_for_committed_ledger() -> None:
    project_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.ledger_integrity_cli",
            "--format",
            "json",
            "--fail-on-invalid",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["complete"] is True
    assert payload["exists"] is True


def test_cli_runs_from_repository_root() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    completed = subprocess.run(
        [
            repo_root / "estimador-cag" / ".venv" / "bin" / "python",
            "-m",
            "energy_core.ledger_integrity_cli",
            "--ledger",
            ".energy/specs/0001-energy-policy-ledger/decisions.jsonl",
            "--format",
            "text",
            "--fail-on-invalid",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "Energy Aware Code Ledger Integrity" in completed.stdout
    assert "Complete: True" in completed.stdout
