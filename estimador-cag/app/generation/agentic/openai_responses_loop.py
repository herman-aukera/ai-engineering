"""
Exact OpenAI Responses API loop for Session 12.

This module implements the assignment-specific manual loop:

1. client.responses.create(...)
2. inspect function_call items
3. execute local tools
4. return function_call_output items with matching call_id
5. continue with previous_response_id
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, cast

from app.generation.agentic.agent_schemas import (
    AgentRunRequest,
    AgentRunResult,
    AgentTraceItem,
    CalculateEstimateInput,
    CalculateEstimateOutput,
    SearchBudgetsInput,
    ToolName,
    ValidateEstimateInput,
    ValidateEstimateOutput,
)
from app.generation.agentic.agent_tools import (
    calculate_estimate,
    search_budgets,
    validate_estimate,
)
from app.generation.agentic.retrieval_bridge import (
    SemanticSearchLike,
    search_budgets_with_service,
)


def build_responses_tool_schemas() -> list[dict[str, Any]]:
    """Return flat Responses API function tool schemas with strict mode enabled."""

    return [
        {
            "type": "function",
            "name": "search_budgets",
            "description": (
                "Recover historical budget references for one concrete component "
                "or requirement from the meeting transcript. Use one call per "
                "meaningfully separate component."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for one component or requirement.",
                    },
                    "filters": {
                        "type": ["object", "null"],
                        "description": "Optional metadata filters for the retrieval pipeline.",
                        "properties": {
                            "component_type": {"type": ["string", "null"]},
                            "date_range": {"type": ["string", "null"]},
                            "client_sector": {"type": ["string", "null"]},
                            "client_country": {"type": ["string", "null"]},
                            "main_technology": {"type": ["string", "null"]},
                            "complexity": {"type": ["string", "null"]},
                            "year": {"type": ["number", "null"]},
                            "budget_id": {"type": ["string", "null"]},
                            "component_id": {"type": ["string", "null"]},
                        },
                        "required": [
                            "component_type",
                            "date_range",
                            "client_sector",
                            "client_country",
                            "main_technology",
                            "complexity",
                            "year",
                            "budget_id",
                            "component_id",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": ["query", "filters"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        {
            "type": "function",
            "name": "calculate_estimate",
            "description": (
                "Calculate a deterministic partial or consolidated estimate from "
                "components and their reference hours. This tool never calls an LLM."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "components": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "complexity": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high"],
                                },
                                "reference_hours": {"type": "number"},
                            },
                            "required": ["name", "complexity", "reference_hours"],
                            "additionalProperties": False,
                        },
                    },
                    "hourly_rate_eur": {"type": "number"},
                    "contingency_pct": {"type": "number"},
                },
                "required": ["components", "hourly_rate_eur", "contingency_pct"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        {
            "type": "function",
            "name": "validate_estimate",
            "description": (
                "Validate the final estimate before returning it. Use this as the "
                "last tool call to detect missing components, incoherent totals, "
                "or suspicious guardrail failures."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "required_component_names": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                "required": ["required_component_names"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    ]


def build_responses_agent_instructions() -> str:
    """Return the system instructions for the Responses API agent."""

    return (
        "You are a senior software estimation agent. "
        "Decompose the meeting transcript into separately estimable components. "
        "For each meaningful component, call search_budgets with a focused query. "
        "After collecting references, call calculate_estimate with all components. "
        "Before final output, call validate_estimate. "
        "Use the tools rather than inventing tool results. "
        "Stop when a structured estimate has been calculated and validated."
    )


def _get(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _response_output(response: Any) -> list[Any]:
    output = _get(response, "output", [])
    return list(output or [])


def _item_type(item: Any) -> str | None:
    return _get(item, "type")


def _response_id(response: Any) -> str:
    response_id = _get(response, "id")
    if not response_id:
        raise ValueError("Responses API response is missing id")
    return str(response_id)


def _response_output_text(response: Any) -> str:
    return str(_get(response, "output_text", "") or "")


def _parse_arguments(raw_arguments: Any) -> dict[str, Any]:
    if raw_arguments is None:
        return {}
    if isinstance(raw_arguments, dict):
        return dict(raw_arguments)
    if isinstance(raw_arguments, str):
        parsed = json.loads(raw_arguments or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("function_call arguments must decode to an object")
        return parsed
    raise ValueError("function_call arguments must be a JSON string or object")


def _normalize_search_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Remove nullable strict-schema filter placeholders before Pydantic validation."""

    normalized = dict(arguments)
    filters = normalized.get("filters")
    if isinstance(filters, dict):
        compact_filters = {key: value for key, value in filters.items() if value is not None}
        normalized["filters"] = compact_filters or None
    return normalized


def _reasoning_summary(item: Any) -> str:
    summary = _get(item, "summary")
    if isinstance(summary, Sequence) and not isinstance(summary, str):
        parts: list[str] = []
        for part in summary:
            text = _get(part, "text")
            if text:
                parts.append(str(text))
        if parts:
            return " ".join(parts)

    content = _get(item, "content")
    if content:
        return str(content)

    return "Model reasoning step."


def _final_message(response: Any) -> str:
    output_text = _response_output_text(response)
    if output_text:
        return output_text

    for item in _response_output(response):
        content = _get(item, "content")
        if isinstance(content, Sequence) and not isinstance(content, str):
            parts = [str(_get(part, "text", "")) for part in content]
            joined = " ".join(part for part in parts if part)
            if joined:
                return joined

    return "Model returned final response without more tool calls."


async def _execute_tool(
    *,
    tool_name: ToolName,
    arguments: dict[str, Any],
    retrieval_service: SemanticSearchLike | None,
    estimate: CalculateEstimateOutput | None,
) -> tuple[dict[str, Any], CalculateEstimateOutput | None, ValidateEstimateOutput | None]:
    if tool_name == "search_budgets":
        payload = SearchBudgetsInput(**_normalize_search_arguments(arguments))
        if retrieval_service is None:
            output = search_budgets(payload)
        else:
            output = await search_budgets_with_service(payload, service=retrieval_service)
        return output.model_dump(), estimate, None

    if tool_name == "calculate_estimate":
        calculated = calculate_estimate(CalculateEstimateInput(**arguments))
        return calculated.model_dump(), calculated, None

    if tool_name == "validate_estimate":
        if estimate is None:
            raise ValueError("validate_estimate cannot run before calculate_estimate")
        validation_arguments = dict(arguments)
        validation_arguments["estimate"] = estimate.model_dump()
        validation = validate_estimate(ValidateEstimateInput(**validation_arguments))
        return validation.model_dump(), estimate, validation

    raise ValueError(f"Unsupported tool: {tool_name}")


async def run_openai_responses_agent(
    request: AgentRunRequest,
    *,
    client: Any,
    model: str = "gpt-5",
    retrieval_service: SemanticSearchLike | None = None,
    reasoning_effort: str = "medium",
) -> AgentRunResult:
    """Run the exact manual Responses API tool loop."""

    tools = build_responses_tool_schemas()
    trace: list[AgentTraceItem] = []
    estimate: CalculateEstimateOutput | None = None
    validation: ValidateEstimateOutput | None = None

    response = client.responses.create(
        model=request.model or model,
        instructions=build_responses_agent_instructions(),
        input=request.transcript,
        tools=tools,
        reasoning={"effort": reasoning_effort},
    )

    iterations = 0

    while True:
        iterations += 1
        if iterations > request.max_iterations:
            raise RuntimeError("OpenAI Responses agent exceeded max_iterations")

        function_outputs: list[dict[str, str]] = []
        function_call_count = 0

        for item in _response_output(response):
            item_type = _item_type(item)

            if item_type == "reasoning":
                trace.append(
                    AgentTraceItem(
                        role="reasoning",
                        content=_reasoning_summary(item),
                    )
                )
                continue

            if item_type != "function_call":
                continue

            function_call_count += 1
            tool_name = cast(ToolName, str(_get(item, "name")))
            call_id = str(_get(item, "call_id"))
            arguments = _parse_arguments(_get(item, "arguments"))

            trace.append(
                AgentTraceItem(
                    role="function_call",
                    content=f"Call {tool_name}.",
                    tool_name=tool_name,
                    call_id=call_id,
                    arguments=arguments,
                )
            )

            output, estimate, maybe_validation = await _execute_tool(
                tool_name=tool_name,
                arguments=arguments,
                retrieval_service=retrieval_service,
                estimate=estimate,
            )
            if maybe_validation is not None:
                validation = maybe_validation

            trace.append(
                AgentTraceItem(
                    role="function_call_output",
                    content=f"Observed output for {call_id}.",
                    call_id=call_id,
                    output=output,
                )
            )

            function_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(output),
                }
            )

        if function_call_count == 0:
            if estimate is None:
                raise RuntimeError("OpenAI Responses agent terminated without estimate")

            trace.append(
                AgentTraceItem(
                    role="final",
                    content=_final_message(response),
                )
            )

            return AgentRunResult(
                estimate=estimate,
                validation=validation,
                trace=trace,
                provider="openai-responses",
                model=request.model or model,
                terminated=True,
            )

        response = client.responses.create(
            model=request.model or model,
            previous_response_id=_response_id(response),
            input=function_outputs,
            tools=tools,
            reasoning={"effort": reasoning_effort},
        )
