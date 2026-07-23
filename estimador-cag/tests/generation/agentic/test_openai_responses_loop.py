import asyncio
import json
from types import SimpleNamespace

from app.generation.agentic.agent_schemas import AgentRunRequest
from app.generation.agentic.openai_responses_loop import (
    build_responses_tool_schemas,
    run_openai_responses_agent,
)


class FakeResponsesClient:
    def __init__(self):
        self.calls = []
        self.responses = [
            SimpleNamespace(
                id="resp_1",
                output=[
                    SimpleNamespace(
                        type="reasoning",
                        summary=[SimpleNamespace(text="Split the transcript into separate budget searches.")],
                    ),
                    SimpleNamespace(
                        type="function_call",
                        call_id="call_search_auth",
                        name="search_budgets",
                        arguments=json.dumps({"query": "JWT authentication financial backend"}),
                    ),
                    SimpleNamespace(
                        type="function_call",
                        call_id="call_search_audit",
                        name="search_budgets",
                        arguments=json.dumps({"query": "audit logging admin dashboard CSV import"}),
                    ),
                ],
                output_text="",
            ),
            SimpleNamespace(
                id="resp_2",
                output=[
                    SimpleNamespace(
                        type="reasoning",
                        summary=[SimpleNamespace(text="Use retrieved references to calculate a consolidated estimate.")],
                    ),
                    SimpleNamespace(
                        type="function_call",
                        call_id="call_calculate_estimate",
                        name="calculate_estimate",
                        arguments=json.dumps(
                            {
                                "components": [
                                    {"name": "JWT authentication", "complexity": "medium", "reference_hours": 40.0},
                                    {"name": "Audit logging", "complexity": "low", "reference_hours": 24.0},
                                    {"name": "Admin dashboard", "complexity": "medium", "reference_hours": 56.0},
                                    {"name": "CSV import", "complexity": "medium", "reference_hours": 32.0},
                                ],
                                "hourly_rate_eur": 75,
                                "contingency_pct": 20,
                            }
                        ),
                    ),
                ],
                output_text="",
            ),
            SimpleNamespace(
                id="resp_3",
                output=[
                    SimpleNamespace(
                        type="function_call",
                        call_id="call_validate_estimate",
                        name="validate_estimate",
                        arguments=json.dumps(
                            {
                                "required_component_names": [
                                    "JWT authentication",
                                    "Audit logging",
                                    "Admin dashboard",
                                    "CSV import",
                                ]
                            }
                        ),
                    ),
                ],
                output_text="",
            ),
            SimpleNamespace(
                id="resp_4",
                output=[
                    SimpleNamespace(
                        type="message",
                        content=[SimpleNamespace(text="Final structured estimate is ready.")],
                    )
                ],
                output_text="Final structured estimate is ready.",
            ),
        ]

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeOpenAIClient:
    def __init__(self):
        self.responses = FakeResponsesClient()


def test_openai_responses_loop_uses_manual_function_call_outputs():
    client = FakeOpenAIClient()

    result = asyncio.run(
        run_openai_responses_agent(
            AgentRunRequest(
                transcript=(
                    "We need JWT authentication, audit logging, an admin dashboard, "
                    "and CSV import for a finance backend."
                ),
                provider="openai",
                model="gpt-5",
                max_iterations=8,
            ),
            client=client,
            model="gpt-5",
        )
    )

    assert result.provider == "openai-responses"
    assert result.model == "gpt-5"
    assert result.terminated is True
    assert result.estimate.total_hours == 182.4
    assert result.estimate.total_cost_eur == 13680.0
    assert result.validation is not None
    assert result.validation.valid is True

    tool_calls = [item for item in result.trace if item.role == "function_call"]
    tool_outputs = [item for item in result.trace if item.role == "function_call_output"]

    assert [item.tool_name for item in tool_calls].count("search_budgets") == 2
    assert [item.tool_name for item in tool_calls].count("calculate_estimate") == 1
    assert [item.tool_name for item in tool_calls].count("validate_estimate") == 1
    assert {item.call_id for item in tool_calls} == {item.call_id for item in tool_outputs}

    first_call = client.responses.calls[0]
    assert first_call["model"] == "gpt-5"
    assert first_call["reasoning"] == {"effort": "medium"}
    assert "previous_response_id" not in first_call

    second_call = client.responses.calls[1]
    assert second_call["previous_response_id"] == "resp_1"
    assert second_call["input"][0]["type"] == "function_call_output"
    assert second_call["input"][0]["call_id"] == "call_search_auth"


def test_responses_tool_schemas_are_flat_and_strict():
    tools = build_responses_tool_schemas()

    names = {tool["name"] for tool in tools}
    assert names == {"search_budgets", "calculate_estimate", "validate_estimate"}

    def assert_strict_objects(schema):
        if isinstance(schema, dict):
            if schema.get("type") == "object" or schema.get("type") == ["object", "null"]:
                assert schema.get("additionalProperties") is False
                property_names = set(schema.get("properties", {}))
                if property_names:
                    assert set(schema.get("required", [])) == property_names
            for value in schema.values():
                assert_strict_objects(value)
        elif isinstance(schema, list):
            for value in schema:
                assert_strict_objects(value)

    for tool in tools:
        assert tool["type"] == "function"
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert tool["strict"] is True
        assert "function" not in tool
        assert_strict_objects(tool["parameters"])
