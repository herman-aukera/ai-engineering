"""DeepSeek baseline draft harness for Energy Aware Chat benchmarks."""

from __future__ import annotations

from typing import Protocol

from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    ProviderTier,
)

BASELINE_SYSTEM_PROMPT = """You are the plain DeepSeek baseline draft provider for Energy Aware Chat.

Write one useful assistant answer candidate for later evaluation.
Do not evaluate yourself.
Do not include an Energy Card.
Do not claim that validation, tests, citations, sources, or deployment exist unless the user supplied that evidence.
Do not reveal hidden chain of thought. Provide a concise answer only.
"""

BASELINE_TIER_LADDER: tuple[ProviderTier, ...] = (
    "flash",
    "pro",
    "backup",
    "backup_pro",
)


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


def build_deepseek_baseline_messages(
    request: DeepSeekBaselineRequest,
) -> list[dict[str, str]]:
    """Build the plain baseline messages used before energy-aware evaluation."""

    constraints = _format_optional_list(
        "Required constraints", request.required_constraints
    )
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
    allow_provider_fallback: bool = True,
    tier_ladder: list[ProviderTier] | None = None,
) -> DeepSeekBaselineResult:
    """Generate one plain provider draft for later Energy Aware evaluation.

    Legacy callers retain the historical fallback ladder. New V2 callers must
    pass an explicit fallback policy; the safe V2 default disables fallback.
    """

    active_provider = provider or _build_default_provider()
    messages = build_deepseek_baseline_messages(request)
    active_ladder = list(tier_ladder or BASELINE_TIER_LADDER)
    if request.tier not in active_ladder:
        active_ladder.insert(0, request.tier)
    provider_result = _complete_baseline_messages(
        provider=active_provider,
        messages=messages,
        starting_tier=request.tier,
        tier_ladder=active_ladder,
        max_tokens=request.max_tokens,
        allow_provider_fallback=allow_provider_fallback,
    )
    draft_answer = _extract_draft_answer(provider_result)
    resolved_tier = _provider_tier(provider_result.get("tier") or request.tier)
    fallback_used = bool(provider_result.get("fallback_used", False))
    served_provider = str(provider_result.get("provider") or "deepseek")
    evidence_refs = ["provider:deepseek_baseline", f"tier:{resolved_tier}"]
    if fallback_used:
        evidence_refs.append(f"fallback_from:{request.tier}")

    return DeepSeekBaselineResult(
        request=request,
        draft_answer=draft_answer,
        provider=served_provider,
        model=str(provider_result.get("model") or "unknown"),
        tier=resolved_tier,
        input_tokens=_optional_int(provider_result.get("input_tokens")),
        output_tokens=_optional_int(provider_result.get("output_tokens")),
        cost_usd=_optional_float(provider_result.get("cost_usd")),
        finish_reason=_optional_str(provider_result.get("finish_reason")),
        fallback_used=fallback_used,
        evidence_refs=evidence_refs,
        metadata={
            "prompt_family": "plain_baseline",
            "energy_evaluated": False,
            "fallback_capable": hasattr(
                active_provider, "complete_with_fallback_messages"
            ),
            "fallback_authorized": allow_provider_fallback,
            "requested_tier": request.tier,
            "resolved_tier": resolved_tier,
            "tier_ladder": active_ladder,
        },
    )


def _complete_baseline_messages(
    *,
    provider: BaselineDraftProvider,
    messages: list[dict[str, str]],
    starting_tier: str,
    tier_ladder: list[ProviderTier],
    max_tokens: int,
    allow_provider_fallback: bool,
) -> dict:
    fallback_method = getattr(provider, "complete_with_fallback_messages", None)
    if allow_provider_fallback and callable(fallback_method):
        return fallback_method(
            messages=messages,
            starting_tier=starting_tier,
            tier_ladder=tier_ladder,
            max_tokens=max_tokens,
        )

    return provider.complete_messages(
        messages=messages,
        tier=starting_tier,
        max_tokens=max_tokens,
    )


def _build_default_provider() -> BaselineDraftProvider:
    """Load the LiteLLM provider only when the live baseline is called."""

    from app.services.litellm_provider import LiteLLMProvider

    return LiteLLMProvider()


def _format_optional_list(label: str, values: list[str]) -> str:
    if not values:
        return f"{label}: none supplied."
    formatted = "\n".join(f"- {value}" for value in values)
    return f"{label}:\n{formatted}"


def _extract_draft_answer(provider_result: dict) -> str:
    raw_answer = provider_result.get("estimation") or provider_result.get(
        "draft_answer"
    )
    if not isinstance(raw_answer, str) or not raw_answer.strip():
        raise RuntimeError("DeepSeek baseline provider returned no visible draft answer.")
    return raw_answer.strip()


def _provider_tier(value: object) -> ProviderTier:
    if value in BASELINE_TIER_LADDER:
        return value  # type: ignore[return-value]
    raise RuntimeError(f"Energy Chat baseline returned unknown provider tier: {value}")


def _optional_int(value) -> int | None:
    return None if value is None else int(value)


def _optional_float(value) -> float | None:
    return None if value is None else float(value)


def _optional_str(value) -> str | None:
    return None if value is None else str(value)
