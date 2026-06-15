from __future__ import annotations

from pathlib import Path

from energy_core.evidence_matrix import (
    build_evidence_matrix,
    format_evidence_matrix_markdown,
)

SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
POLICY = SPEC_DIR / "energy-policy.yaml"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def main() -> int:
    matrix = build_evidence_matrix(POLICY, EVIDENCE)
    markdown = format_evidence_matrix_markdown(matrix)

    assert matrix["complete"] is True
    assert matrix["missing_required_acceptance"] == []
    assert "# Energy Aware Code Evidence Matrix" in markdown
    assert "pytest_output" in markdown

    print("Energy Core evidence matrix smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
