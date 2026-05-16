from app.schemas.estimation import (
    DetailLevel,
    EstimationRequest,
    EstimationResult,
    OutputFormat,
    ProjectType,
)
from app.services import llm_service

VALID_DESCRIPTION = (
    "Build a customer onboarding SaaS with authentication, admin approval, "
    "email notifications, and a reporting dashboard for operations managers."
)


def structured_payload() -> dict:
    """
    Valid structured estimate used by the fake provider.

    Why this matters:
    The product service should now consume structured provider output and return
    fields for the UI.
    """

    return {
        "summary": "A structured product estimate.",
        "project_type": "web_saas",
        "detail_level": "medium",
        "output_format": "phases_table",
        "total_duration_weeks": 4,
        "total_cost_eur": 9000,
        "confidence_pct": 76,
        "phases": [
            {
                "name": "Discovery",
                "summary": "Clarify requirements and delivery risks.",
                "duration_weeks": 2,
                "cost_eur": 4000,
                "confidence_pct": 80,
                "tasks": ["Interview stakeholders", "Define roles"],
                "risks": ["Reporting scope may expand"],
            },
            {
                "name": "Build",
                "summary": "Build backend, UI, notifications, and reporting.",
                "duration_weeks": 2,
                "cost_eur": 5000,
                "confidence_pct": 74,
                "tasks": ["Build API", "Build UI", "Add emails", "Add reports"],
                "risks": ["Email template details may change"],
            },
        ],
        "assumptions": ["Email and password authentication only"],
        "risks": ["Reporting scope may grow"],
        "recommendations": ["Confirm approval workflow before build"],
    }


class FakeCache:
    backend_name = "redis"

    def __init__(self):
        self.stored = {}

    def make_key(self, *, tier, model, system_prompt, transcription):
        self.last_key_input = {
            "tier": tier,
            "model": model,
            "system_prompt": system_prompt,
            "transcription": transcription,
        }
        return "typed-cache-key"

    def get(self, key):
        return None

    def set(self, key, value):
        self.stored[key] = value


class FakeLiteLLMProvider:
    def __init__(self):
        self.calls = []

    def resolve_model(self, tier):
        class Resolved:
            model = "deepseek-v4-flash"

        return Resolved()

    def complete_structured_messages_with_fallback(
        self,
        *,
        messages,
        starting_tier,
        tier_ladder,
        response_model,
        max_tokens=2000,
    ):
        self.calls.append(
            {
                "messages": messages,
                "starting_tier": starting_tier,
                "tier_ladder": tier_ladder,
                "response_model": response_model,
                "max_tokens": max_tokens,
            }
        )
        return {
            "result": structured_payload(),
            "model": "deepseek-v4-flash",
            "tier": starting_tier,
            "provider": "deepseek",
            "input_tokens": 10,
            "output_tokens": 20,
            "cost_usd": 0.0001,
            "cost_source": "static_estimate",
            "pricing_model": "deepseek-v4-flash",
            "finish_reason": "stop",
            "fallback_used": False,
            "timestamp": "2026-05-12T00:00:00+00:00",
        }


def test_estimate_product_renders_prompt_and_sends_separate_system_user_messages(monkeypatch):
    fake_cache = FakeCache()
    fake_provider = FakeLiteLLMProvider()
    render_calls = []

    request = EstimationRequest(
        description=VALID_DESCRIPTION,
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
    )

    def fake_render_estimation_prompt(received_request, version="v1"):
        render_calls.append((received_request, version))
        return "rendered system prompt", "rendered user prompt"

    monkeypatch.setattr(llm_service, "build_redis_cache", lambda: fake_cache)
    monkeypatch.setattr(llm_service, "LiteLLMProvider", lambda: fake_provider)
    monkeypatch.setattr(
        llm_service,
        "render_estimation_prompt",
        fake_render_estimation_prompt,
    )

    result = llm_service.estimate_product(request)

    assert result["prompt_version"] == "v1"
    assert isinstance(result["result"], EstimationResult)
    assert result["result"].summary == "A structured product estimate."
    assert result["text"].startswith("## Product estimate")
    assert result["cached"] is False
    assert result["cache_backend"] == "redis"
    assert result["model"] == "deepseek-v4-flash"
    assert result["provider"] == "deepseek"
    assert result["tier"] == "flash"

    assert render_calls == [(request, "v1")]
    assert fake_provider.calls[0]["messages"] == [
        {"role": "system", "content": "rendered system prompt"},
        {"role": "user", "content": "rendered user prompt"},
    ]
    assert fake_provider.calls[0]["starting_tier"] == "flash"
    assert fake_provider.calls[0]["response_model"] is EstimationResult
    assert fake_cache.last_key_input["transcription"] == request.model_dump_json()
    assert "prompt_version=v1" in fake_cache.last_key_input["system_prompt"]
    assert "rendered system prompt" in fake_cache.last_key_input["system_prompt"]
    assert "rendered user prompt" in fake_cache.last_key_input["system_prompt"]
    assert fake_cache.stored
