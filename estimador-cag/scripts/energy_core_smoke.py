from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / ".energy/specs/0001-energy-policy-ledger"
POLICY = SPEC_DIR / "energy-policy.yaml"
ACCEPT_CANDIDATE = SPEC_DIR / "examples/candidate_accept.json"
REJECT_CANDIDATE = SPEC_DIR / "examples/candidate_reject_tests_failed.json"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="energy-core-smoke-") as tmp:
        tmp_path = Path(tmp)
        decisions = tmp_path / "decisions.jsonl"
        report = tmp_path / "decision-report.md"
        policy_report = tmp_path / "policy-report.md"
        candidate_report = tmp_path / "candidate-report.md"
        evidence_report = tmp_path / "evidence-report.md"
        ledger_report = tmp_path / "ledger-report.md"
        trends_report = tmp_path / "decision-trends.md"
        spec_report = tmp_path / "spec-report.md"
        bundle_report = tmp_path / "bundle-manifest.md"
        audit_report = tmp_path / "audit-pack.md"
        failed_evidence = tmp_path / "failed-evidence.jsonl"

        policy_validation = _run(
            "policy-validate",
            "--policy",
            str(POLICY),
            "--format",
            "json",
            "--fail-on-invalid",
        )
        policy_payload = json.loads(policy_validation.stdout)
        _assert(policy_payload["complete"] is True, "policy validation should pass")
        policy_markdown = _run(
            "policy-validate",
            "--policy",
            str(POLICY),
            "--format",
            "markdown",
            "--report",
            str(policy_report),
        )
        _assert(
            "# Energy Aware Code Policy Validation" in policy_markdown.stdout,
            "policy validation Markdown should print",
        )
        _assert(
            "# Energy Aware Code Policy Validation" in policy_report.read_text(encoding="utf-8"),
            "policy validation Markdown report should be written",
        )

        candidate_validation = _run(
            "candidate-validate",
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--format",
            "json",
            "--fail-on-invalid",
        )
        candidate_payload = json.loads(candidate_validation.stdout)
        _assert(candidate_payload["complete"] is True, "candidate validation should pass")
        candidate_markdown = _run(
            "candidate-validate",
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--format",
            "markdown",
            "--report",
            str(candidate_report),
        )
        _assert(
            "# Energy Aware Code Candidate Validation" in candidate_markdown.stdout,
            "candidate validation Markdown should print",
        )
        _assert(
            "# Energy Aware Code Candidate Validation" in candidate_report.read_text(encoding="utf-8"),
            "candidate validation Markdown report should be written",
        )

        accept_json = _run(
            "evaluate",
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--evidence",
            str(EVIDENCE),
            "--decisions",
            str(decisions),
            "--format",
            "json",
        )
        accept_payload = json.loads(accept_json.stdout)
        _assert(accept_payload["decision"] == "accept", "accept JSON decision should be accept")

        accept_text = _run(
            "evaluate",
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--evidence",
            str(EVIDENCE),
            "--decisions",
            str(decisions),
            "--format",
            "text",
            "--report",
            str(report),
        )
        _assert("Decision: accept" in accept_text.stdout, "text output should include accept decision")
        _assert("# Energy Aware Code Decision Report" in report.read_text(encoding="utf-8"), "report should be Markdown")

        dry_run_decisions = tmp_path / "dry-run-decisions.jsonl"
        dry_run = _run(
            "evaluate",
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--evidence",
            str(EVIDENCE),
            "--format",
            "json",
            "--dry-run",
        )
        _assert(json.loads(dry_run.stdout)["decision"] == "accept", "dry run should evaluate")
        _assert(not dry_run_decisions.exists(), "dry run should not create a decision ledger")

        spec_coverage = _run(
            "spec-coverage",
            "--spec-dir",
            str(SPEC_DIR),
            "--format",
            "json",
        )
        spec_payload = json.loads(spec_coverage.stdout)
        _assert(spec_payload["complete"] is True, "spec coverage should be complete")
        _assert(spec_payload["missing"] == [], "spec coverage should not report missing artifacts")

        spec_markdown = _run(
            "spec-coverage",
            "--spec-dir",
            str(SPEC_DIR),
            "--format",
            "markdown",
            "--report",
            str(spec_report),
        )
        _assert(
            "# Energy Aware Code Spec Coverage" in spec_markdown.stdout,
            "Markdown spec coverage should print",
        )
        _assert(
            "# Energy Aware Code Spec Coverage" in spec_report.read_text(encoding="utf-8"),
            "Markdown spec coverage report should be written",
        )

        summary_json = _run(
            "evidence-summary",
            "--evidence",
            str(EVIDENCE),
            "--format",
            "json",
        )
        summary = json.loads(summary_json.stdout)
        _assert(summary["total"] == 5, "evidence summary should count records")
        _assert(summary["by_status"] == {"pass": 5}, "evidence summary should group statuses")

        summary_markdown = _run(
            "evidence-summary",
            "--evidence",
            str(EVIDENCE),
            "--format",
            "markdown",
            "--report",
            str(evidence_report),
        )
        _assert(
            "# Energy Aware Code Evidence Summary" in summary_markdown.stdout,
            "Markdown summary should print",
        )
        _assert(
            "# Energy Aware Code Evidence Summary" in evidence_report.read_text(encoding="utf-8"),
            "Markdown summary report should be written",
        )

        failed_evidence.write_text(
            json.dumps(
                {
                    "evidence_id": "pytest-failed",
                    "type": "pytest_output",
                    "status": "fail",
                    "summary": "pytest failed intentionally for smoke validation",
                    "trusted": True,
                    "exit_code": 1,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        reject = _run(
            "evaluate",
            "--policy",
            str(POLICY),
            "--candidate",
            str(REJECT_CANDIDATE),
            "--evidence",
            str(failed_evidence),
            "--decisions",
            str(decisions),
            "--format",
            "text",
            "--fail-on-non-accept",
            check=False,
        )
        _assert(reject.returncode == 2, f"reject exit code should be 2, got {reject.returncode}")
        _assert("Decision: reject" in reject.stdout, "reject output should include decision")
        _assert("tests_failed" in reject.stdout, "reject output should include tests_failed")

        ledger_json = _run(
            "ledger-summary",
            "--decisions",
            str(decisions),
            "--format",
            "json",
        )
        ledger_summary = json.loads(ledger_json.stdout)
        _assert(ledger_summary["total"] == 3, "ledger summary should count appended decisions")
        _assert(ledger_summary["by_decision"] == {"accept": 2, "reject": 1}, "ledger summary should group decisions")

        ledger_markdown = _run(
            "ledger-summary",
            "--decisions",
            str(decisions),
            "--format",
            "markdown",
            "--report",
            str(ledger_report),
        )
        _assert(
            "# Energy Aware Code Decision Ledger Summary" in ledger_markdown.stdout,
            "Markdown ledger summary should print",
        )
        _assert("slice-001-accept" in ledger_markdown.stdout, "ledger summary should include candidate ids")
        _assert(
            "# Energy Aware Code Decision Ledger Summary" in ledger_report.read_text(encoding="utf-8"),
            "Markdown ledger summary report should be written",
        )

        trends_json = _run(
            "decision-trends",
            "--decisions",
            str(decisions),
            "--format",
            "json",
        )
        trends = json.loads(trends_json.stdout)
        _assert(trends["total"] == 3, "decision trends should count ledger rows")
        _assert(trends["non_accept"] == 1, "decision trends should count non-accept decisions")
        _assert(trends["trend"] == "needs_attention", "reject decision should make trend need attention")

        trends_markdown = _run(
            "decision-trends",
            "--decisions",
            str(decisions),
            "--format",
            "markdown",
            "--report",
            str(trends_report),
        )
        _assert(
            "# Energy Aware Code Decision Trends" in trends_markdown.stdout,
            "Markdown decision trends should print",
        )
        _assert(
            "# Energy Aware Code Decision Trends" in trends_report.read_text(encoding="utf-8"),
            "Markdown decision trends report should be written",
        )

        bundle_json = _run(
            "bundle-manifest",
            "--spec-dir",
            str(SPEC_DIR),
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--evidence",
            str(EVIDENCE),
            "--decisions",
            str(decisions),
            "--format",
            "json",
            "--fail-on-incomplete",
        )
        bundle = json.loads(bundle_json.stdout)
        _assert(bundle["complete"] is True, "bundle manifest should be complete")
        _assert(bundle["missing_required"] == [], "bundle manifest should not miss required files")

        bundle_markdown = _run(
            "bundle-manifest",
            "--spec-dir",
            str(SPEC_DIR),
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--evidence",
            str(EVIDENCE),
            "--decisions",
            str(decisions),
            "--format",
            "markdown",
            "--report",
            str(bundle_report),
        )
        _assert(
            "# Energy Aware Code Bundle Manifest" in bundle_markdown.stdout,
            "Markdown bundle manifest should print",
        )
        _assert(
            "# Energy Aware Code Bundle Manifest" in bundle_report.read_text(encoding="utf-8"),
            "Markdown bundle manifest report should be written",
        )

        audit_json = _run(
            "audit-pack",
            "--spec-dir",
            str(SPEC_DIR),
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--evidence",
            str(EVIDENCE),
            "--decisions",
            str(decisions),
            "--format",
            "json",
            "--fail-on-not-ready",
        )
        audit_payload = json.loads(audit_json.stdout)
        _assert(audit_payload["ready_to_accept"] is True, "audit pack should be ready to accept")
        _assert(audit_payload["decision"]["decision"] == "accept", "audit pack decision should accept")
        _assert(audit_payload["ledger_summary"]["total"] == 3, "audit pack should include ledger summary")

        audit_markdown = _run(
            "audit-pack",
            "--spec-dir",
            str(SPEC_DIR),
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--evidence",
            str(EVIDENCE),
            "--decisions",
            str(decisions),
            "--format",
            "markdown",
            "--report",
            str(audit_report),
        )
        _assert("# Energy Aware Code Audit Pack" in audit_markdown.stdout, "audit pack Markdown should print")
        _assert("Decision preview: accept" in audit_markdown.stdout, "audit pack should include decision preview")
        _assert(
            "# Energy Aware Code Audit Pack" in audit_report.read_text(encoding="utf-8"),
            "audit pack Markdown report should be written",
        )

    print("Energy Core smoke passed.")
    return 0


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "energy_core.cli", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
