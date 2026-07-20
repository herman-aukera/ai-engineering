"""Session 13 Plus S2: semantic complexity classification before structure extraction."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from app.generation.graph.review_state import ReviewedEstimationGraphState
from app.schemas.v3_routing import ComplexitySignals
from app.services.v3_complexity_router import (
    assess_complexity,
    build_model_routing_plan,
)
from app.services.v3_semantic_classifier import (
    FakeSemanticClassifier,
    arbitrate_classification,
)

SemanticClassifyNode = Callable[
    [ReviewedEstimationGraphState],
    Awaitable[ReviewedEstimationGraphState],
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


def _estimate_signals(transcript: str) -> ComplexitySignals:
    """Derive deterministic signals from the transcript for the complexity baseline."""
    lines = transcript.split("\n")
    char_count = len(transcript)
    return ComplexitySignals(
        requirement_count=min(500, max(0, len(lines) // 2)),
        integration_count=min(100, transcript.lower().count("integrat")),
        non_functional_requirement_count=(
            1 if any(word in transcript.lower() for word in ("secure", "security", "complian", "scale", "perform"))
            else 0
        ),
        ambiguous_requirement_count=(
            1 if any(word in transcript.lower() for word in ("maybe", "perhaps", "might", "possibly"))
            else 0
        ),
        transcript_chars=char_count,
        compliance_or_security_critical=any(
            word in transcript.lower() for word in ("complian", "security", "pci", "hipaa", "gdpr")
        ),
        data_migration_required="migrat" in transcript.lower(),
    )


def build_semantic_classify_node() -> SemanticClassifyNode:
    """Build a node that classifies complexity and stores assessments in state.

    The node uses the deterministic :class:`FakeSemanticClassifier` by default.
    When a real LLM classifier is wired in (S3+), the node signature stays the
    same — only the injected classifier changes.
    """

    classifier = FakeSemanticClassifier()

    async def semantic_classify(
        state: ReviewedEstimationGraphState,
    ) -> ReviewedEstimationGraphState:
        transcript = _effective_transcript(state)
        if not transcript:
            return cast(
                ReviewedEstimationGraphState,
                {
                    "review_required": True,
                    "errors": [
                        {
                            "code": "missing_transcript_for_classification",
                            "message": "No transcript or reformulated request is available for semantic classification.",
                            "node": NODE_NAME,
                            "severity": "error",
                        }
                    ],
                    "trace_events": [
                        {
                            "event_type": "semantic_classification_failed",
                            "node": NODE_NAME,
                            "summary": "Semantic classification could not start — no transcript.",
                            "evidence_refs": [],
                            "state_delta_keys": ["review_required", "errors", "trace_events"],
                        }
                    ],
                },
            )

        # 1. Semantic (fake) classifier
        semantic_assessment = classifier.classify(transcript)
        semantic_dict = semantic_assessment.model_dump(mode="json")

        # 2. Deterministic baseline
        signals = _estimate_signals(transcript)
        deterministic = assess_complexity(signals, detected_languages=["en"])
        deterministic_dict = deterministic.model_dump(mode="json")

        # 3. Arbitration
        arbitrated = arbitrate_classification(
            deterministic=deterministic,
            semantic=semantic_assessment,
        )
        arbitrated_dict = arbitrated.model_dump(mode="json")

        # 4. Route plan from the arbitrated level
        route_plan = build_model_routing_plan(deterministic)
        route_plan_dict = route_plan.model_dump(mode="json")

        return cast(
            ReviewedEstimationGraphState,
            {
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
        )

    return semantic_classify
