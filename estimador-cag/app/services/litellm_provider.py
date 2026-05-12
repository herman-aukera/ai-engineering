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
from app.services.conversation import ConversationTurn, build_conversation_messages
from app.services.costs import estimate_cost_usd


@dataclass(frozen=True)
class ResolvedModel:
    """Resolved provider configuration for a logical LLM tier."""

    tier: TierName
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float



def _litellm_model_name(*, provider: str, model: str) -> str:
    """
    Convert configured model names into LiteLLM provider routed model names.

    LAYER: services
    RESPONSIBILITY: Keep env config human readable while giving LiteLLM the provider prefix it needs.
    WHY IT EXISTS: LiteLLM routes Moonshot/Kimi models through the moonshot/ provider prefix.
    DEPENDS_ON: LiteLLM provider naming conventions.
    """
    if provider == "kimi" and not model.startswith("moonshot/"):
        return f"moonshot/{model}"
    return model

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
                model=_litellm_model_name(provider="kimi", model=settings.kimi_model),
                api_key=settings.kimi_api_key,
                base_url=settings.kimi_base_url,
                temperature=1.0,
            )

        if tier == "backup_pro":
            return ResolvedModel(
                tier="backup_pro",
                provider="kimi",
                model=_litellm_model_name(provider="kimi", model=settings.kimi_model_pro),
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
        history: list[ConversationTurn] | None = None,
        max_history_turns: int = 6,
    ) -> dict:
        """
        Execute a synchronous LiteLLM completion for one logical tier.

        LAYER: services
        RESPONSIBILITY: Call LiteLLM and normalize response metadata.
        WHY IT EXISTS: Gives llm_service.py one provider agnostic completion API.
        DEPENDS_ON: litellm.completion, resolve_model.
        """
        resolved = self.resolve_model(tier)
        messages = build_conversation_messages(
            system_prompt=system_prompt,
            transcription=transcription,
            history=history,
            max_history_turns=max_history_turns,
        )

        response = litellm.completion(
            model=resolved.model,
            messages=messages,
            api_key=resolved.api_key,
            api_base=resolved.base_url,
            temperature=resolved.temperature,
            max_tokens=max_tokens,
        )

        raw_content = response.choices[0].message.content
        content = self._clean_estimation_content(raw_content)
        if not content or not content.strip():
            raise RuntimeError(
                f"Empty response content from model={resolved.model}, tier={resolved.tier}. "
                "Provider returned tokens but no visible estimation."
            )

        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        cost = estimate_cost_usd(
            model=resolved.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        return {
            "estimation": content,
            "model": resolved.model,
            "tier": resolved.tier,
            "provider": resolved.provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost["cost_usd"],
            "cost_source": cost["cost_source"],
            "pricing_model": cost["pricing_model"],
            "finish_reason": finish_reason,
            "timestamp": datetime.now(UTC).isoformat(),
        }


    def complete_messages(
        self,
        *,
        messages: list[dict[str, str]],
        tier: TierName,
        max_tokens: int = 2000,
    ) -> dict:
        """
        Execute a synchronous LiteLLM completion from explicit chat messages.

        LAYER: services
        RESPONSIBILITY: Send already-rendered system and user messages without
                        rebuilding or concatenating prompts.
        WHY IT EXISTS: Session 04 moves prompting into templates, so the provider
                       needs a message-native API.
        DEPENDS_ON: litellm.completion, resolve_model.
        """
        resolved = self.resolve_model(tier)

        response = litellm.completion(
            model=resolved.model,
            messages=messages,
            api_key=resolved.api_key,
            api_base=resolved.base_url,
            temperature=resolved.temperature,
            max_tokens=max_tokens,
        )

        raw_content = response.choices[0].message.content
        content = self._clean_estimation_content(raw_content)
        if not content or not content.strip():
            raise RuntimeError(
                f"Empty response content from model={resolved.model}, tier={resolved.tier}. "
                "Provider returned tokens but no visible estimation."
            )

        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        cost = estimate_cost_usd(
            model=resolved.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        return {
            "estimation": content,
            "model": resolved.model,
            "tier": resolved.tier,
            "provider": resolved.provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost["cost_usd"],
            "cost_source": cost["cost_source"],
            "pricing_model": cost["pricing_model"],
            "finish_reason": finish_reason,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def complete_with_fallback_messages(
        self,
        *,
        messages: list[dict[str, str]],
        starting_tier: TierName,
        tier_ladder: list[TierName],
        max_tokens: int = 2000,
    ) -> dict:
        """
        Execute a message-native LiteLLM completion with tier fallback.

        LAYER: services
        RESPONSIBILITY: Try the requested tier and escalate while preserving the
                        exact rendered system and user messages.
        WHY IT EXISTS: Keeps Session 04 typed product prompting compatible with
                       the existing fallback ladder.
        DEPENDS_ON: complete_messages.
        """
        start_idx = tier_ladder.index(starting_tier)
        tiers_to_try = tier_ladder[start_idx:]
        errors: list[str] = []

        for index, tier in enumerate(tiers_to_try):
            try:
                result = self.complete_messages(
                    messages=messages,
                    tier=tier,
                    max_tokens=max_tokens,
                )
                result["fallback_used"] = index > 0
                return result
            except Exception as exc:
                errors.append(f"{tier}: {exc}")
                continue

        raise RuntimeError(f"All LLM tiers failed: {'; '.join(errors)}")

    def complete_with_fallback(
        self,
        *,
        transcription: str,
        system_prompt: str,
        starting_tier: TierName,
        tier_ladder: list[TierName],
        max_tokens: int = 2000,
        history: list[ConversationTurn] | None = None,
        max_history_turns: int = 6,
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
        history: list[ConversationTurn] | None = None,
        max_history_turns: int = 6,
    ):
        """
        Stream a LiteLLM completion for one logical tier.

        LAYER: services
        RESPONSIBILITY: Normalize LiteLLM streaming chunks into visible text tokens.
        WHY IT EXISTS: Keeps streaming provider behavior behind the same abstraction
                       as synchronous completion.

        FALLBACK POLICY:
        Some OpenAI-compatible providers can return a valid streaming response with
        no visible delta.content chunks. When that happens, we fallback to a normal
        synchronous completion and yield the complete visible answer once.
        """
        resolved = self.resolve_model(tier)
        messages = build_conversation_messages(
            system_prompt=system_prompt,
            transcription=transcription,
            history=history,
            max_history_turns=max_history_turns,
        )

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
            token = self._extract_stream_token(chunk)
            if token:
                emitted_any = True
                yield token

        if emitted_any:
            return

        fallback = self.complete(
            transcription=transcription,
            system_prompt=system_prompt,
            tier=tier,
            max_tokens=max_tokens,
            history=history,
            max_history_turns=max_history_turns,
        )
        yield fallback["estimation"]

    def verify_visible_output(
        self,
        *,
        tier: TierName,
        transcription: str,
        system_prompt: str,
        max_tokens: int = 800,
    ) -> dict:
        """
        Verify whether a tier returns non empty visible output.

        LAYER: services
        RESPONSIBILITY: Provide an explicit reliability check for suspicious tiers.
        WHY IT EXISTS: Kimi K2.6 can appear successful while returning no visible
                       content. This helper turns that behavior into measurable
                       reliability metadata instead of guesswork.
        DEPENDS_ON: complete.
        """
        resolved = self.resolve_model(tier)

        try:
            result = self.complete(
                transcription=transcription,
                system_prompt=system_prompt,
                tier=tier,
                max_tokens=max_tokens,
            )
            visible_output = bool(result.get("estimation", "").strip())

            return {
                "tier": tier,
                "provider": resolved.provider,
                "model": resolved.model,
                "visible_output": visible_output,
                "reliable": visible_output,
                "error_type": None,
                "error_message": None,
                "input_tokens": result.get("input_tokens"),
                "output_tokens": result.get("output_tokens"),
                "finish_reason": result.get("finish_reason"),
                "timestamp": result.get("timestamp"),
            }

        except Exception as exc:
            return {
                "tier": tier,
                "provider": resolved.provider,
                "model": resolved.model,
                "visible_output": False,
                "reliable": False,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "input_tokens": None,
                "output_tokens": None,
                "finish_reason": None,
                "timestamp": None,
            }

    @staticmethod
    def _clean_estimation_content(content: str | None) -> str | None:
        """
        Remove process-like preambles before the final estimation.

        WHY IT EXISTS: Some providers may return a visible preamble before the
        actual answer. The UI should show the final estimation, not the model's
        self-description of the task.
        """
        if content is None:
            return None

        markers = [
            "## Estimación",
            "## Estimacion",
            "### Desglose",
            "Desglose de tareas",
        ]

        positions = [content.find(marker) for marker in markers if content.find(marker) != -1]
        if not positions:
            return content

        start = min(positions)
        return content[start:].lstrip()

    @staticmethod
    def _extract_stream_token(chunk) -> str | None:
        """
        Extract visible token text from LiteLLM/OpenAI-compatible stream chunks.

        WHY IT EXISTS: Providers differ between object-style and dict-style chunks.
        """
        try:
            choice = chunk.choices[0]
        except (AttributeError, IndexError, TypeError):
            try:
                choice = chunk["choices"][0]
            except (KeyError, IndexError, TypeError):
                return None

        try:
            delta = choice.delta
        except AttributeError:
            delta = choice.get("delta", {}) if isinstance(choice, dict) else {}

        if isinstance(delta, dict):
            return delta.get("content")

        return getattr(delta, "content", None)

