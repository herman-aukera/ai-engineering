from energy_core.decider import evaluate_candidate
from energy_core.models import CandidateState, EvidenceRecord
from energy_core.policy import load_policy


POLICY_PATH = ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml"


def test_decider_rejects_failed_pytest_evidence():
    policy = load_policy(POLICY_PATH)
    candidate = CandidateState(
        candidate_id="slice-001-tests-failed",
        spec_id="0001-energy-policy-ledger",
        energy_before=400,
        changed_files=["energy_core/decider.py"],
        required_artifacts=[],
        present_artifacts=[],
        validation_claims=[],
        scope_claims=[],
    )
    evidence = [
        EvidenceRecord(
            evidence_id="ev-pytest-failed",
            type="pytest_output",
            status="fail",
            summary="pytest exited with status 1",
            exit_code=1,
        )
    ]

    decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence)

    assert decision.decision == "reject"
    assert "tests_failed" in decision.hard_reject_violations
    assert decision.energy_after >= 1000
    assert decision.next_action == "repair_blocking_violations"


def test_decider_rejects_scope_creep_claim():
    policy = load_policy(POLICY_PATH)
    candidate = CandidateState(
        candidate_id="slice-001-scope-creep",
        spec_id="0001-energy-policy-ledger",
        changed_files=["estimador-cag/app/energy_chat/evaluator.py"],
        required_artifacts=[],
        present_artifacts=[],
        validation_claims=[],
        scope_claims=["scope_creep"],
    )

    decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=[])

    assert decision.decision == "reject"
    assert "scope_creep" in decision.hard_reject_violations
