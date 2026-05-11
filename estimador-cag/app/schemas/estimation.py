"""
LAYER: schemas (data contracts)
RESPONSIBILITY: Define Pydantic models for estimation requests and responses
WHY IT EXISTS: Validates HTTP payloads at the edge and auto-generates OpenAPI docs.
               Separado del router por decision arquitectonica (flag Heladia).
DEPENDS ON: pydantic (BaseModel, Field)
"""

from pydantic import BaseModel, Field


class EstimateRequest(BaseModel):
    """Inbound payload for POST /api/v1/estimate."""
    transcription: str = Field(
        ..., min_length=10,
        description="Texto de la transcripcion de reunion"
    )
    tier: str = Field(default="flash", description="Tier de LLM: flash, pro, backup, backup_pro")


class EstimateResponse(BaseModel):
    """
    Outbound payload with generated estimation and model metadata.
    MEJORA: Incluye provider (deepseek/kimi) y timestamp ISO.
            Esto alinea con el schema del ejercicio de LIDR que muestra 'provider'.
    """
    estimation: str = Field(..., description="Estimacion generada en markdown")
    model: str = Field(..., description="Modelo especifico que respondio")
    tier: str = Field(..., description="Tier logico utilizado")
    provider: str = Field(..., description="Proveedor de LLM: deepseek o kimi")
    input_tokens: int = Field(..., description="Tokens de entrada")
    output_tokens: int = Field(..., description="Tokens de salida")
    timestamp: str = Field(..., description="Timestamp ISO 8601 UTC de la respuesta")
    cached: bool = Field(default=False, description="True when the response came from exact cache")
    cache_backend: str = Field(default="unknown", description="Cache backend used: redis, memory_fallback, or unknown")
    cost_usd: float | None = Field(default=None, description="Estimated LLM call cost in USD")
    cost_source: str | None = Field(
        default=None,
        description="How cost was derived: static_estimate, missing_token_usage, unknown_pricing, etc.",
    )
    pricing_model: str | None = Field(default=None, description="Model id used for cost lookup")
