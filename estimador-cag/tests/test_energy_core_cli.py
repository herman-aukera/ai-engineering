import json
import subprocess
import sys
from pathlib import Path

SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")


def _run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "energy_core.cli", *args],
        check=check,
        text=True,
        capture_output=True,
    )


def test_cli_evaluates_candidate_and_appends_decision_ledger(tmp_path):
    decisions_path = tmp_path / "decisions.jsonl"

    result = _run_cli(
        "evaluate",
        "--policy",
        str(SPEC_DIR / "energy-policy.yaml"),
        "--candidate",
        str(SPEC_DIR / "examples/candidate_accept.json"),
        "--evidence",
        str(SPEC_DIR / "evidence.jsonl"),
        "--decisions",
        str(decisions_path),
        "--format",
        "json",
    )

    payload = json.loads(result.stdout)
    ledger_rows = decisions_path.read_text(encoding="utf-8").splitlines()

    assert payload["decision"] == "accept"
    assert payload["candidate_id"] == "slice-001-accept"
    assert len(ledger_rows) == 1
    assert json.loads(ledger_rows[0])["candidate_id"] == "slice-001-accept"


def test_cli_text_output_is_human_readable(tmp_path):
    decisions_path = tmp_path / "decisions.jsonl"

    result = _run_cli(
        "evaluate",
        "--policy",
        str(SPEC_DIR / "energy-policy.yaml"),
        "--candidate",
        str(SPEC_DIR / "examples/candidate_accept.json"),
        "--evidence",
        str(SPEC_DIR / "evidence.jsonl"),
        "--decisions",
        str(decisions_path),
        "--format",
        "text",
    )

    assert "Energy Aware Code Decision" in result.stdout
    assert "Decision: accept" in result.stdout
    assert "Candidate: slice-001-accept" in result.stdout
    assert "Energy: 0" in result.stdout
    assert "Evidence refs:" in result.stdout
    assert "Next action: stop" in result.stdout


def test_cli_writes_markdown_report(tmp_path):
    decisions_path = tmp_path / "decisions.jsonl"
    report_path = tmp_path / "decision-report.md"

    result = _run_cli(
        "evaluate",
        "--policy",
        str(SPEC_DIR / "energy-policy.yaml"),
        "--candidate",
        str(SPEC_DIR / "examples/candidate_accept.json"),
        "--evidence",
        str(SPEC_DIR / "evidence.jsonl"),
        "--decisions",
        str(decisions_path),
        "--format",
        "json",
        "--report",
        str(report_path),
    )

    payload = json.loads(result.stdout)
    report = report_path.read_text(encoding="utf-8")

    assert payload["decision"] == "accept"
    assert "# Energy Aware Code Decision Report" in report
    assert "Decision: accept" in report
    assert "Candidate: slice-001-accept" in report
    assert "Evidence refs" in report


def test_cli_can_fail_automation_on_non_accept_decision(tmp_path):
    decisions_path = tmp_path / "decisions.jsonl"

    result = _run_cli(
        "evaluate",
        "--policy",
        str(SPEC_DIR / "energy-policy.yaml"),
        "--candidate",
        str(SPEC_DIR / "examples/candidate_reject_tests_failed.json"),
        "--evidence",
        str(SPEC_DIR / "evidence.jsonl"),
        "--decisions",
        str(decisions_path),
        "--format",
        "json",
        "--fail-on-non-accept",
        check=False,
    )

    payload = json.loads(result.stdout)
    ledger_rows = decisions_path.read_text(encoding="utf-8").splitlines()

    assert result.returncode == 2
    assert payload["decision"] == "reject"
    assert "tests_failed" in payload["hard_reject_violations"]
    assert len(ledger_rows) == 1
