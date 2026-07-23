from app.generation.agentic.agent_loop import run_agent_loop
from app.generation.agentic.agent_schemas import AgentRunRequest


def test_fake_provider_agent_loop_runs_reason_act_observe_until_final():
    request = AgentRunRequest(
        transcript=(
            "Client needs a web SaaS for a financial back office. "
            "The scope includes JWT authentication, audit logging, "
            "admin dashboard, and CSV import."
        ),
        provider="fake",
        max_iterations=8,
    )

    result = run_agent_loop(request)

    assert result.provider == "fake"
    assert result.terminated is True
    assert result.validation is not None
    assert result.validation.valid is True
    assert result.estimate.total_hours > 0

    roles = [item.role for item in result.trace]
    assert "reasoning" in roles
    assert "function_call" in roles
    assert "function_call_output" in roles
    assert roles[-1] == "final"

    tool_calls = [item for item in result.trace if item.role == "function_call"]
    tool_outputs = [item for item in result.trace if item.role == "function_call_output"]

    assert [item.tool_name for item in tool_calls].count("search_budgets") >= 2
    assert [item.tool_name for item in tool_calls].count("calculate_estimate") == 1
    assert [item.tool_name for item in tool_calls].count("validate_estimate") == 1

    call_ids = {item.call_id for item in tool_calls}
    output_call_ids = {item.call_id for item in tool_outputs}
    assert call_ids == output_call_ids
