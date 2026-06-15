from __future__ import annotations

from pathlib import Path

from energy_core.candidate_readiness import (
    build_candidate_readiness_matrix,
    format_candidate_readiness_text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = PROJECT_ROOT / ".energy/specs/0001-energy-policy-ledger"
POLICY = SPEC_DIR / "energy-policy.yaml"
EVIDENCE = SPEC_DIR / "evidence.jsonl"


def main() -> int:
    matrix = build_candidate_readiness_matrix(
        spec_dir=SPEC_DIR,
        policy_path=POLICY,
        evidence_path=EVIDENCE,
    )
    output = format_candidate_readiness_text(matrix)

    assert matrix["complete"] is True
    assert "Energy Aware Code Candidate Readiness" in output

    print(output)
    print("Energy Core candidate readiness smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
