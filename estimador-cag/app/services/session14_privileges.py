from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, Literal

from app.generation.graph.review_state import Session14AgentId

BusinessTool = Literal[
    "search_budgets",
    "calculate_estimate",
    "validate_estimate",
]

AGENT_TOOL_PRIVILEGES: Final[
    Mapping[Session14AgentId, frozenset[BusinessTool]]
] = MappingProxyType(
    {
        "supervisor": frozenset(),
        "requirements_extractor": frozenset(),
        "budget_searcher": frozenset({"search_budgets"}),
        "estimate_generator": frozenset({"calculate_estimate"}),
        "coherence_validator": frozenset({"validate_estimate"}),
        "human_review_gate": frozenset(),
        "finalize": frozenset(),
    }
)


def allowed_tools_for(
    agent_id: Session14AgentId,
) -> frozenset[BusinessTool]:
    """Return the immutable server-owned tool allowlist for one agent."""

    try:
        return AGENT_TOOL_PRIVILEGES[agent_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown Session 14 agent: {agent_id}"
        ) from exc


def assert_tool_allowed(
    agent_id: Session14AgentId,
    tool: BusinessTool,
) -> None:
    """Fail closed when an agent requests an undeclared business tool."""

    if tool not in allowed_tools_for(agent_id):
        raise PermissionError(
            f"{agent_id} is not allowed to use {tool}"
        )
