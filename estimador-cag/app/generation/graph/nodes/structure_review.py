"""Durable human structure gate for the Session 13 Plus reviewed graph."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.types import interrupt

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.schemas.human_review import HumanReviewMode, StructureReviewDecision

StructureReviewNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState],
]


class StaleStructureReviewError(RuntimeError):
    """Raised when a human response targets an obsolete review revision."""


def _structure_issue_codes(state: ReviewedEstimationGraphState) -> list[str]:
    errors = state.get("errors")
    if not isinstance(errors, list):
        return []

    return sorted(
        {
            str(error.get("code"))
            for error in errors
            if isinstance(error, dict)
            and error.get("node") in {"extract_requirements", "classify_components"}
            and error.get("code")
        }
    )


def _should_interrupt(
    state: ReviewedEstimationGraphState,
    *,
    mode: HumanReviewMode,
) -> bool:
    if mode == "disabled":
        return False
    if mode == "required":
        return True
    return bool(state.get("review_required") or _structure_issue_codes(state))


def _review_payload(
    state: ReviewedEstimationGraphState,
    *,
    revision: int,
    mode: HumanReviewMode,
) -> dict[str, Any]:
    return {
        "gate": "structure_review",
        "instruction": (
            "Approve, edit, reject, or request regeneration of the structured "
            "requirements and components."
        ),
        "estimation_id": state.get("estimation_id"),
        "graph_version": state.get("graph_version"),
        "review_mode": mode,
        "revision": revision,
        "requirements": state.get("requirements", []),
        "components": state.get("components", []),
        "issues": [
            error
            for error in state.get("errors", [])
            if isinstance(error, dict)
            and error.get("node") in {"extract_requirements", "classify_components"}
        ],
        "allowed_actions": ["approve", "edit", "reject", "regenerate"],
    }


def _trace_event(
    *,
    event_type: str,
    summary: str,
    state_delta_keys: list[str],
    evidence_refs: list[str],
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "node": "structure_review",
        "summary": summary,
        "evidence_refs": evidence_refs,
        "state_delta_keys": state_delta_keys,
    }


def build_structure_review_node(
    *,
    default_mode: HumanReviewMode = "risk_based",
) -> StructureReviewNode:
    """Build a replay-safe interrupt gate over structure-only state."""

    async def structure_review(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        raw_mode = state.get("human_review_mode", default_mode)
        mode: HumanReviewMode = raw_mode
        revision = int(state.get("structure_review_revision", 0))

        if not _should_interrupt(state, mode=mode):
            return {
                "structure_review_status": "skipped",
                "structure_route": "continue",
                "trace_events": [
                    _trace_event(
                        event_type="structure_review_skipped",
                        summary=f"Structure review was skipped in {mode} mode.",
                        state_delta_keys=[
                            "structure_review_status",
                            "structure_route",
                            "trace_events",
                        ],
                        evidence_refs=[],
                    )
                ],
            }

        raw_decision = interrupt(
            _review_payload(
                state,
                revision=revision,
                mode=mode,
            )
        )
        decision = StructureReviewDecision.model_validate(raw_decision)
        if decision.expected_revision != revision:
            raise StaleStructureReviewError(
                "structure review revision does not match the current checkpoint"
            )

        next_revision = revision + 1
        requirement_ids = [
            str(requirement.get("requirement_id"))
            for requirement in state.get("requirements", [])
            if isinstance(requirement, dict) and requirement.get("requirement_id")
        ]
        component_ids = [
            str(component.get("component_id"))
            for component in state.get("components", [])
            if isinstance(component, dict) and component.get("component_id")
        ]
        evidence_refs = [*requirement_ids, *component_ids]
        common_update: ReviewedEstimationGraphState = {
            "structure_review_revision": next_revision,
            "structure_review_record": {
                "action": decision.action,
                "reason": decision.reason,
                "revision": next_revision,
            },
        }

        if decision.action == "approve":
            resolved_codes = _structure_issue_codes(state)
            return {
                **common_update,
                "review_required": False,
                "structure_review_status": "approved",
                "structure_route": "continue",
                "resolved_issue_codes": resolved_codes,
                "trace_events": [
                    _trace_event(
                        event_type="structure_approved",
                        summary="A human approved the proposed project structure.",
                        state_delta_keys=[
                            "review_required",
                            "structure_review_revision",
                            "structure_review_status",
                            "structure_review_record",
                            "structure_route",
                            "resolved_issue_codes",
                            "trace_events",
                        ],
                        evidence_refs=evidence_refs,
                    )
                ],
            }

        if decision.action == "edit":
            reviewed_requirements = [
                requirement.model_dump(mode="json")
                for requirement in decision.requirements or []
            ]
            reviewed_components = [
                component.model_dump(mode="json")
                for component in decision.components or []
            ]
            reviewed_evidence_refs = [
                *[
                    requirement["requirement_id"]
                    for requirement in reviewed_requirements
                ],
                *[
                    component["component_id"]
                    for component in reviewed_components
                ],
            ]
            return {
                **common_update,
                "requirements": reviewed_requirements,
                "components": reviewed_components,
                "v2_modules": decision.v2_modules or [],
                "review_required": False,
                "structure_review_status": "edited",
                "structure_route": "continue",
                "resolved_issue_codes": _structure_issue_codes(state),
                "trace_events": [
                    _trace_event(
                        event_type="structure_edited",
                        summary="A human edited and approved the project structure.",
                        state_delta_keys=[
                            "requirements",
                            "components",
                            "v2_modules",
                            "review_required",
                            "structure_review_revision",
                            "structure_review_status",
                            "structure_review_record",
                            "structure_route",
                            "resolved_issue_codes",
                            "trace_events",
                        ],
                        evidence_refs=reviewed_evidence_refs,
                    )
                ],
            }

        if decision.action == "regenerate":
            return {
                **common_update,
                "review_required": True,
                "structure_review_status": "regeneration_requested",
                "structure_route": "regenerate",
                "trace_events": [
                    _trace_event(
                        event_type="structure_regeneration_requested",
                        summary=decision.reason or "A human requested structure regeneration.",
                        state_delta_keys=[
                            "review_required",
                            "structure_review_revision",
                            "structure_review_status",
                            "structure_review_record",
                            "structure_route",
                            "trace_events",
                        ],
                        evidence_refs=evidence_refs,
                    )
                ],
            }

        return {
            **common_update,
            "review_required": True,
            "status": "needs_review",
            "structure_review_status": "rejected",
            "structure_route": "stop",
            "trace_events": [
                _trace_event(
                    event_type="structure_rejected",
                    summary=decision.reason or "A human rejected the proposed structure.",
                    state_delta_keys=[
                        "review_required",
                        "status",
                        "structure_review_revision",
                        "structure_review_status",
                        "structure_review_record",
                        "structure_route",
                        "trace_events",
                    ],
                    evidence_refs=evidence_refs,
                )
            ],
        }

    return structure_review
