"""Strict contracts for selective agent-assisted evidence recovery."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agent_runtime import AgentRuntimeResult


class StrictRecoveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchRecoveryEvidenceArgs(StrictRecoveryModel):
    component_id: str = Field(min_length=1, max_length=120)
    query: str = Field(min_length=3, max_length=1000)


class SelectRecoveryEvidenceArgs(StrictRecoveryModel):
    component_id: str = Field(min_length=1, max_length=120)
    search_id: str = Field(min_length=1, max_length=160)


class ValidateRecoveryArgs(StrictRecoveryModel):
    component_ids: list[str] = Field(min_length=1)


class RecoveryBudgetMatch(StrictRecoveryModel):
    """One accepted server-owned historical reference."""

    component_id: str = Field(min_length=1)
    budget_id: str = Field(min_length=1)
    reference_component_id: str | None = None
    source_document_id: str = Field(min_length=1)
    source_chunk_id: str = Field(min_length=1)
    recorded_hours: float | None = Field(default=None, gt=0)
    distance: float | None = Field(default=None, ge=0)
    score: float | None = None
    retrieval_method: str = Field(min_length=1)


class SelectiveRecoveryResult(StrictRecoveryModel):
    """Recovered evidence plus bounded runtime evidence, never model-authored hours."""

    flagged_component_ids: list[str]
    recovered_component_ids: list[str]
    unresolved_component_ids: list[str]
    recovered_matches: list[RecoveryBudgetMatch]
    runtime: AgentRuntimeResult
