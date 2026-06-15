from pathlib import Path

from energy_core.evidence_matrix import (
    build_evidence_matrix,
    format_evidence_matrix_markdown,
    format_evidence_matrix_text,
)

SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
POLICY = SPEC_DIR / "energy-policy.yaml"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def test_evidence_matrix_is_complete_for_default_evidence() -> None:
    matrix = build_evidence_matrix(POLICY, EVIDENCE)

    assert matrix["complete"] is True
    assert matrix["record_total"] == 5
    assert matrix["missing_required_acceptance"] == []
    assert matrix["undeclared_record_types"] == []


def test_evidence_matrix_rows_include_required_acceptance_status() -> None:
    matrix = build_evidence_matrix(POLICY, EVIDENCE)
    rows = {row["evidence_type"]: row for row in matrix["rows"]}

    assert rows["pytest_output"]["required_acceptance"] is True
    assert rows["pytest_output"]["has_trusted_pass"] is True
    assert rows["lint_output"]["trusted_pass_total"] == 1


def test_evidence_matrix_formats_text_and_markdown() -> None:
    matrix = build_evidence_matrix(POLICY, EVIDENCE)

    text = format_evidence_matrix_text(matrix)
    markdown = format_evidence_matrix_markdown(matrix)

    assert "Energy Aware Code Evidence Matrix" in text
    assert "Complete: True" in text
    assert "# Energy Aware Code Evidence Matrix" in markdown
    assert "## Missing required acceptance evidence" in markdown
