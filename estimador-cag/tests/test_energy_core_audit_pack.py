import json
import subprocess
import sys
from pathlib import Path

from energy_core.audit import build_audit_pack, format_audit_pack_markdown

SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")


def _run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "energy_core.cli", *args],
        check=check,
        text=True,
        capture_output=True,
    )


def test_audit_pack_combines_readiness_inputs_without_mutating_ledger(tmp_path):
    decisions_path = tmp_path / "decisions.jsonl"

    pack = build_audit_pack(
        spec_dir=SPEC_DIR,
        policy_path=SPEC_DIR / "energy-policy.yaml",
        candidate_path=SPEC_DIR / "examples/candidate_accept.json",
        evidence_path=SPEC_DIR / "evidence.jsonl",
        decisions_path=decisions_path,
    )
    markdown = format_audit_pack_markdown(pack)

    assert pack["ready_to_accept"] is True
    assert pack["spec_coverage"]["complete"] is True
    assert pack["policy_validation"]["complete"] is True
    assert pack["candidate_validation"]["complete"] is True
    assert pack["evidence_summary"]["total"] == 5
    assert pack["decision"]["decision"] == "accept"
    assert pack["ledger_summary"]["total"] == 0
    assert not decisions_path.exists()
    assert "# Energy Aware Code Audit Pack" in markdown
    assert "Decision preview: accept" in markdown


def test_cli_audit_pack_outputs_json_and_markdown_report(tmp_path):
    decisions_path = tmp_path / "decisions.jsonl"
    report_path = tmp_path / "audit-pack.md"

    _run_cli(
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

    json_result = _run_cli(
        "audit-pack",
        "--spec-dir",
        str(SPEC_DIR),
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
        "--fail-on-not-ready",
    )
    markdown_result = _run_cli(
        "audit-pack",
        "--spec-dir",
        str(SPEC_DIR),
        "--policy",
        str(SPEC_DIR / "energy-policy.yaml"),
        "--candidate",
        str(SPEC_DIR / "examples/candidate_accept.json"),
        "--evidence",
        str(SPEC_DIR / "evidence.jsonl"),
        "--decisions",
        str(decisions_path),
        "--format",
        "markdown",
        "--report",
        str(report_path),
    )

    payload = json.loads(json_result.stdout)
    report = report_path.read_text(encoding="utf-8")

    assert payload["ready_to_accept"] is True
    assert payload["decision"]["decision"] == "accept"
    assert payload["ledger_summary"]["total"] == 1
    assert "# Energy Aware Code Audit Pack" in markdown_result.stdout
    assert "Decision preview: accept" in markdown_result.stdout
    assert "# Energy Aware Code Audit Pack" in report
