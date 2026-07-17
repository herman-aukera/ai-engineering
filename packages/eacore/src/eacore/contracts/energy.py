from __future__ import annotations

from pydantic import Field, model_validator

from .base import StrictModel


class EnergyComponent(StrictModel):
    component_id: str
    constraint_id: str
    penalty: float = Field(ge=0, allow_inf_nan=False)
    hard_blocking: bool = False
    observation_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()


class EnergySnapshot(StrictModel):
    energy_snapshot_id: str
    candidate_id: str
    policy_ref: str
    energy_before: float = Field(ge=0, allow_inf_nan=False)
    energy_after: float = Field(ge=0, allow_inf_nan=False)
    energy_delta: float = Field(allow_inf_nan=False)
    hard_failure_refs: tuple[str, ...] = ()
    missing_evidence_refs: tuple[str, ...] = ()
    conflict_refs: tuple[str, ...] = ()
    components: tuple[EnergyComponent, ...]
    setup_work: bool = False
    setup_work_justification: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_arithmetic(self) -> EnergySnapshot:
        expected_delta = self.energy_after - self.energy_before
        if abs(expected_delta - self.energy_delta) > 1e-9:
            raise ValueError("energy_delta must equal energy_after - energy_before")
        if self.setup_work and not self.setup_work_justification:
            raise ValueError("setup work requires an explicit bounded justification")
        if not self.setup_work and self.setup_work_justification is not None:
            raise ValueError("setup_work_justification requires setup_work=true")
        return self
