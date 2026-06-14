from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT / "estimador-cag"
SPEC_DIR = PROJECT_ROOT / ".energy/specs/0001-energy-policy-ledger"
POLICY = SPEC_DIR / "energy-policy.yaml"
ACCEPT_CANDIDATE = SPEC_DIR / "examples/candidate_accept.json"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def main() -> int:
    help_result = _run("--help")
    _assert("policy-validate" in help_result.stdout, "root help should include policy-validate")
    _assert("candidate-validate" in help_result.stdout, "root help should include candidate-validate")
    _assert("audit-pack" in help_result.stdout, "root help should include audit-pack")

    policy = _run(
        "policy-validate",
        "--policy",
        str(POLICY),
        "--format",
        "json",
        "--fail-on-invalid",
    )
    _assert(json.loads(policy.stdout)["complete"] is True, "root policy validation should pass")

    candidate = _run(
        "candidate-validate",
        "--policy",
        str(POLICY),
        "--candidate",
        str(ACCEPT_CANDIDATE),
        "--format",
        "json",
        "--fail-on-invalid",
    )
    _assert(json.loads(candidate.stdout)["complete"] is True, "root candidate validation should pass")

    decision = _run(
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
    _assert(json.loads(decision.stdout)["decision"] == "accept", "root dry-run evaluation should accept")

    evidence_summary = _run(
        "evidence-summary",
        "--evidence",
        str(EVIDENCE),
        "--format",
        "markdown",
    )
    _assert(
        "# Energy Aware Code Evidence Summary" in evidence_summary.stdout,
        "root evidence summary should print Markdown",
    )

    with tempfile.TemporaryDirectory(prefix="energy-core-root-smoke-") as tmp:
        decisions = Path(tmp) / "decisions.jsonl"
        _run(
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
        audit = _run(
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
        audit_payload = json.loads(audit.stdout)
        _assert(audit_payload["ready_to_accept"] is True, "root audit pack should be ready to accept")
        _assert(audit_payload["decision"]["decision"] == "accept", "root audit pack should preview accept")

    print("Energy Core root smoke passed.")
    return 0


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "energy_core.cli", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
