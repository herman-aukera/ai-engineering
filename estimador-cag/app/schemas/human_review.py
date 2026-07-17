"""Strict contracts for checkpoint-safe human review decisions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HumanReviewMode = Literal["disabled", "required", "risk_based"]
StructureReviewAction = Literal["approve", "edit", "reject", "regenerate"]
FinalEstimateReviewAction = Literal["approve", "reject", "request_recovery", "override"]


class StrictReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewedRequirement(StrictReviewPayload):
    requirement_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=2000)


class ReviewedComponent(StrictReviewPayload):
    component_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    category: str = Field(min_length=1, max_length=120)
    requirement_ids: list[str] = Field(min_length=1)


class StructureReviewDecision(StrictReviewPayload):
    """Human response returned to a structure-gate interrupt."""

    action: StructureReviewAction
    expected_revision: int = Field(ge=0)
    reason: str | None = Field(default=None, max_length=2000)
    requirements: list[ReviewedRequirement] | None = None
    components: list[ReviewedComponent] | None = None
    v2_modules: list[dict[str, object]] | None = None

    @model_validator(mode="after")
    def validate_action_contract(self) -> StructureReviewDecision:
        if self.action == "edit":
            if not self.requirements or not self.components:
                raise ValueError("edit requires non-empty requirements and components")
            known_requirement_ids = {
                requirement.requirement_id for requirement in self.requirements
            }
            if len(known_requirement_ids) != len(self.requirements):
                raise ValueError("reviewed requirement_id values must be unique")

            component_ids = [component.component_id for component in self.components]
            if len(set(component_ids)) != len(component_ids):
                raise ValueError("reviewed component_id values must be unique")

            referenced_requirement_ids = {
                requirement_id
                for component in self.components
                for requirement_id in component.requirement_ids
            }
            unknown_ids = referenced_requirement_ids - known_requirement_ids
            if unknown_ids:
                raise ValueError(
                    "reviewed components reference unknown requirements: "
                    + ", ".join(sorted(unknown_ids))
                )
        elif (
            self.requirements is not None
            or self.components is not None
            or self.v2_modules is not None
        ):
            raise ValueError("only edit may include requirements or components")

        if self.action in {"reject", "regenerate"} and not (self.reason or "").strip():
            raise ValueError(f"{self.action} requires a reason")
        return self


class HumanBaselineOverride(StrictReviewPayload):
    component_id: str = Field(min_length=1, max_length=120)
    hours: float = Field(gt=0, le=100_000)
    evidence_refs: list[str] = Field(min_length=1, max_length=50)


class FinalEstimateReviewDecision(StrictReviewPayload):
    """Strict resume value for the final estimate gate."""

    action: FinalEstimateReviewAction
    expected_revision: int = Field(ge=0)
    actor: str = Field(min_length=1, max_length=240)
    reason: str | None = Field(default=None, max_length=2000)
    overrides: list[HumanBaselineOverride] | None = None

    @model_validator(mode="after")
    def validate_final_action_contract(self) -> FinalEstimateReviewDecision:
        reason = (self.reason or "").strip()
        if self.action in {"reject", "request_recovery", "override"} and not reason:
            raise ValueError(f"{self.action} requires a reason")
        if self.action == "override":
            if not self.overrides:
                raise ValueError("override requires at least one typed baseline")
            component_ids = [item.component_id for item in self.overrides]
            if len(component_ids) != len(set(component_ids)):
                raise ValueError("override component_id values must be unique")
        elif self.overrides is not None:
            raise ValueError("only override may include baseline overrides")
        return self
