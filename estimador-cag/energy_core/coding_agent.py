"""Provider-neutral, inert coding-agent proposal contracts."""

from __future__ import annotations

from pydantic import Field

from energy_core.models import EnergyModel


class CodingProposal(EnergyModel):
    proposal_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    spec_id: str = Field(min_length=1)
    patch: str
    changed_files: tuple[str, ...] = Field(default_factory=tuple)
    proposed_commands: tuple[tuple[str, ...], ...] = Field(default_factory=tuple)


class ProposalAdapter:
    """Normalizes proposal data and intentionally has no execution method."""

    def normalize(self, payload: dict[str, object]) -> CodingProposal:
        return CodingProposal.model_validate(payload)
