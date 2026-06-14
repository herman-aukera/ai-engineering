import json
import subprocess
import sys
from pathlib import Path


SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")


def test_cli_evaluates_candidate_and_appends_decision_ledger(tmp_path):
    decisions_path = tmp_path / "decisions.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_core.cli",
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
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    ledger_rows = decisions_path.read_text(encoding="utf-8").splitlines()

    assert payload["decision"] == "accept"
    assert payload["candidate_id"] == "slice-001-accept"
    assert len(ledger_rows) == 1
    assert json.loads(ledger_rows[0])["candidate_id"] == "slice-001-accept"
