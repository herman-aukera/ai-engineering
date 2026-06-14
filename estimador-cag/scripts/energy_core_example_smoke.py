from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / ".energy/specs/0001-energy-policy-ledger"
POLICY = SPEC_DIR / "energy-policy.yaml"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def main() -> int:
    matrix_json = _run(
        "--spec-dir",
        str(SPEC_DIR),
        "--policy",
        str(POLICY),
        "--evidence",
        str(EVIDENCE),
        "--format",
        "json",
        "--fail-on-mismatch",
    )
    matrix = json.loads(matrix_json.stdout)
    _assert(matrix["complete"] is True, "example matrix should be complete")
    _assert(matrix["passed_cases"] == 4, "example matrix should pass all bundled examples")

    matrix_markdown = _run(
        "--spec-dir",
        str(SPEC_DIR),
        "--policy",
        str(POLICY),
        "--evidence",
        str(EVIDENCE),
        "--format",
        "markdown",
        "--fail-on-mismatch",
    )
    _assert("# Energy Aware Code Example Matrix" in matrix_markdown.stdout, "Markdown matrix should print")
    _assert("Passed cases: 4/4" in matrix_markdown.stdout, "Markdown matrix should include pass count")

    print("Energy Core example smoke passed.")
    return 0


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "energy_core.examples_cli", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    raise SystemExit(main())
