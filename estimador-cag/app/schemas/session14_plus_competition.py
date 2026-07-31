"""Strict contracts for bounded estimate competition in Session 14 Plus."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.v3_energy import ConstraintEnergySnapshot

CompetitionVariant = Literal[
    "baseline",
    "aggressive",
    "conservative",
    "synthesized",
]
CompetitionDisposition = Literal[
    "accept_synthesized",
    "human_review",
]


class StrictCompetitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CompetitionComponent(StrictCompetitionModel):
    component_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    hours: float | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list)


class EstimateCompetitionCandidate(StrictCompetitionModel):
    candidate_id: str = Field(min_length=1)
    variant: CompetitionVariant
    policy_version: str = Field(min_length=1)
    components: list[CompetitionComponent]
    total_hours: float | None = Field(default=None, ge=0)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    assumptions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_total(self) -> EstimateCompetitionCandidate:
        hours = [component.hours for component in self.components]
        if any(value is None for value in hours):
            if self.total_hours is not None:
                raise ValueError("candidate with missing component hours has no total")
            return self
        expected = round(sum(float(value) for value in hours), 2)
        if self.total_hours != expected:
            raise ValueError("candidate total must equal component hours")
        return self


class EstimateCompetitionAssessment(StrictCompetitionModel):
    assessment_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    baseline_candidate_id: str = Field(min_length=1)
    aggressive_candidate_id: str = Field(min_length=1)
    conservative_candidate_id: str = Field(min_length=1)
    synthesized_candidate_id: str = Field(min_length=1)
    selected_candidate_id: str = Field(min_length=1)
    divergence_ratio: float | None = Field(default=None, ge=0)
    material_divergence_threshold: float = Field(gt=0, le=1)
    average_confidence: float = Field(ge=0, le=1)
    conservative_weight: float = Field(ge=0.5, le=0.75)
    disposition: CompetitionDisposition
    review_required: bool
    reason_codes: list[str]
    energy_snapshot: ConstraintEnergySnapshot

    @model_validator(mode="after")
    def validate_disposition(self) -> EstimateCompetitionAssessment:
        if self.disposition == "human_review" and not self.review_required:
            raise ValueError("human review disposition requires review_required")
        if self.disposition == "accept_synthesized":
            if self.review_required:
                raise ValueError("accepted synthesis cannot require review")
            if self.selected_candidate_id != self.synthesized_candidate_id:
                raise ValueError("accepted synthesis must select synthesized candidate")
        return self


class EstimateCompetitionOutcome(StrictCompetitionModel):
    candidates: list[EstimateCompetitionCandidate]
    assessment: EstimateCompetitionAssessment
    selected_component_estimates: list[dict[str, object]]

    @model_validator(mode="after")
    def validate_candidate_identity(self) -> EstimateCompetitionOutcome:
        by_id = {candidate.candidate_id: candidate for candidate in self.candidates}
        if len(by_id) != len(self.candidates):
            raise ValueError("competition candidate IDs must be unique")
        required = {
            self.assessment.baseline_candidate_id,
            self.assessment.aggressive_candidate_id,
            self.assessment.conservative_candidate_id,
            self.assessment.synthesized_candidate_id,
            self.assessment.selected_candidate_id,
        }
        if not required.issubset(by_id):
            raise ValueError("assessment references unknown candidate")
        return self
