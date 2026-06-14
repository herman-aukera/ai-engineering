from pathlib import Path

from energy_core.policy import load_policy

POLICY_PATH = Path(".energy/specs/0001-energy-policy-ledger/energy-policy.yaml")


def test_energy_policy_loads_default_hard_and_soft_constraints():
    policy = load_policy(POLICY_PATH)

    assert policy.policy_id == "energy-code-default"
    assert policy.version == "1.0.0"
    assert policy.thresholds.accept_max_soft_energy == 120
    assert policy.hard_constraints["tests_failed"].decision == "reject"
    assert policy.hard_constraints["missing_required_evidence"].decision == "repair"
    assert policy.soft_constraints["unnecessary_complexity"].penalty == 100
    assert policy.evidence_types["pytest_output"].trusted is True
