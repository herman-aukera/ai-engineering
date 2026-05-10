"""
LAYER: services (provider abstraction)
RESPONSIBILITY: Resolve logical LLM tiers into LiteLLM compatible model settings.
WHY IT EXISTS: Keeps provider/model routing separate from business logic and prepares
               Session 03 canonical LiteLLM integration.
DEPENDS_ON: dataclasses, app.config.settings

ARCHITECTURE NOTE:
This module does not call the LLM yet. It only defines the provider routing contract.
The actual LiteLLM call is introduced in a later TDD slice.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

import litellm

from app.config import TierName, settings


@dataclass(frozen=True)
class ResolvedModel:
    """Resolved provider configuration for a logical LLM tier."""

    tier: TierName
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float


class LiteLLMProvider:
    """
    Resolve application tiers into provider specific LiteLLM settings.

    LAYER: services
    RESPONSIBILITY: Convert flash/pro/backup/backup_pro into concrete model config.
    WHY IT EXISTS: Gives llm_service.py a provider agnostic routing interface.
    DEPENDS_ON: app.config.settings
    """

    def resolve_model(self, tier: TierName) -> ResolvedModel:
        """Return model settings for the requested logical tier."""
        if tier == "flash":
            return ResolvedModel(
                tier="flash",
                provider="deepseek",
                model=settings.deepseek_model,
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                temperature=0.3,
            )

        if tier == "pro":
            return ResolvedModel(
                tier="pro",
                provider="deepseek",
                model=settings.deepseek_model_pro,
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                temperature=0.3,
            )

        if tier == "backup":
            return ResolvedModel(
                tier="backup",
                provider="kimi",
                model=settings.kimi_model,
                api_key=settings.kimi_api_key,
                base_url=settings.kimi_base_url,
                temperature=1.0,
            )

        if tier == "backup_pro":
            return ResolvedModel(
                tier="backup_pro",
                provider="kimi",
                model=settings.kimi_model_pro,
                api_key=settings.kimi_api_key,
                base_url=settings.kimi_base_url,
                temperature=1.0,
            )

        raise ValueError(f"Unknown tier: {tier}")

    def complete(
        self,
        *,
        transcription: str,
        system_prompt: str,
        tier: TierName,
        max_tokens: int = 2000,
    ) -> dict:
        """
        Execute a synchronous LiteLLM completion for one logical tier.

        LAYER: services
        RESPONSIBILITY: Call LiteLLM and normalize response metadata.
        WHY IT EXISTS: Gives llm_service.py one provider agnostic completion API.
        DEPENDS_ON: litellm.completion, resolve_model.
        """
        resolved = self.resolve_model(tier)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"TRANSCRIPCION DE REUNION:\n{transcription}"},
        ]

        response = litellm.completion(
            model=resolved.model,
            messages=messages,
            api_key=resolved.api_key,
            api_base=resolved.base_url,
            temperature=resolved.temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError(
                f"Empty response content from model={resolved.model}, tier={resolved.tier}. "
                "Provider returned tokens but no visible estimation."
            )

        usage = response.usage
        finish_reason = getattr(response.choices[0], "finish_reason", None)

        return {
            "estimation": content,
            "model": resolved.model,
            "tier": resolved.tier,
            "provider": resolved.provider,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "finish_reason": finish_reason,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def complete_with_fallback(
        self,
        *,
        transcription: str,
        system_prompt: str,
        starting_tier: TierName,
        tier_ladder: list[TierName],
        max_tokens: int = 2000,
    ) -> dict:
        """
        Execute a synchronous LiteLLM completion with tier fallback.

        LAYER: services
        RESPONSIBILITY: Try the requested tier and escalate through configured tiers.
        WHY IT EXISTS: Keeps fallback behavior centralized and testable.
        DEPENDS_ON: complete.
        """
        start_idx = tier_ladder.index(starting_tier)
        tiers_to_try = tier_ladder[start_idx:]
        errors: list[str] = []

        for index, tier in enumerate(tiers_to_try):
            try:
                result = self.complete(
                    transcription=transcription,
                    system_prompt=system_prompt,
                    tier=tier,
                    max_tokens=max_tokens,
                )
                result["fallback_used"] = index > 0
                return result
            except Exception as exc:
                errors.append(f"{tier}: {exc}")
                continue

        raise RuntimeError(f"All LLM tiers failed: {'; '.join(errors)}")

    def stream(
        self,
        *,
        transcription: str,
        system_prompt: str,
        tier: TierName,
        max_tokens: int = 2000,
    ):
        """
        Stream a LiteLLM completion for one logical tier.

        LAYER: services
        RESPONSIBILITY: Normalize LiteLLM streaming chunks into visible text tokens.
        WHY IT EXISTS: Keeps streaming provider behavior behind the same abstraction
                       as synchronous completion.
        DEPENDS_ON: litellm.completion, resolve_model.
        """
        resolved = self.resolve_model(tier)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"TRANSCRIPCION DE REUNION:\n{transcription}"},
        ]

        stream = litellm.completion(
            model=resolved.model,
            messages=messages,
            api_key=resolved.api_key,
            api_base=resolved.base_url,
            temperature=resolved.temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        emitted_any = False
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                emitted_any = True
                yield delta

        if not emitted_any:
            raise RuntimeError(
                f"Empty streaming response content from model={resolved.model}, tier={resolved.tier}."
            )

