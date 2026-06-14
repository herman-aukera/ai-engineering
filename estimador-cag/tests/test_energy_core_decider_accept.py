from energy_core.decider import evaluate_candidate
from energy_core.models import CandidateState, EvidenceRecord
from energy_core.policy import load_policy

POLICY_PATH = ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml"


def test_decider_accepts_candidate_with_required_trusted_evidence():
    policy = load_policy(POLICY_PATH)
    candidate = CandidateState(
        candidate_id="slice-001-accept",
        spec_id="0001-energy-policy-ledger",
        energy_before=500,
        changed_files=["energy_core/models.py", "tests/test_energy_core_decider_accept.py"],
        required_artifacts=["energy_core/models.py"],
        present_artifacts=["energy_core/models.py"],
        validation_claims=[],
        scope_claims=[],
    )
    evidence = [
        EvidenceRecord(evidence_id="ev-pytest", type="pytest_output", status="pass", summary="focused tests passed"),
        EvidenceRecord(evidence_id="ev-compile", type="compile_output", status="pass", summary="py_compile passed"),
        EvidenceRecord(evidence_id="ev-lint", type="lint_output", status="pass", summary="ruff passed"),
        EvidenceRecord(evidence_id="ev-secret", type="secret_scan_output", status="pass", summary="no secrets"),
        EvidenceRecord(evidence_id="ev-diff", type="git_diff", status="pass", summary="diff is scoped"),
    ]

    decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence)

    assert decision.decision == "accept"
    assert decision.energy_after < decision.energy_before
    assert decision.hard_reject_violations == []
    assert decision.hard_repair_violations == []
    assert decision.missing_evidence == []
