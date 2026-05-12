"""
LAYER: services (business logic)
RESPONSIBILITY: Build system prompts, execute LLM calls with tier routing, and parse responses
WHY IT EXISTS: Separates prompt engineering and LLM communication from HTTP transport.
DEPENDS ON: app.config (Settings, tier routing), app.context.examples (CAG data)
"""

import logging

from redis import Redis

from app.config import TierName, settings
from app.context.examples import ESTIMATION_EXAMPLES
from app.prompts.loader import render_estimation_prompt
from app.schemas.estimation import EstimationRequest
from app.services.cache import RedisEstimationCache
from app.services.conversation import ConversationTurn
from app.services.litellm_provider import LiteLLMProvider

logger = logging.getLogger(__name__)


def _get_provider(tier: str) -> str:
    """Deriva el nombre del proveedor a partir del tier."""
    if tier in ("flash", "pro"):
        return "deepseek"
    elif tier in ("backup", "backup_pro"):
        return "kimi"
    return "unknown"

def _temperature_for_model(model: str) -> float:
    """
    Return provider-safe temperature.

    Kimi K2 models reject arbitrary temperature values and require 1.
    DeepSeek accepts lower deterministic values such as 0.3.
    """
    if model.startswith("kimi-k2."):
        return 1.0
    return 0.3


def build_system_prompt() -> str:
    """Constructs the CAG system prompt with few-shot examples."""
    examples_text = "\n\n---\n\n".join(
        f"TRANSCRIPCION:\n{ex['meeting_summary']}\n\nESTIMACION GENERADA:\n{ex['estimation']}"
        for ex in ESTIMATION_EXAMPLES
    )
    return f"""Eres un estimador de software senior con 15 anos de experiencia.
Generas estimaciones detalladas basandote en transcripciones de reuniones.

Reglas:
- Desglosa en tareas concretas (horas por tarea)
- Incluye total de horas, equipo recomendado y duracion estimada
- Se realista, no optimista
- Usa markdown para la estimacion

Ejemplos de referencia:

{examples_text}"""



def build_redis_cache() -> RedisEstimationCache:
    """
    Build the Redis exact response cache from application settings.

    LAYER: services
    RESPONSIBILITY: Create the process-independent cache backend used by estimate().
    WHY IT EXISTS: Keeps Redis client construction out of endpoint code and makes
                   cache wiring testable.
    DEPENDS ON: settings.redis_url, settings.cache_ttl_seconds, redis.Redis.
    """
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return RedisEstimationCache(
        redis_client=redis_client,
        ttl_seconds=settings.cache_ttl_seconds,
    )

def estimate_with_exact_cache(
    *,
    transcription: str,
    tier: str,
    model: str,
    system_prompt: str,
    cache,
    model_call,
) -> dict:
    """
    Orchestrate exact response caching around an LLM estimation call.

    LAYER: services
    RESPONSIBILITY: Check exact cache before calling the model and store fresh responses.
    WHY IT EXISTS: Keeps cache orchestration testable without making real provider calls.
    DEPENDS ON: cache object with make_key/get/set/backend_name and a zero-arg model_call.
    """
    cache_key = cache.make_key(
        tier=tier,
        model=model,
        system_prompt=system_prompt,
        transcription=transcription,
    )

    cached_result = cache.get(cache_key)
    if cached_result is not None:
        result = cached_result.copy()
        result["cached"] = True
        result["cache_backend"] = cache.backend_name
        return result

    result = model_call().copy()
    result["cached"] = False
    result["cache_backend"] = cache.backend_name
    cache.set(cache_key, result.copy())
    return result

def estimate(
    transcription: str,
    tier: TierName | None = None,
    history: list[ConversationTurn] | None = None,
    max_history_turns: int = 6,
) -> dict:
    """
    Synchronous LLM call with Redis exact cache and LiteLLM provider fallback.

    LAYER: services
    RESPONSIBILITY: Orchestrate CAG prompt creation, Redis exact cache, LiteLLM call,
                    fallback routing, and normalized response metadata.
    WHY IT EXISTS: Keeps HTTP routers thin while centralizing the application use case.
    DEPENDS ON: build_system_prompt, build_redis_cache, LiteLLMProvider.
    """
    system_prompt = build_system_prompt()
    effective_tier = tier or settings.llm_tier
    provider = LiteLLMProvider()
    resolved = provider.resolve_model(effective_tier)
    cache = build_redis_cache()

    def model_call() -> dict:
        logger.info(f"Calling LiteLLM starting_tier={effective_tier}, model={resolved.model}")
        return provider.complete_with_fallback(
            transcription=transcription,
            system_prompt=system_prompt,
            starting_tier=effective_tier,
            tier_ladder=settings.tier_ladder,
            max_tokens=2000,
            history=history,
            max_history_turns=max_history_turns,
        )

    return estimate_with_exact_cache(
        transcription=transcription,
        tier=effective_tier,
        model=resolved.model,
        system_prompt=system_prompt,
        cache=cache,
        model_call=model_call,
    )



def estimate_product(
    request: EstimationRequest,
    tier: TierName | None = None,
    prompt_version: str = "v1",
) -> dict:
    """
    Estimate a typed product request using versioned prompt templates.

    LAYER: services
    RESPONSIBILITY: Render Session 04 product prompts, call the provider with
                    separate system and user messages, and return the mandatory
                    EstimationResponse shape.
    WHY IT EXISTS: Converts the estimator from free chat input into a typed
                   product interface without deleting the legacy Session 03 flow.
    DEPENDS ON: render_estimation_prompt, Redis exact cache, LiteLLMProvider.
    """
    system_prompt, user_prompt = render_estimation_prompt(request, version=prompt_version)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    effective_tier = tier or settings.llm_tier
    provider = LiteLLMProvider()
    resolved = provider.resolve_model(effective_tier)
    cache = build_redis_cache()

    cache_identity = request.model_dump_json()
    combined_prompt_identity = f"{system_prompt}\n\n--- user prompt ---\n{user_prompt}"

    def model_call() -> dict:
        logger.info(
            "Calling LiteLLM product estimator "
            f"starting_tier={effective_tier}, model={resolved.model}, "
            f"prompt_version={prompt_version}"
        )
        return provider.complete_with_fallback_messages(
            messages=messages,
            starting_tier=effective_tier,
            tier_ladder=settings.tier_ladder,
            max_tokens=2000,
        )

    result = estimate_with_exact_cache(
        transcription=cache_identity,
        tier=effective_tier,
        model=resolved.model,
        system_prompt=combined_prompt_identity,
        cache=cache,
        model_call=model_call,
    )

    return {
        "text": result["estimation"],
        "prompt_version": prompt_version,
    }

def estimate_stream(
    transcription: str,
    tier: TierName | None = None,
    history: list[ConversationTurn] | None = None,
    max_history_turns: int = 6,
):
    """
    Stream estimation tokens through the LiteLLM provider abstraction.

    LAYER: services
    RESPONSIBILITY: Build the CAG prompt and delegate streaming to LiteLLMProvider.
    WHY IT EXISTS: Keeps streaming provider details out of FastAPI and Streamlit.
    DEPENDS ON: build_system_prompt, LiteLLMProvider.
    """
    system_prompt = build_system_prompt()
    effective_tier = tier or settings.llm_tier
    provider = LiteLLMProvider()

    logger.info(f"Streaming with LiteLLM tier={effective_tier}")

    yield from provider.stream(
        transcription=transcription,
        system_prompt=system_prompt,
        tier=effective_tier,
        max_tokens=2000,
        history=history,
        max_history_turns=max_history_turns,
    )

