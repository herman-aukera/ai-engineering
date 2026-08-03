"""Session 13 Plus S2: semantic complexity classification before structure extraction."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.types import Command

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.schemas.v3_routing import ComplexitySignals
from app.services.v3_complexity_router import (
    assess_complexity,
    build_model_routing_plan,
)
from app.services.v3_semantic_classifier import (
    FakeSemanticClassifier,
    SemanticClassifier,
    arbitrate_classification,
)

SemanticDestination = Literal["structure_phase", "structure_core"]
SemanticClassifyNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[Command],
]

NODE_NAME = "semantic_classify"


def _effective_transcript(state: ReviewedEstimationGraphState) -> str:
    """Return the reformulated brief when available, otherwise the raw transcript."""
    reformulated = state.get("reformulated_request")
    if isinstance(reformulated, str) and reformulated.strip():
        return reformulated.strip()
    transcript = state.get("transcript")
    if isinstance(transcript, str) and transcript.strip():
        return transcript.strip()
    return ""


def _effective_destination(
    state: ReviewedEstimationGraphState,
    configured: SemanticDestination,
) -> SemanticDestination:
    """Preserve V2 routing while targeting the nested unified structure node."""

    if state.get("unified_graph_version"):
        return "structure_core"
    return configured


def _estimate_signals(transcript: str) -> ComplexitySignals:
    """Derive deterministic signals from the transcript for the complexity baseline."""
    lines = transcript.split("\n")
    char_count = len(transcript)
    return ComplexitySignals(
        requirement_count=min(500, max(0, len(lines) // 2)),
        integration_count=min(100, transcript.lower().count("integrat")),
        non_functional_requirement_count=(
            1
            if any(
                word in transcript.lower()
                for word in (
                    "secure",
                    "security",
                    "complian",
                    "scale",
                    "perform",
                )
            )
            else 0
        ),
        ambiguous_requirement_count=(
            1
            if any(
                word in transcript.lower()
                for word in ("maybe", "perhaps", "might", "possibly")
            )
            else 0
        ),
        transcript_chars=char_count,
        compliance_or_security_critical=any(
            word in transcript.lower()
            for word in ("complian", "security", "pci", "hipaa", "gdpr")
        ),
        data_migration_required="migrat" in transcript.lower(),
    )


def build_semantic_classify_node(
    classifier: SemanticClassifier | None = None,
    *,
    destination: SemanticDestination = "structure_phase",
) -> SemanticClassifyNode:
    """Build semantic classification with a graph-compatible destination.

    The configured default preserves the reviewed Session 13 Plus topology.
    Unified state resolves to ``structure_core`` so nested execution cannot
    write to an unknown channel.
    """

    resolved = classifier if classifier is not None else FakeSemanticClassifier()

    async def semantic_classify(
        state: ReviewedEstimationGraphState,
    ) -> Command:
        next_node = _effective_destination(state, destination)
        transcript = _effective_transcript(state)
        if not transcript:
            return Command(
                update={
                    "review_required": True,
                    "errors": [
                        {
                            "code": "missing_transcript_for_classification",
                            "message": (
                                "No transcript or reformulated request is available "
                                "for semantic classification."
                            ),
                            "node": NODE_NAME,
                            "severity": "error",
                        }
                    ],
                    "trace_events": [
                        {
                            "event_type": "semantic_classification_failed",
                            "node": NODE_NAME,
                            "summary": (
                                "Semantic classification could not start — no transcript."
                            ),
                            "evidence_refs": [],
                            "state_delta_keys": [
                                "review_required",
                                "errors",
                                "trace_events",
                            ],
                        }
                    ],
                },
                goto=next_node,
            )

        semantic_assessment = resolved.classify(transcript)
        semantic_dict = semantic_assessment.model_dump(mode="json")

        signals = _estimate_signals(transcript)
        deterministic = assess_complexity(signals, detected_languages=["en"])
        deterministic_dict = deterministic.model_dump(mode="json")

        arbitrated = arbitrate_classification(
            deterministic=deterministic,
            semantic=semantic_assessment,
        )
        arbitrated_dict = arbitrated.model_dump(mode="json")

        route_plan = build_model_routing_plan(
            deterministic,
            authoritative_level=arbitrated.arbitrated_level,
        )
        route_plan_dict = route_plan.model_dump(mode="json")

        return Command(
            update={
                "semantic_assessment": semantic_dict,
                "v3_complexity": deterministic_dict,
                "arbitrated_assessment": arbitrated_dict,
                "v3_route_plan": route_plan_dict,
                "trace_events": [
                    {
                        "event_type": "semantic_classification_completed",
                        "node": NODE_NAME,
                        "summary": (
                            f"Semantic: {semantic_assessment.level}, "
                            f"Deterministic: {deterministic.level}, "
                            f"Arbitrated: {arbitrated.arbitrated_level} "
                            f"({arbitrated.resolution})"
                        ),
                        "evidence_refs": [
                            semantic_assessment.classifier_version,
                            deterministic.classifier_version,
                        ],
                        "state_delta_keys": [
                            "semantic_assessment",
                            "v3_complexity",
                            "arbitrated_assessment",
                            "v3_route_plan",
                            "trace_events",
                        ],
                    }
                ],
            },
            goto=next_node,
        )

    return semantic_classify
