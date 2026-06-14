import json

from energy_core.ledger import append_decision
from energy_core.models import EnergyDecision


def _decision(candidate_id: str, decision: str) -> EnergyDecision:
    return EnergyDecision(
        policy_id="energy-code-default",
        candidate_id=candidate_id,
        decision=decision,
        energy_before=100,
        energy_after=0,
        energy_delta=-100,
        hard_reject_violations=[],
        hard_repair_violations=[],
        soft_violations=[],
        missing_evidence=[],
        evidence_refs=[],
        required_repairs=[],
        reasoning_summary="Decision accepted by deterministic test evidence.",
        next_action="stop",
    )


def test_decision_ledger_appends_jsonl_records_without_overwriting(tmp_path):
    ledger_path = tmp_path / "decisions.jsonl"

    append_decision(ledger_path, _decision("candidate-001", "accept"))
    append_decision(ledger_path, _decision("candidate-002", "repair"))

    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]

    assert [row["candidate_id"] for row in rows] == ["candidate-001", "candidate-002"]
    assert [row["decision"] for row in rows] == ["accept", "repair"]
