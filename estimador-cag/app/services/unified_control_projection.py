"""Allowlisted product projection for the unified Control Room."""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.graph_estimation import GraphEstimationRun

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "authorization",
    "dsn",
    "hidden_reasoning",
    "password",
    "prompt",
    "raw_provider_output",
    "secret",
    "token",
    "transcript",
)
_SECRET_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|pylf_[A-Za-z0-9_-]{20,}|BEGIN (?:RSA|OPENSSH|PRIVATE) KEY)"
)
SafeScalar = str | int | float | bool | None
SafeValue = SafeScalar | list[object] | dict[str, object]


class UnifiedControlProjection(BaseModel):
    """Strict response that excludes raw source and provider content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    estimation_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    execution_status: Literal["completed", "awaiting_human_review"]
    graph_version: str = Field(min_length=1)
    status: str
    unified_phase: str
    review_required: bool
    human_review_status: str
    human_review_revision: int = Field(ge=0)
    human_review_reason_codes: list[str]
    route_events: list[dict[str, object]]
    critic_report: dict[str, object]
    boss_decision: dict[str, object]
    reliability_report: dict[str, object]
    competition_candidates: list[dict[str, object]]
    competition_assessment: dict[str, object]
    authorized_capabilities: dict[str, str]
    context_detail: str
    context_id: str | None
    context_fingerprint: str | None
    context_source_revision: int = Field(ge=0)
    context_evidence_refs: list[str]
    proposal: dict[str, object]
    rollback_paths: list[str]


def _safe_projection(value: object, *, path: str) -> SafeValue:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if _SECRET_PATTERN.search(value):
            raise ValueError(f"secret-like value is forbidden: {path}")
        return value
    if isinstance(value, list):
        return [
            _safe_projection(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
                raise ValueError(f"sensitive field is forbidden: {path}.{key}")
            result[key] = _safe_projection(item, path=f"{path}.{key}")
        return result
    raise ValueError(f"unsupported projected value at {path}")


def _mapping(state: Mapping[str, object], key: str) -> dict[str, object]:
    raw = state.get(key)
    if not isinstance(raw, Mapping):
        return {}
    projected = _safe_projection(raw, path=key)
    if not isinstance(projected, dict):
        raise ValueError(f"{key} projection must be a mapping")
    return projected


def _mapping_list(
    state: Mapping[str, object],
    key: str,
) -> list[dict[str, object]]:
    raw = state.get(key)
    if not isinstance(raw, list):
        return []
    projected = _safe_projection(raw, path=key)
    if not isinstance(projected, list):
        raise ValueError(f"{key} projection must be a list")
    result: list[dict[str, object]] = []
    for item in projected:
        if not isinstance(item, dict):
            raise ValueError(f"{key} entries must be mappings")
        result.append(item)
    return result


def unified_control_projection_from_run(
    run: GraphEstimationRun,
) -> UnifiedControlProjection:
    """Project only control-plane evidence from an executed unified thread."""

    state = run.state
    context = _mapping(state, "plus_compacted_context")
    authorized_raw = state.get("plus_authorized_capabilities")
    authorized = (
        {
            str(key): str(value)
            for key, value in authorized_raw.items()
        }
        if isinstance(authorized_raw, Mapping)
        else {}
    )
    evidence_refs = context.get("evidence_refs", [])
    if not isinstance(evidence_refs, list):
        evidence_refs = []

    projection = UnifiedControlProjection(
        estimation_id=run.estimation_id,
        thread_id=run.thread_id,
        execution_status=run.execution_status,
        graph_version=str(state.get("graph_version", "unknown")),
        status=str(state.get("status", "unknown")),
        unified_phase=str(state.get("unified_phase", "unknown")),
        review_required=bool(state.get("review_required", False)),
        human_review_status=str(
            state.get("human_review_status", "not_requested")
        ),
        human_review_revision=int(state.get("human_review_revision", 0)),
        human_review_reason_codes=[
            str(value)
            for value in state.get("human_review_reason_codes", [])
            if isinstance(value, str)
        ],
        route_events=_mapping_list(state, "unified_route_events"),
        critic_report=_mapping(state, "critic_report"),
        boss_decision=_mapping(state, "boss_decision"),
        reliability_report=_mapping(state, "reliability_report"),
        competition_candidates=_mapping_list(
            state,
            "plus_competition_candidates",
        ),
        competition_assessment=_mapping(
            state,
            "plus_competition_assessment",
        ),
        authorized_capabilities=authorized,
        context_detail=str(state.get("plus_context_detail", "medium")),
        context_id=(
            str(context["context_id"])
            if context.get("context_id") is not None
            else None
        ),
        context_fingerprint=(
            str(context["fingerprint"])
            if context.get("fingerprint") is not None
            else None
        ),
        context_source_revision=int(
            state.get("plus_context_source_revision", 0)
        ),
        context_evidence_refs=[
            str(value)
            for value in evidence_refs
            if isinstance(value, str)
        ],
        proposal=_mapping(state, "proposal"),
        rollback_paths=[
            "/api/v1/estimate/graph",
            "/api/v1/estimate/graph/reviewed/start",
        ],
    )
    return projection.model_copy(deep=True)
