from pathlib import Path

from energy_core.examples import build_example_matrix, format_example_matrix_markdown, format_example_matrix_text

SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
POLICY = SPEC_DIR / "energy-policy.yaml"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def test_example_matrix_matches_expected_decisions() -> None:
    matrix = build_example_matrix(spec_dir=SPEC_DIR, policy_path=POLICY, evidence_path=EVIDENCE)

    assert matrix["complete"] is True
    assert matrix["passed_cases"] == 4
    assert matrix["failed_cases"] == 0
    assert matrix["missing_examples"] == []

    decisions = {case["example"]: case["actual_decision"] for case in matrix["cases"]}
    assert decisions == {
        "candidate_accept.json": "accept",
        "candidate_repair_missing_evidence.json": "repair",
        "candidate_reject_tests_failed.json": "reject",
        "candidate_reject_scope_creep.json": "reject",
    }


def test_example_matrix_reports_are_human_readable() -> None:
    matrix = build_example_matrix(spec_dir=SPEC_DIR, policy_path=POLICY, evidence_path=EVIDENCE)

    text = format_example_matrix_text(matrix)
    markdown = format_example_matrix_markdown(matrix)

    assert "Energy Aware Code Example Matrix" in text
    assert "candidate_reject_scope_creep.json" in text
    assert "# Energy Aware Code Example Matrix" in markdown
    assert "Expected decision: reject" in markdown
