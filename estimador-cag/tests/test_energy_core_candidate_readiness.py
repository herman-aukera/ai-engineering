from __future__ import annotations

import json
from pathlib import Path

from energy_core.candidate_readiness import build_candidate_readiness_matrix
from energy_core.candidate_readiness_cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = PROJECT_ROOT / ".energy/specs/0001-energy-policy-ledger"
POLICY = SPEC_DIR / "energy-policy.yaml"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def test_candidate_readiness_matrix_marks_intentional_not_ready_examples() -> None:
    matrix = build_candidate_readiness_matrix(
        spec_dir=SPEC_DIR,
        policy_path=POLICY,
        evidence_path=EVIDENCE,
    )

    assert matrix["complete"] is True
    assert matrix["total_cases"] == 4
    assert matrix["ready_cases"] == 2
    assert matrix["not_ready_cases"] == 2

    cases = {case["example"]: case for case in matrix["cases"]}
    assert cases["candidate_accept.json"]["ready"] is True
    assert cases["candidate_reject_scope_creep.json"]["ready"] is True
    assert cases["candidate_repair_missing_evidence.json"]["ready"] is False
    assert cases["candidate_reject_tests_failed.json"]["ready"] is False


def test_candidate_readiness_cli_json_output(capsys) -> None:
    exit_code = main(
        [
            "--spec-dir",
            str(SPEC_DIR),
            "--policy",
            str(POLICY),
            "--evidence",
            str(EVIDENCE),
            "--format",
            "json",
            "--fail-on-incomplete",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["complete"] is True
    assert payload["ready_cases"] == 2
    assert payload["not_ready_cases"] == 2
