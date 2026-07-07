"""
Session 12 hand-written fake-provider agent loop.

This module proves the reason-act-observe mechanics before live provider
adapters are introduced.
"""

from __future__ import annotations

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


def run_agent_loop(request: AgentRunRequest) -> AgentRunResult:
    """
    Run a deterministic fake-provider manual loop.

    Live providers will be added behind the same contract in a later slice.
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
                output = search_budgets(SearchBudgetsInput(**arguments))
                _append_tool_output(trace, call_id, output.model_dump())
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
