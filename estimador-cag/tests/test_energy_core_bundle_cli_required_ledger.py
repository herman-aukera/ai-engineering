from __future__ import annotations

import json
from pathlib import Path

from energy_core import cli

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = PROJECT_ROOT / ".energy/specs/0001-energy-policy-ledger"
POLICY = SPEC_DIR / "energy-policy.yaml"
ACCEPT_CANDIDATE = SPEC_DIR / "examples/candidate_accept.json"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def test_bundle_manifest_cli_fails_for_supplied_absent_ledger(tmp_path: Path, capsys) -> None:
    supplied_ledger = tmp_path / "ledger.jsonl"

    exit_code = cli.main(
        [
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
            str(supplied_ledger),
            "--format",
            "json",
            "--fail-on-incomplete",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["complete"] is False
    assert str(supplied_ledger.resolve()) in payload["missing_required"]
