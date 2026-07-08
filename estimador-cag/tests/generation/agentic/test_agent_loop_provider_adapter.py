from unittest.mock import patch

from app.generation.agentic.agent_loop import run_agent_loop
from app.generation.agentic.agent_schemas import AgentRunRequest


def test_agent_loop_uses_provider_adapter_for_planning():
    request = AgentRunRequest(
        transcript=(
            "Client needs JWT authentication, audit logging, admin dashboard, "
            "and CSV import for a financial back office."
        ),
        provider="fake",
        max_iterations=8,
    )

    with patch(
        "app.generation.agentic.agent_loop.build_provider_adapter"
    ) as build_adapter:
        from app.generation.agentic.provider_adapters import FakeProviderAdapter

        build_adapter.return_value = FakeProviderAdapter()

        result = run_agent_loop(request)

    build_adapter.assert_called_once_with("fake")
    assert result.terminated is True
    assert result.validation is not None
    assert result.validation.valid is True
