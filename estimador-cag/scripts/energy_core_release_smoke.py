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
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="energy-core-release-smoke-") as tmp:
        tmp_path = Path(tmp)
        decisions = tmp_path / "decisions.jsonl"
        report = tmp_path / "release-readiness.md"
        missing_decisions = tmp_path / "missing-decisions.jsonl"

        _run(
            "energy_core.cli",
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

        release_json = _run(
            "energy_core.release_cli",
            "--project-root",
            str(ROOT),
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
        release_payload = json.loads(release_json.stdout)
        _assert(release_payload["ready_to_extract"] is True, "release readiness should pass")
        _assert(release_payload["boundary"]["clean"] is True, "package boundary should be clean")
        _assert(release_payload["release_artifacts"]["complete"] is True, "release artifacts should be present")

        release_markdown = _run(
            "energy_core.release_cli",
            "--project-root",
            str(ROOT),
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
            str(report),
        )
        _assert("# Energy Aware Code Release Readiness" in release_markdown.stdout, "Markdown should print")
        _assert("Ready to extract: True" in release_markdown.stdout, "Markdown should show readiness")
        _assert("# Energy Aware Code Release Readiness" in report.read_text(encoding="utf-8"), "report should be written")

        blocked = _run(
            "energy_core.release_cli",
            "--project-root",
            str(ROOT),
            "--spec-dir",
            str(SPEC_DIR),
            "--policy",
            str(POLICY),
            "--candidate",
            str(ACCEPT_CANDIDATE),
            "--evidence",
            str(EVIDENCE),
            "--decisions",
            str(missing_decisions),
            "--format",
            "json",
            "--fail-on-not-ready",
            check=False,
        )
        _assert(blocked.returncode == 1, "missing supplied ledger should block release readiness")
        _assert(
            "supplied_decisions_missing" in json.loads(blocked.stdout)["blockers"],
            "missing supplied ledger blocker should be explicit",
        )

    print("Energy Core release smoke passed.")
    return 0


def _run(module: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
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
