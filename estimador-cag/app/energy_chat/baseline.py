"""DeepSeek baseline draft harness for Energy Aware Chat benchmarks."""

from __future__ import annotations

from typing import Protocol

from app.energy_chat.contracts import DeepSeekBaselineRequest, DeepSeekBaselineResult

BASELINE_SYSTEM_PROMPT = """You are the plain DeepSeek baseline draft provider for Energy Aware Chat.

Write one useful assistant answer candidate for later evaluation.
Do not evaluate yourself.
Do not include an Energy Card.
Do not claim that validation, tests, citations, sources, or deployment exist unless the user supplied that evidence.
Do not reveal hidden chain of thought. Provide a concise answer only.
"""


class BaselineDraftProvider(Protocol):
    """Provider seam used to keep normal tests fake-provider only."""

    def complete_messages(
        self,
        *,
        messages: list[dict[str, str]],
        tier: str,
        max_tokens: int,
    ) -> dict:
        """Return a provider-normalized draft completion."""


def build_deepseek_baseline_messages(request: DeepSeekBaselineRequest) -> list[dict[str, str]]:
    """Build the plain baseline messages used before energy-aware evaluation."""

    constraints = _format_optional_list("Required constraints", request.required_constraints)
    sections = _format_optional_list("Required sections", request.required_sections)
    user_content = (
        "Create a draft answer candidate for this user request.\n\n"
        f"Mode: {request.mode}\n"
        f"{constraints}\n"
        f"{sections}\n\n"
        f"User request:\n{request.user_message}"
    )
    return [
        {"role": "system", "content": BASELINE_SYSTEM_PROMPT.strip()},
        {"role": "user", "content": user_content.strip()},
    ]


def generate_deepseek_baseline_draft(
    request: DeepSeekBaselineRequest,
    *,
    provider: BaselineDraftProvider | None = None,
) -> DeepSeekBaselineResult:
    """
    Generate one plain DeepSeek draft answer for later Energy Aware evaluation.

    The default provider is loaded lazily so imports and normal tests never require
    real provider keys. Tests should inject a fake provider through the seam.
    """

    active_provider = provider or _build_default_provider()
    messages = build_deepseek_baseline_messages(request)
    provider_result = active_provider.complete_messages(
        messages=messages,
        tier=request.tier,
        max_tokens=request.max_tokens,
    )
    draft_answer = _extract_draft_answer(provider_result)
    return DeepSeekBaselineResult(
        request=request,
        draft_answer=draft_answer,
        provider=str(provider_result.get("provider") or "deepseek"),
        model=str(provider_result.get("model") or "unknown"),
        tier=request.tier,
        input_tokens=_optional_int(provider_result.get("input_tokens")),
        output_tokens=_optional_int(provider_result.get("output_tokens")),
        cost_usd=_optional_float(provider_result.get("cost_usd")),
        finish_reason=_optional_str(provider_result.get("finish_reason")),
        fallback_used=bool(provider_result.get("fallback_used", False)),
        evidence_refs=["provider:deepseek_baseline", f"tier:{request.tier}"],
        metadata={
            "prompt_family": "plain_baseline",
            "energy_evaluated": False,
        },
    )


def _build_default_provider() -> BaselineDraftProvider:
    """Load the existing LiteLLM provider only when the live baseline is called."""

    from app.services.litellm_provider import LiteLLMProvider

    return LiteLLMProvider()


def _format_optional_list(label: str, values: list[str]) -> str:
    if not values:
        return f"{label}: none supplied."
    formatted = "\n".join(f"- {value}" for value in values)
    return f"{label}:\n{formatted}"


def _extract_draft_answer(provider_result: dict) -> str:
    raw_answer = provider_result.get("estimation") or provider_result.get("draft_answer")
    if not isinstance(raw_answer, str) or not raw_answer.strip():
        raise RuntimeError("DeepSeek baseline provider returned no visible draft answer.")
    return raw_answer.strip()


def _optional_int(value) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_str(value) -> str | None:
    if value is None:
        return None
    return str(value)
