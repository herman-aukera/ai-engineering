from __future__ import annotations

from pathlib import Path

from energy_core.candidate_readiness import build_candidate_readiness_matrix

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
    print(
        "Energy Core candidate readiness smoke passed: "
        f"complete={matrix['complete']}, "
        f"ready={matrix['ready_cases']}/{matrix['total_cases']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
