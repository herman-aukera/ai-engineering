"""Adapt terminal graph runs to public and session-product response shapes.

The graph and legacy estimators do not expose semantically identical results.
This adapter preserves graph evidence and provides a deterministic text fallback
without fabricating legacy phases, duration, or confidence fields.
"""

from __future__ import annotations

from app.schemas.graph_estimation import GraphEstimationResponse
from app.services.graph_estimation import GraphEstimationRun


def graph_response_from_run(run: GraphEstimationRun) -> GraphEstimationResponse:
    """Validate one terminal graph run against the public graph contract."""

    state = run.state
    human_review = run.interrupts[0] if run.interrupts else None
    status = (
        "awaiting_human_review"
        if run.execution_status == "awaiting_human_review"
        else state.get("status")
    )
    return GraphEstimationResponse.model_validate(
        {
            "estimation_id": run.estimation_id,
            "thread_id": run.thread_id,
            "graph_version": state.get("graph_version"),
            "status": status,
            "review_required": state.get("review_required"),
            "estimate": state.get("estimate"),
            "requirements": state.get("requirements", []),
            "components": state.get("components", []),
            "budget_matches": state.get("budget_matches", []),
            "component_estimates": state.get("component_estimates", []),
            "errors": state.get("errors", []),
            "trace_events": state.get("trace_events", []),
            "route_events": state.get("route_events", []),
            "agent_contributions": state.get(
                "agent_contributions",
                [],
            ),
            "revision": state.get("human_review_revision", 0),
            "human_review_status": state.get("human_review_status"),
            "human_review_reason_codes": state.get(
                "human_review_reason_codes",
                [],
            ),
            "human_review": human_review,
            "provider_metadata": state.get("provider_metadata", {}),
            "execution_metadata": state.get("execution_metadata", {}),
        }
    )


def _display_number(value: float | None) -> str:
    if value is None:
        return "not available"
    return f"{value:g}"


def _render_graph_text(response: GraphEstimationResponse) -> str:
    estimate = response.estimate
    lines = [
        "## Graph estimate",
        "",
        f"- Status: {response.status}",
        f"- Review required: {'yes' if response.review_required else 'no'}",
        f"- Total hours: {_display_number(estimate.total_hours)}",
        f"- Total cost: EUR {_display_number(estimate.total_cost_eur)}",
        "",
        "### Components",
    ]

    if not estimate.components:
        lines.append("- No component estimates were produced.")
    else:
        for component in estimate.components:
            hours = _display_number(component.hours)
            confidence_pct = round(component.confidence * 100)
            lines.append(
                f"- {component.name}: {hours} hours "
                f"({component.grounding_status}, confidence {confidence_pct}%)"
            )

    if response.errors:
        lines.extend(["", "### Issues"])
        lines.extend(
            f"- [{issue.severity}] {issue.code}: {issue.message}"
            for issue in response.errors
        )

    return "\n".join(lines)


def adapt_graph_run_to_product_response(
    run: GraphEstimationRun,
    *,
    requested_prompt_version: str,
    requested_tier: str | None,
) -> dict[str, object]:
    """Return a session-compatible response while declaring partial parity."""

    graph_response = graph_response_from_run(run)
    provider_metadata = graph_response.provider_metadata

    return {
        "prompt_version": provider_metadata.prompt_version or "graph-managed",
        "requested_prompt_version": requested_prompt_version,
        "result": None,
        "text": _render_graph_text(graph_response),
        "cached": False,
        "cache_backend": None,
        "model": provider_metadata.model,
        "provider": provider_metadata.provider,
        "tier": None,
        "requested_tier": requested_tier,
        "served_tier": None,
        "fallback_used": False,
        "estimation_backend": "graph",
        "compatibility": {
            "mode": "graph_text_fallback",
            "parity": "partial",
            "legacy_structured_result": False,
            "reason": (
                "The graph exposes component hours and provenance, while the "
                "legacy product contract requires phases, duration, and confidence."
            ),
        },
        "graph_estimation": graph_response.model_dump(mode="json"),
    }
