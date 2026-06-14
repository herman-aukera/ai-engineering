from __future__ import annotations

from typing import Literal

from pydantic import Field

from energy_core.models import CandidateState, EnergyModel, EvidenceRecord

AdapterKind = Literal["aider", "cline", "opencode", "manual", "unknown"]
AdapterMode = Literal["plan_review", "patch_review", "command_review", "diff_review"]
RiskLevel = Literal["low", "medium", "high"]


class AdapterActionProposal(EnergyModel):
    """Design-only contract for future adapter proposals.

    This model records what an adapter wants reviewed. It deliberately does not
    execute commands, mutate files, approve work, or append decisions.
    """

    proposal_id: str
    adapter: AdapterKind = "unknown"
    mode: AdapterMode
    summary: str
    affected_files: list[str] = Field(default_factory=list)
    expected_evidence_types: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "medium"
    requires_human_approval: bool = False
    execution_performed: bool = False


class AdapterEvidencePacket(EnergyModel):
    """Evidence bundle produced around an adapter proposal."""

    packet_id: str
    proposal_id: str
    produced_by: AdapterKind = "unknown"
    trusted: bool = False
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    summary: str = ""


def proposal_to_candidate_state(
    proposal: AdapterActionProposal,
    *,
    spec_id: str,
    energy_before: int = 500,
) -> CandidateState:
    """Map an adapter proposal to the existing deterministic judge contract."""

    soft_flags: list[str] = []
    if proposal.risk_level == "high":
        soft_flags.append("high_risk_adapter_proposal")
    if proposal.execution_performed:
        soft_flags.append("execution_already_performed")

    return CandidateState(
        candidate_id=proposal.proposal_id,
        spec_id=spec_id,
        energy_before=energy_before,
        changed_files=proposal.affected_files,
        required_artifacts=proposal.expected_evidence_types,
        present_artifacts=[],
        validation_claims=[proposal.summary],
        scope_claims=[proposal.mode],
        soft_flags=soft_flags,
    )
