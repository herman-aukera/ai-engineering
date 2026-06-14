from energy_core.adapter_contracts import (
    AdapterActionProposal,
    AdapterEvidencePacket,
    proposal_to_candidate_state,
)
from energy_core.models import EvidenceRecord


def test_adapter_proposal_maps_to_candidate_state_without_execution() -> None:
    proposal = AdapterActionProposal(
        proposal_id="proposal-001",
        adapter="aider",
        mode="patch_review",
        summary="Review a proposed patch before applying it.",
        affected_files=["energy_core/example.py"],
        expected_evidence_types=["pytest_output", "git_diff"],
        risk_level="low",
    )

    candidate = proposal_to_candidate_state(
        proposal,
        spec_id="0001-energy-policy-ledger",
    )

    assert proposal.execution_performed is False
    assert candidate.candidate_id == "proposal-001"
    assert candidate.spec_id == "0001-energy-policy-ledger"
    assert candidate.changed_files == ["energy_core/example.py"]
    assert candidate.required_artifacts == ["pytest_output", "git_diff"]
    assert candidate.present_artifacts == []
    assert candidate.soft_flags == []


def test_high_risk_or_preexecuted_adapter_proposals_are_flagged() -> None:
    proposal = AdapterActionProposal(
        proposal_id="proposal-risky",
        adapter="cline",
        mode="command_review",
        summary="Review a command proposal before running it.",
        risk_level="high",
        execution_performed=True,
    )

    candidate = proposal_to_candidate_state(
        proposal,
        spec_id="0001-energy-policy-ledger",
    )

    assert "high_risk_adapter_proposal" in candidate.soft_flags
    assert "execution_already_performed" in candidate.soft_flags


def test_adapter_evidence_packet_keeps_evidence_untrusted_by_default() -> None:
    packet = AdapterEvidencePacket(
        packet_id="packet-001",
        proposal_id="proposal-001",
        produced_by="manual",
        evidence=[
            EvidenceRecord(
                evidence_id="ev-diff",
                type="git_diff",
                status="pass",
                summary="Diff was reviewed manually.",
            )
        ],
    )

    assert packet.trusted is False
    assert packet.evidence[0].type == "git_diff"
