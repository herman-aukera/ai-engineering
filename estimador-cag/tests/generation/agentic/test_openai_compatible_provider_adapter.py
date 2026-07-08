from app.generation.agentic.provider_adapters import (
    OpenAICompatibleProviderAdapter,
    ProviderAdapterRequest,
    parse_provider_plan_json,
)


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeCompletion(
            """
            {
              "steps": [
                {
                  "kind": "reasoning",
                  "content": "Identify components before estimating."
                },
                {
                  "kind": "function_call",
                  "content": "Call search_budgets.",
                  "tool_name": "search_budgets",
                  "call_id": "call_search_auth",
                  "arguments": {
                    "query": "JWT authentication financial backend"
                  }
                },
                {
                  "kind": "function_call",
                  "content": "Call calculate_estimate.",
                  "tool_name": "calculate_estimate",
                  "call_id": "call_calculate_estimate",
                  "arguments": {
                    "components": [
                      {
                        "name": "JWT authentication",
                        "complexity": "medium",
                        "reference_hours": 40
                      }
                    ],
                    "hourly_rate_eur": 75,
                    "contingency_pct": 0.2
                  }
                },
                {
                  "kind": "function_call",
                  "content": "Call validate_estimate.",
                  "tool_name": "validate_estimate",
                  "call_id": "call_validate_estimate",
                  "arguments": {
                    "required_component_names": ["JWT authentication"]
                  }
                },
                {
                  "kind": "final",
                  "content": "Return the structured estimate."
                }
              ]
            }
            """
        )


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def test_parse_provider_plan_json_returns_normalized_steps():
    steps = parse_provider_plan_json(
        """
        {
          "steps": [
            {"kind": "reasoning", "content": "Think."},
            {
              "kind": "function_call",
              "content": "Call search.",
              "tool_name": "search_budgets",
              "call_id": "call_1",
              "arguments": {"query": "audit logging"}
            },
            {"kind": "final", "content": "Done."}
          ]
        }
        """
    )

    assert [step.kind for step in steps] == ["reasoning", "function_call", "final"]
    assert steps[1].tool_name == "search_budgets"
    assert steps[1].call_id == "call_1"
    assert steps[1].arguments == {"query": "audit logging"}


def test_openai_compatible_provider_adapter_uses_injected_client_without_real_keys():
    client = FakeClient()
    adapter = OpenAICompatibleProviderAdapter(
        client=client,
        model="provider-test-model",
        provider="deepseek",
    )

    steps = adapter.plan(
        ProviderAdapterRequest(
            transcript=(
                "Client needs JWT authentication and audit logging for a financial app."
            ),
            provider="deepseek",
            model="provider-test-model",
        )
    )

    assert [step.kind for step in steps] == [
        "reasoning",
        "function_call",
        "function_call",
        "function_call",
        "final",
    ]
    assert steps[1].tool_name == "search_budgets"
    assert steps[2].tool_name == "calculate_estimate"
    assert steps[3].tool_name == "validate_estimate"

    call = client.chat.completions.calls[0]
    assert call["model"] == "provider-test-model"
    assert call["temperature"] == 0
    assert "Return only JSON" in call["messages"][0]["content"]
    assert "JWT authentication" in call["messages"][1]["content"]


def test_parse_provider_plan_json_rejects_invalid_json_shape():
    try:
        parse_provider_plan_json('{"not_steps": []}')
    except ValueError as exc:
        assert "steps" in str(exc)
    else:
        raise AssertionError("provider plan without steps must fail")


def test_openai_compatible_provider_adapter_allows_temperature_override():
    client = FakeClient()
    adapter = OpenAICompatibleProviderAdapter(
        client=client,
        model="provider-test-model",
        provider="kimi",
        temperature=1,
    )

    adapter.plan(
        ProviderAdapterRequest(
            transcript=(
                "Client needs JWT authentication and audit logging for a financial app."
            ),
            provider="kimi",
            model="provider-test-model",
        )
    )

    call = client.chat.completions.calls[0]
    assert call["temperature"] == 1


def test_parse_provider_plan_json_accepts_trailing_provider_text():
    raw_content = """
    {
      "steps": [
        {"kind": "reasoning", "content": "Think."},
        {
          "kind": "function_call",
          "content": "Call calculate.",
          "tool_name": "calculate_estimate",
          "call_id": "call_calculate",
          "arguments": {
            "components": [
              {
                "name": "JWT authentication",
                "complexity": "medium",
                "reference_hours": 40
              }
            ],
            "hourly_rate_eur": 75,
            "contingency_pct": 0.2
          }
        },
        {"kind": "final", "content": "Done."}
      ]
    }
    This trailing provider note should not break the smoke parser.
    """

    steps = parse_provider_plan_json(raw_content)

    assert [step.kind for step in steps] == [
        "reasoning",
        "function_call",
        "final",
    ]
    assert steps[1].tool_name == "calculate_estimate"


def test_parse_provider_plan_json_accepts_markdown_json_fence():
    fence = chr(96) * 3
    raw_content = (
        fence
        + "json\n"
        + """
        {
          "steps": [
            {"kind": "reasoning", "content": "Think."},
            {"kind": "final", "content": "Done."}
          ]
        }
        """
        + "\n"
        + fence
    )

    steps = parse_provider_plan_json(raw_content)

    assert [step.kind for step in steps] == ["reasoning", "final"]
