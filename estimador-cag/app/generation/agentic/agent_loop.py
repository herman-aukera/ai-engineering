"""
Session 12 hand-written fake-provider agent loop.

This module proves the reason-act-observe mechanics before live provider
adapters are introduced.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.generation.agentic.agent_schemas import (
    AgentRunRequest,
    AgentRunResult,
    AgentTraceItem,
    CalculateEstimateInput,
    EstimateComponentInput,
    SearchBudgetsInput,
    ValidateEstimateInput,
)
from app.generation.agentic.agent_tools import calculate_estimate, search_budgets, validate_estimate
from app.generation.agentic.retrieval_bridge import SemanticSearchLike, search_budgets_with_service


def _fake_plan(transcript: str) -> list[dict[str, Any]]:
    """Return a deterministic fake provider plan for Session 12 loop tests."""

    lowered = transcript.lower()
    components = []

    if "jwt" in lowered or "authentication" in lowered:
        components.append(
            EstimateComponentInput(
                name="JWT authentication",
                complexity="medium",
                reference_hours=40,
            )
        )

    if "audit" in lowered:
        components.append(
            EstimateComponentInput(
                name="Audit logging",
                complexity="low",
                reference_hours=24,
            )
        )

    if "dashboard" in lowered or "admin" in lowered:
        components.append(
            EstimateComponentInput(
                name="Admin dashboard",
                complexity="medium",
                reference_hours=56,
            )
        )

    if "csv" in lowered or "import" in lowered:
        components.append(
            EstimateComponentInput(
                name="CSV import",
                complexity="medium",
                reference_hours=32,
            )
        )

    if not components:
        components.append(
            EstimateComponentInput(
                name="General implementation",
                complexity="medium",
                reference_hours=40,
            )
        )

    return [
        {
            "kind": "reasoning",
            "content": "Identify likely components from the transcript before estimating.",
        },
        {
            "kind": "function_call",
            "tool_name": "search_budgets",
            "call_id": "call_search_auth",
            "arguments": {"query": "JWT authentication financial backend"},
        },
        {
            "kind": "function_call",
            "tool_name": "search_budgets",
            "call_id": "call_search_audit",
            "arguments": {"query": "audit logging admin dashboard CSV import"},
        },
        {
            "kind": "reasoning",
            "content": "Use retrieved budget context plus transcript components to calculate effort.",
        },
        {
            "kind": "function_call",
            "tool_name": "calculate_estimate",
            "call_id": "call_calculate_estimate",
            "arguments": {
                "components": [component.model_dump() for component in components],
                "hourly_rate_eur": 75,
                "contingency_pct": 0.2,
            },
        },
        {
            "kind": "function_call",
            "tool_name": "validate_estimate",
            "call_id": "call_validate_estimate",
            "arguments": {
                "required_component_names": [component.name for component in components],
            },
        },
        {
            "kind": "final",
            "content": "Return the structured estimate and readable trace.",
        },
    ]


def _append_tool_output(
    trace: list[AgentTraceItem],
    call_id: str,
    output: dict[str, Any],
) -> None:
    trace.append(
        AgentTraceItem(
            role="function_call_output",
            content=f"Observed output for {call_id}.",
            call_id=call_id,
            output=output,
        )
    )


async def _execute_search_budgets(
    arguments: dict[str, Any],
    *,
    search_service: SemanticSearchLike | None,
    search_k: int,
) -> dict[str, Any]:
    """Execute search_budgets with retrieval service when injected."""

    payload = SearchBudgetsInput(**arguments)
    if search_service is None:
        return search_budgets(payload).model_dump()

    return (
        await search_budgets_with_service(
            payload,
            service=search_service,
            k=search_k,
        )
    ).model_dump()


async def run_agent_loop_with_retrieval(
    request: AgentRunRequest,
    *,
    search_service: SemanticSearchLike | None = None,
    search_k: int = 5,
) -> AgentRunResult:
    """
    Run the manual agent loop with optional injected retrieval.

    With no search_service, this preserves the deterministic fake shell behavior.
    With search_service, search_budgets observations contain semantic hits.
    """

    if request.provider != "fake":
        raise ValueError("Only fake provider is supported in this slice.")

    trace: list[AgentTraceItem] = []
    estimate = None
    validation = None
    iterations = 0

    for step in _fake_plan(request.transcript):
        iterations += 1
        if iterations > request.max_iterations:
            break

        kind = step["kind"]

        if kind == "reasoning":
            trace.append(
                AgentTraceItem(
                    role="reasoning",
                    content=step["content"],
                )
            )
            continue

        if kind == "function_call":
            tool_name = step["tool_name"]
            call_id = step["call_id"]
            arguments = step["arguments"]

            trace.append(
                AgentTraceItem(
                    role="function_call",
                    content=f"Call {tool_name}.",
                    tool_name=tool_name,
                    call_id=call_id,
                    arguments=arguments,
                )
            )

            if tool_name == "search_budgets":
                output = await _execute_search_budgets(
                    arguments,
                    search_service=search_service,
                    search_k=search_k,
                )
                _append_tool_output(trace, call_id, output)
                continue

            if tool_name == "calculate_estimate":
                estimate = calculate_estimate(CalculateEstimateInput(**arguments))
                _append_tool_output(trace, call_id, estimate.model_dump())
                continue

            if tool_name == "validate_estimate":
                if estimate is None:
                    raise ValueError("validate_estimate cannot run before calculate_estimate")

                validation_arguments = dict(arguments)
                validation_arguments["estimate"] = estimate
                validation = validate_estimate(ValidateEstimateInput(**validation_arguments))
                _append_tool_output(trace, call_id, validation.model_dump())
                continue

            raise ValueError(f"Unsupported tool: {tool_name}")

        if kind == "final":
            trace.append(
                AgentTraceItem(
                    role="final",
                    content=step["content"],
                )
            )
            break

    if estimate is None:
        raise ValueError("Agent loop terminated without an estimate.")

    return AgentRunResult(
        estimate=estimate,
        validation=validation,
        trace=trace,
        provider=request.provider,
        model=request.model,
        terminated=bool(trace and trace[-1].role == "final"),
    )


def run_agent_loop(request: AgentRunRequest) -> AgentRunResult:
    """
    Run the deterministic fake-provider manual loop.

    This synchronous compatibility wrapper intentionally uses no retrieval
    service, so existing CI and trace artifacts stay stable.
    """

    return asyncio.run(run_agent_loop_with_retrieval(request))
