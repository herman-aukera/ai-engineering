"""
Session 12 hand-written agent loop.

This module executes normalized provider-planned steps with deterministic tools
and optional injected retrieval.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from app.generation.agentic.agent_schemas import (
    AgentRunRequest,
    AgentRunResult,
    AgentTraceItem,
    CalculateEstimateInput,
    SearchBudgetsInput,
    ValidateEstimateInput,
)
from app.generation.agentic.agent_tools import calculate_estimate, search_budgets, validate_estimate
from app.generation.agentic.provider_adapters import (
    AgentPlannedStep,
    ProviderAdapterRequest,
    build_provider_adapter,
)
from app.generation.agentic.retrieval_bridge import SemanticSearchLike, search_budgets_with_service


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


async def execute_planned_steps_with_retrieval(
    request: AgentRunRequest,
    planned_steps: Sequence[AgentPlannedStep],
    *,
    search_service: SemanticSearchLike | None = None,
    search_k: int = 5,
) -> AgentRunResult:
    """
    Execute normalized planned steps with deterministic local tools.

    This is the bridge between provider planning and the actual tool loop. It is
    deterministic except for an optional injected retrieval service.
    """

    trace: list[AgentTraceItem] = []
    estimate = None
    validation = None
    iterations = 0

    for step in planned_steps:
        iterations += 1
        if iterations > request.max_iterations:
            break

        if step.kind == "reasoning":
            trace.append(
                AgentTraceItem(
                    role="reasoning",
                    content=step.content,
                )
            )
            continue

        if step.kind == "function_call":
            tool_name = step.tool_name
            call_id = step.call_id
            arguments = step.arguments

            trace.append(
                AgentTraceItem(
                    role="function_call",
                    content=step.content,
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

        if step.kind == "final":
            trace.append(
                AgentTraceItem(
                    role="final",
                    content=step.content,
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


async def run_agent_loop_with_retrieval(
    request: AgentRunRequest,
    *,
    search_service: SemanticSearchLike | None = None,
    search_k: int = 5,
) -> AgentRunResult:
    """
    Run the manual agent loop with optional injected retrieval.

    Provider adapters plan normalized steps. The loop validates and executes
    tools, preserving the trace contract.
    """

    adapter = build_provider_adapter(request.provider)
    planned_steps = adapter.plan(
        ProviderAdapterRequest(
            transcript=request.transcript,
            provider=request.provider,
            model=request.model,
        )
    )

    return await execute_planned_steps_with_retrieval(
        request,
        planned_steps,
        search_service=search_service,
        search_k=search_k,
    )


def run_agent_loop(request: AgentRunRequest) -> AgentRunResult:
    """
    Run the deterministic fake-provider manual loop.

    This synchronous compatibility wrapper intentionally uses no retrieval
    service, so existing CI and trace artifacts stay stable.
    """

    return asyncio.run(run_agent_loop_with_retrieval(request))
