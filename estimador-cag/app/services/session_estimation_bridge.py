"""Bridge the conversational session product to legacy or graph estimation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.config import EstimationBackend, TierName
from app.schemas.estimation import EstimationRequest
from app.services.estimation_dispatcher import dispatch_estimation
from app.services.graph_estimation import GraphEstimationApplication
from app.services.graph_product_adapter import adapt_graph_run_to_product_response

LegacyEstimator = Callable[..., dict[str, Any]]


class GraphBackendUnavailableError(RuntimeError):
    """Raised when graph mode is selected but its lifespan service is absent."""


class GraphBackendExecutionError(RuntimeError):
    """Raised when the selected graph service fails during execution."""


def build_graph_transcript(*, transcript: str, attachments_text: str) -> str:
    """Add extracted attachment context without moving ownership from the route."""

    normalized_attachments = attachments_text.strip()
    if not normalized_attachments:
        return transcript

    return f"{transcript}\n\nAttachment context:\n{normalized_attachments}"


async def execute_session_estimation(
    *,
    backend: EstimationBackend,
    legacy_estimator: LegacyEstimator,
    graph_service: GraphEstimationApplication | None,
    request: EstimationRequest,
    transcript: str,
    tier: TierName | None,
    prompt_version: str,
    project_metadata: object,
    attachments_text: str,
    conversation_history: list[dict[str, str]],
) -> dict[str, Any]:
    """Select one backend while preserving each backend's native contract."""

    async def legacy_operation() -> dict[str, Any]:
        return legacy_estimator(
            request,
            tier=tier,
            prompt_version=prompt_version,
            project_metadata=project_metadata,
            attachments_text=attachments_text,
            conversation_history=conversation_history,
        )

    async def graph_operation() -> dict[str, Any]:
        if graph_service is None:
            raise GraphBackendUnavailableError(
                "Estimation graph service is not available."
            )

        try:
            run = await graph_service.estimate(
                transcript=build_graph_transcript(
                    transcript=transcript,
                    attachments_text=attachments_text,
                )
            )
        except Exception as exc:
            raise GraphBackendExecutionError(
                "Graph estimation execution failed."
            ) from exc

        return adapt_graph_run_to_product_response(
            run,
            requested_prompt_version=prompt_version,
            requested_tier=tier,
        )

    return await dispatch_estimation(
        backend=backend,
        legacy_operation=legacy_operation,
        graph_operation=graph_operation,
    )
