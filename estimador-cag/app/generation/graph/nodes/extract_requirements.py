"""First required Session 13 graph node: structured requirement extraction."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import (
    EstimationGraphState,
    IssueSeverity,
    RequirementItem,
)

ExtractRequirementsNode = Callable[
    [EstimationGraphState],
    Awaitable[EstimationGraphState],
]


def _execution_metadata(
    state: EstimationGraphState,
    *,
    requirement_count: int,
) -> dict[str, str | int]:
    metadata: dict[str, str | int] = dict(
        state.get("execution_metadata", {})
    )
    metadata["requirement_count"] = requirement_count
    return metadata


def _normalize_requirements(
    requirements: Sequence[RequirementItem],
) -> list[RequirementItem]:
    normalized: list[RequirementItem] = []
    seen_ids: set[str] = set()

    for requirement in requirements:
        requirement_id = requirement.get("requirement_id")
        text = requirement.get("text")

        if not isinstance(requirement_id, str):
            raise ValueError("requirement_id must be a string")
        if not isinstance(text, str):
            raise ValueError("requirement text must be a string")

        requirement_id = requirement_id.strip()
        text = text.strip()

        if not requirement_id:
            raise ValueError("requirement_id must not be blank")
        if not text:
            raise ValueError("requirement text must not be blank")
        if requirement_id in seen_ids:
            raise ValueError("requirement_id must be unique")

        seen_ids.add(requirement_id)
        normalized.append(
            {
                "requirement_id": requirement_id,
                "text": text,
            }
        )

    return normalized


def _failure_update(
    state: EstimationGraphState,
    *,
    code: str,
    message: str,
    event_type: str,
    summary: str,
    severity: IssueSeverity,
) -> EstimationGraphState:
    return {
        "requirements": [],
        "review_required": True,
        "errors": [
            {
                "code": code,
                "message": message,
                "node": "extract_requirements",
                "severity": severity,
            }
        ],
        "trace_events": [
            {
                "event_type": event_type,
                "node": "extract_requirements",
                "summary": summary,
                "evidence_refs": [],
                "state_delta_keys": [
                    "requirements",
                    "review_required",
                    "errors",
                    "execution_metadata",
                    "trace_events",
                ],
            }
        ],
        "execution_metadata": _execution_metadata(
            state,
            requirement_count=0,
        ),
    }


def build_extract_requirements_node(
    dependencies: GraphNodeDependencies,
) -> ExtractRequirementsNode:
    """Bind injected services to the requirement-extraction node."""

    async def extract_requirements(
        state: EstimationGraphState,
    ) -> EstimationGraphState:
        transcript = state.get("transcript")

        if not isinstance(transcript, str) or not transcript.strip():
            return _failure_update(
                state,
                code="missing_transcript",
                message="The graph state does not contain a valid transcript.",
                event_type="transcript_missing",
                summary="Requirement extraction could not start.",
                severity="error",
            )

        raw_requirements = (
            await dependencies.requirement_extractor.extract_requirements(
                transcript=transcript
            )
        )

        try:
            requirements = _normalize_requirements(raw_requirements)
        except (AttributeError, KeyError, TypeError, ValueError):
            return _failure_update(
                state,
                code="invalid_requirements",
                message=(
                    "Requirement extraction returned an invalid structured result."
                ),
                event_type="requirements_invalid",
                summary="Requirement extraction failed structured validation.",
                severity="error",
            )

        if not requirements:
            return _failure_update(
                state,
                code="no_requirements",
                message="No structured requirements were extracted.",
                event_type="requirements_missing",
                summary="Requirement extraction produced no requirements.",
                severity="warning",
            )

        requirement_ids = [
            requirement["requirement_id"]
            for requirement in requirements
        ]

        return {
            "requirements": requirements,
            "execution_metadata": _execution_metadata(
                state,
                requirement_count=len(requirements),
            ),
            "trace_events": [
                {
                    "event_type": "requirements_extracted",
                    "node": "extract_requirements",
                    "summary": (
                        f"Extracted {len(requirements)} structured requirements."
                    ),
                    "evidence_refs": requirement_ids,
                    "state_delta_keys": [
                        "requirements",
                        "execution_metadata",
                        "trace_events",
                    ],
                }
            ],
        }

    return extract_requirements
