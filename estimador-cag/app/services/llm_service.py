"""
LAYER: services (business logic)
RESPONSIBILITY: Build system prompts, execute LLM calls with tier routing, and parse responses
WHY IT EXISTS: Separates prompt engineering and LLM communication from HTTP transport.
DEPENDS ON: app.config (Settings, tier routing), app.context.examples (CAG data)
"""

import logging
from datetime import datetime, timezone
from app.config import settings, get_model_config, TierName
from app.context.examples import ESTIMATION_EXAMPLES

logger = logging.getLogger(__name__)


def _get_provider(tier: str) -> str:
    """Deriva el nombre del proveedor a partir del tier."""
    if tier in ("flash", "pro"):
        return "deepseek"
    elif tier in ("backup", "backup_pro"):
        return "kimi"
    return "unknown"


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

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"TRANSCRIPCION DE REUNION:\n{transcription}"},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            usage = response.usage

            logger.info(f"Respuesta OK: tier={attempt_tier}, tokens={usage.prompt_tokens}/{usage.completion_tokens}")

            return {
                "estimation": content,
                "model": model,
                "tier": attempt_tier,
                "provider": _get_provider(attempt_tier),
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.warning(f"Tier {attempt_tier} fallo: {e}. Escalando...")
            continue

    raise RuntimeError("Todos los tiers de LLM fallaron. Verifica API keys y quotas.")
