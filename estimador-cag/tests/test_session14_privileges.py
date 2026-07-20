from __future__ import annotations

from types import MappingProxyType
from typing import get_args

import pytest

from app.services.session14_privileges import (
    AGENT_TOOL_PRIVILEGES,
    BusinessTool,
    allowed_tools_for,
    assert_tool_allowed,
)

EXPECTED_PRIVILEGES = {
    "supervisor": frozenset(),
    "requirements_extractor": frozenset(),
    "budget_searcher": frozenset({"search_budgets"}),
    "estimate_generator": frozenset({"calculate_estimate"}),
    "coherence_validator": frozenset({"validate_estimate"}),
    "human_review_gate": frozenset(),
    "finalize": frozenset(),
}


def test_business_tool_allowlist_is_closed_and_exact() -> None:
    assert set(get_args(BusinessTool)) == {
        "search_budgets",
        "calculate_estimate",
        "validate_estimate",
    }


def test_privilege_registry_is_complete_and_immutable() -> None:
    assert isinstance(AGENT_TOOL_PRIVILEGES, MappingProxyType)
    assert dict(AGENT_TOOL_PRIVILEGES) == EXPECTED_PRIVILEGES
    assert all(
        isinstance(tools, frozenset)
        for tools in AGENT_TOOL_PRIVILEGES.values()
    )

    with pytest.raises(TypeError):
        AGENT_TOOL_PRIVILEGES["supervisor"] = frozenset(
            {"search_budgets"}
        )


@pytest.mark.parametrize(
    ("agent_id", "expected_tools"),
    list(EXPECTED_PRIVILEGES.items()),
)
def test_each_agent_receives_only_its_declared_tools(
    agent_id: str,
    expected_tools: frozenset[str],
) -> None:
    assert allowed_tools_for(agent_id) == expected_tools


@pytest.mark.parametrize(
    ("agent_id", "tool"),
    [
        pytest.param(
            "supervisor",
            "search_budgets",
            id="supervisor-cannot-search",
        ),
        pytest.param(
            "requirements_extractor",
            "calculate_estimate",
            id="extractor-cannot-calculate",
        ),
        pytest.param(
            "budget_searcher",
            "validate_estimate",
            id="searcher-cannot-validate",
        ),
        pytest.param(
            "estimate_generator",
            "search_budgets",
            id="generator-cannot-search",
        ),
        pytest.param(
            "coherence_validator",
            "calculate_estimate",
            id="validator-cannot-calculate",
        ),
    ],
)
def test_runtime_guard_rejects_cross_agent_tool_access(
    agent_id: str,
    tool: str,
) -> None:
    with pytest.raises(PermissionError, match=agent_id):
        assert_tool_allowed(agent_id, tool)


def test_runtime_guard_accepts_declared_tool_and_rejects_unknown_agent() -> None:
    assert_tool_allowed("budget_searcher", "search_budgets")

    with pytest.raises(ValueError, match="unknown Session 14 agent"):
        allowed_tools_for("rogue_agent")
