from app.schemas.estimation import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)
from app.services import llm_service

VALID_DESCRIPTION = (
    "Build a customer onboarding SaaS with authentication, admin approval, "
    "email notifications, and a reporting dashboard for operations managers."
)


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

    def complete_with_fallback_messages(
        self,
        *,
        messages,
        starting_tier,
        tier_ladder,
        max_tokens=2000,
    ):
        self.calls.append(
            {
                "messages": messages,
                "starting_tier": starting_tier,
                "tier_ladder": tier_ladder,
                "max_tokens": max_tokens,
            }
        )
        return {
            "estimation": "## Typed product estimate",
            "model": "deepseek-v4-flash",
            "tier": starting_tier,
            "provider": "deepseek",
            "input_tokens": 10,
            "output_tokens": 20,
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

    assert result == {
        "text": "## Typed product estimate",
        "prompt_version": "v1",
    }

    assert render_calls == [(request, "v1")]
    assert fake_provider.calls[0]["messages"] == [
        {"role": "system", "content": "rendered system prompt"},
        {"role": "user", "content": "rendered user prompt"},
    ]
    assert fake_provider.calls[0]["starting_tier"] == "flash"
    assert fake_cache.last_key_input["transcription"] == request.model_dump_json()
    assert "rendered system prompt" in fake_cache.last_key_input["system_prompt"]
    assert "rendered user prompt" in fake_cache.last_key_input["system_prompt"]
    assert fake_cache.stored
