"""Provider-neutral semantic-classifier contracts for Session 13 Plus V3."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.schemas.v3_routing import ComplexityLevel, StrictV3Model

ArbitrationResolution = Literal[
    "consensus",
    "semantic_escalation",
    "deterministic_override",
]

TranscriptQuality = Literal[
    "well_structured",
    "conversational",
    "fragmentary",
    "ambiguous",
]


class SemanticSignals(StrictV3Model):
    """Provider-neutral signals extracted from a natural-language project transcript.

    These signals are designed to be produced by any LLM classifier without
    embedding provider-specific fields.  Provider identity is recorded on the
    enclosing ``SemanticAssessment``, not inside the signals payload.
    """

    domain_category: str = Field(
        min_length=1,
        max_length=120,
        description="Primary domain, e.g. 'web', 'data', 'infra', 'mobile'.",
    )
    primary_modality: str = Field(
        min_length=1,
        max_length=120,
        description="Dominant input modality, e.g. 'text', 'mixed', 'code_heavy'.",
    )
    scope_indicators: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Scope hints: 'greenfield', 'migration', 'integration', etc.",
    )
    risk_indicators: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Risk hints: 'compliance', 'security', 'data_loss', etc.",
    )
    ambiguity_flags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Ambiguity flags: 'vague_scope', 'contradictory', 'missing_details'.",
    )
    complexity_hints: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Complexity hints: 'multi_team', 'distributed', 'real_time', etc.",
    )
    estimated_requirement_count: int = Field(
        default=0,
        ge=0,
        le=500,
        description="LLM-estimated number of discrete requirements.",
    )
    estimated_integration_count: int = Field(
        default=0,
        ge=0,
        le=100,
        description="LLM-estimated number of external integrations.",
    )
    requires_specialist_review: bool = Field(
        default=False,
        description="The LLM recommends a human specialist review.",
    )
    transcript_quality: TranscriptQuality = Field(
        description="LLM-judged transcript structure quality.",
    )


class SemanticAssessment(StrictV3Model):
    """LLM-produced complexity classification, distinct from the deterministic baseline.

    This record is checkpoint-safe and provider-agnostic at the schema level.
    The *producer* (provider + model) is captured in ``classifier_version``
    rather than in dedicated provider fields, keeping the schema reusable
    across any LLM backend.
    """

    level: ComplexityLevel
    confidence: float = Field(ge=0, le=1, description="LLM self-reported confidence.")
    signals: SemanticSignals
    rationale: str = Field(
        min_length=1,
        max_length=2000,
        description="Natural-language explanation from the classifier.",
    )
    classifier_version: str = Field(
        min_length=1,
        max_length=240,
        description="Identifies the classifier that produced this assessment.",
    )


class ClassifierArbitration(StrictV3Model):
    """Resolved complexity after comparing deterministic and semantic assessments.

    The arbitration is a deterministic Python function.  The model never selects
    its own tier or promotes itself.  This record is checkpoint-safe and
    replayable.
    """

    arbitrated_level: ComplexityLevel
    resolution: ArbitrationResolution
    resolution_reason: str = Field(
        min_length=1,
        max_length=2000,
        description="Human-readable explanation of the arbitration decision.",
    )
    human_review_required: bool = Field(
        description="True when either assessment or arbitration logic demands human review.",
    )
    deterministic_assessment_ref: str = Field(
        min_length=1,
        max_length=240,
        description="classifier_version of the deterministic ComplexityAssessment.",
    )
    semantic_assessment_ref: str = Field(
        min_length=1,
        max_length=240,
        description="classifier_version of the semantic SemanticAssessment.",
    )

    @model_validator(mode="after")
    def validate_c5_forces_human_review(self) -> ClassifierArbitration:
        if self.arbitrated_level == "C5" and not self.human_review_required:
            raise ValueError("C5 arbitrated complexity requires human review")
        return self
