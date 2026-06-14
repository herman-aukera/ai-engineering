import json
from pathlib import Path

from energy_core.models import CandidateState
from energy_core.policy import load_policy
from energy_core.state import read_candidate_state
from energy_core.validation import validate_candidate_state, validate_policy

SPEC_DIR = Path(".energy/specs/0001-energy-policy-ledger")
POLICY_PATH = SPEC_DIR / "energy-policy.yaml"
ACCEPT_CANDIDATE = SPEC_DIR / "examples/candidate_accept.json"


def test_policy_validation_accepts_default_policy():
    policy = load_policy(POLICY_PATH)

    summary = validate_policy(policy)

    assert summary["complete"] is True
    assert summary["missing"] == []
    assert summary["thresholds_valid"] is True
    assert "pytest_output" in summary["required_acceptance_evidence"]
    assert summary["missing_hard_constraints"] == []
    assert summary["missing_evidence_types"] == []


def test_candidate_validation_accepts_default_candidate():
    policy = load_policy(POLICY_PATH)
    candidate = read_candidate_state(ACCEPT_CANDIDATE)

    summary = validate_candidate_state(policy, candidate)

    assert summary["complete"] is True
    assert summary["candidate_id"] == "slice-001-accept"
    assert summary["missing"] == []
    assert summary["unknown_soft_flags"] == []


def test_candidate_validation_detects_unknown_soft_flags():
    policy = load_policy(POLICY_PATH)
    candidate = CandidateState(
        candidate_id="bad-candidate",
        spec_id="0001-energy-policy-ledger",
        changed_files=["energy_core/example.py"],
        soft_flags=["imaginary_soft_constraint"],
    )

    summary = validate_candidate_state(policy, candidate)

    assert summary["complete"] is False
    assert "known_soft_flags" in summary["missing"]
    assert summary["unknown_soft_flags"] == ["imaginary_soft_constraint"]


def test_policy_validation_detects_missing_required_contracts(tmp_path):
    bad_policy_path = tmp_path / "bad-policy.json"
    policy_payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    policy_payload["hard_constraints"].pop("tests_failed")
    policy_payload["required_acceptance_evidence"].append("unknown_evidence_type")
    bad_policy_path.write_text(json.dumps(policy_payload), encoding="utf-8")

    policy = load_policy(bad_policy_path)
    summary = validate_policy(policy)

    assert summary["complete"] is False
    assert "required_hard_constraints" in summary["missing"]
    assert "known_required_acceptance_evidence" in summary["missing"]
    assert summary["missing_hard_constraints"] == ["tests_failed"]
    assert summary["unknown_acceptance_evidence"] == ["unknown_evidence_type"]
