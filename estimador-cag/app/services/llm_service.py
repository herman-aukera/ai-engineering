"""
LAYER: services (business logic)
RESPONSIBILITY: Build system prompts, execute LLM calls with tier routing, and parse responses
WHY IT EXISTS: Separates prompt engineering and LLM communication from HTTP transport.
DEPENDS ON: app.config (Settings, tier routing), app.context.examples (CAG data)
"""

import logging
from datetime import UTC, datetime

from redis import Redis

from app.config import TierName, get_model_config, settings
from app.context.examples import ESTIMATION_EXAMPLES
from app.services.cache import RedisEstimationCache

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

def estimate(transcription: str, tier: TierName | None = None) -> dict:
    """
    Synchronous LLM call with automatic tier fallback.
    MEJORA: Incluye provider y timestamp en la respuesta.
    """
    system_prompt = build_system_prompt()
    effective_tier = tier or settings.llm_tier
    ladder = settings.tier_ladder
    start_idx = ladder.index(effective_tier)
    tiers_to_try = ladder[start_idx:]

    for attempt_tier in tiers_to_try:
        try:
            client, model = get_model_config(attempt_tier)
            logger.info(f"Llamando tier={attempt_tier}, model={model}")

            cache = build_redis_cache()

            def model_call() -> dict:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"TRANSCRIPCION DE REUNION:\n{transcription}",
                        },
                    ],
                    temperature=_temperature_for_model(model),
                    max_tokens=2000,
                )

                content = response.choices[0].message.content
                usage = response.usage

                if not content or not content.strip():
                    raise RuntimeError(
                        f"Empty response content from model={model}, tier={attempt_tier}. "
                        "Provider returned tokens but no visible estimation."
                    )

                logger.info(
                    f"Respuesta OK: tier={attempt_tier}, "
                    f"tokens={usage.prompt_tokens}/{usage.completion_tokens}"
                )

                return {
                    "estimation": content,
                    "model": model,
                    "tier": attempt_tier,
                    "provider": _get_provider(attempt_tier),
                    "input_tokens": usage.prompt_tokens,
                    "output_tokens": usage.completion_tokens,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            return estimate_with_exact_cache(
                transcription=transcription,
                tier=attempt_tier,
                model=model,
                system_prompt=system_prompt,
                cache=cache,
                model_call=model_call,
            )
        except Exception as e:
            logger.warning(f"Tier {attempt_tier} fallo: {e}. Escalando...")
            continue

    raise RuntimeError("Todos los tiers de LLM fallaron. Verifica API keys y quotas.")


def estimate_stream(transcription: str, tier: TierName | None = None):
    """
    Synchronous generator yielding estimation tokens one by one.
    LAYER: services
    RESPONSIBILITY: Streaming LLM call for real-time UX in Streamlit.
    WHY IT EXISTS: Session 3 Nivel 2 requires token-by-token streaming.
    DEPENDS ON: app.config (get_model_config, settings), app.context.examples.
    """
    system_prompt = build_system_prompt()
    effective_tier = tier or settings.llm_tier
    ladder = settings.tier_ladder
    start_idx = ladder.index(effective_tier)
    tiers_to_try = ladder[start_idx:]

    for attempt_tier in tiers_to_try:
        try:
            client, model = get_model_config(attempt_tier)
            logger.info(f"Streaming tier={attempt_tier}, model={model}")

            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"TRANSCRIPCION DE REUNION:\n{transcription}"},
                ],
                temperature=_temperature_for_model(model),
                max_tokens=2000,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return  # Successful stream ends here
        except Exception as e:
            logger.warning(f"Stream tier {attempt_tier} fallo: {e}. Escalando...")
            continue

    raise RuntimeError(
        "Todos los tiers de LLM fallaron en streaming. "
        "Verifica API keys y quotas."
    )
