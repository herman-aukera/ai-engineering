from app.generation.agentic.provider_adapters import (
    AgentPlannedStep,
    FakeProviderAdapter,
    ProviderAdapterRequest,
    build_provider_adapter,
)


def test_fake_provider_adapter_returns_normalized_agent_steps():
    adapter = FakeProviderAdapter()
    request = ProviderAdapterRequest(
        transcript=(
            "Client needs JWT authentication, audit logging, admin dashboard, "
            "and CSV import."
        ),
        provider="fake",
        model=None,
    )

    steps = adapter.plan(request)

    assert steps[0].kind == "reasoning"
    assert steps[-1].kind == "final"

    tool_steps = [step for step in steps if step.kind == "function_call"]
    assert [step.tool_name for step in tool_steps] == [
        "search_budgets",
        "search_budgets",
        "calculate_estimate",
        "validate_estimate",
    ]

    assert all(step.call_id for step in tool_steps)
    assert tool_steps[0].arguments == {"query": "JWT authentication financial backend"}


def test_build_provider_adapter_supports_fake_only_before_live_smoke():
    adapter = build_provider_adapter("fake")

    assert isinstance(adapter, FakeProviderAdapter)

    try:
        build_provider_adapter("deepseek")
    except ValueError as exc:
        assert "not implemented yet" in str(exc)
    else:
        raise AssertionError("DeepSeek adapter must stay disabled until live smoke slice")


def test_agent_planned_step_requires_tool_name_for_function_call():
    try:
        AgentPlannedStep(
            kind="function_call",
            content="Call something.",
            call_id="call_missing_tool",
            arguments={},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("function_call without tool_name must fail")
