from energy_core.decider import evaluate_candidate
from energy_core.models import CandidateState, EvidenceRecord
from energy_core.policy import load_policy

POLICY_PATH = ".energy/specs/0001-energy-policy-ledger/energy-policy.yaml"


def test_decider_repairs_when_required_evidence_is_missing():
    policy = load_policy(POLICY_PATH)
    candidate = CandidateState(
        candidate_id="slice-001-missing-evidence",
        spec_id="0001-energy-policy-ledger",
        energy_before=300,
        changed_files=["energy_core/cli.py"],
        required_artifacts=[],
        present_artifacts=[],
        validation_claims=["implementation complete"],
        scope_claims=[],
    )

    decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=[])

    assert decision.decision == "repair"
    assert "missing_required_evidence" in decision.hard_repair_violations
    assert decision.missing_evidence
    assert decision.next_action == "add_required_evidence"


def test_decider_repairs_lint_failure_without_rejecting():
    policy = load_policy(POLICY_PATH)
    candidate = CandidateState(
        candidate_id="slice-001-lint-failed",
        spec_id="0001-energy-policy-ledger",
        changed_files=["energy_core/policy.py"],
    )
    evidence = [
        EvidenceRecord(
            evidence_id="ev-lint-failed",
            type="lint_output",
            status="fail",
            summary="ruff reported fixable violations",
            exit_code=1,
        )
    ]

    decision = evaluate_candidate(policy=policy, candidate=candidate, evidence=evidence)

    assert decision.decision == "repair"
    assert "lint_failed" in decision.hard_repair_violations
    assert decision.hard_reject_violations == []
