"""
LAYER: config (settings & wiring)
RESPONSIBILITY: Load environment variables, validate them via Pydantic, and define tier routing.
WHY IT EXISTS: Prevents secret leakage into source code and centralizes environment-dependent
               configuration. Fails fast on startup if configuration is invalid.
DEPENDS_ON: pydantic_settings (BaseSettings), openai (OpenAI client factory)
"""

from typing import Literal

from openai import OpenAI
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TierName = Literal["flash", "pro", "backup", "backup_pro"]
EstimationBackend = Literal["legacy", "graph"]
GraphRolloutMode = Literal["off", "shadow", "serve"]
GraphRetrievalMode = Literal["sequential", "parallel"]


class Settings(BaseSettings):
    """Environment-backed application settings with fail-closed validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_tier: TierName = "flash"
    estimation_backend: EstimationBackend = "legacy"
    graph_rollout_mode: GraphRolloutMode = "off"
    graph_retrieval_mode: GraphRetrievalMode = "sequential"
    graph_retrieval_max_concurrency: int = 4
    session14_confidence_threshold: float = 0.65
    ea_allow_byok: bool = False

    deepseek_api_key: str = "dummy"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_model_pro: str = "deepseek-v4-pro"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    kimi_api_key: str = "dummy"
    kimi_model: str = "kimi-k2.5"
    kimi_model_pro: str = "kimi-k2.6"
    kimi_model_max: str = ""
    kimi_base_url: str = "https://api.moonshot.ai/v1"

    openai_api_key: str = "dummy"
    openai_model_luna: str = "gpt-5.6-luna"
    openai_model_terra: str = "gpt-5.6-terra"
    openai_model_sol: str = "gpt-5.6-sol"
    openai_base_url: str = "https://api.openai.com/v1"

    provider_benchmark_snapshot_path: str = ""

    database_url: str = "postgresql://dev:dev@localhost:5432/lidr"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 86400

    semantic_cache_mode: Literal["off", "shadow", "serve"] = "shadow"
    semantic_cache_threshold: float = 0.85
    stress_fake_provider: bool = False

    @model_validator(mode="after")
    def validate_settings(self):
        """Require server credentials or an explicitly enabled BYOK-only mode."""
        server_credentials_missing = (
            self.deepseek_api_key == "dummy"
            and self.kimi_api_key == "dummy"
            and self.openai_api_key == "dummy"
        )
        if (
            not self.stress_fake_provider
            and not self.ea_allow_byok
            and server_credentials_missing
        ):
            raise ValueError(
                "At least one server API key must be configured or EA_ALLOW_BYOK=true "
                "must explicitly enable request-scoped BYOK mode."
            )
        if self.graph_retrieval_max_concurrency <= 0:
            raise ValueError("GRAPH_RETRIEVAL_MAX_CONCURRENCY must be positive")
        if not 0 <= self.session14_confidence_threshold <= 1:
            raise ValueError(
                "SESSION14_CONFIDENCE_THRESHOLD must be between zero and one"
            )
        return self

    @property
    def tier_ladder(self) -> list[TierName]:
        """Ordered list of legacy tiers for compatibility and escalation logic."""
        return ["flash", "pro", "backup", "backup_pro"]


settings = Settings()


def get_model_config(tier: TierName | None = None) -> tuple[OpenAI, str]:
    """Return an OpenAI-compatible client and model for a legacy tier."""
    tier = tier or settings.llm_tier

    if tier == "flash":
        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        return client, settings.deepseek_model
    if tier == "pro":
        client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        return client, settings.deepseek_model_pro
    if tier == "backup":
        return (
            OpenAI(
                api_key=settings.kimi_api_key,
                base_url=settings.kimi_base_url,
            ),
            settings.kimi_model,
        )
    if tier == "backup_pro":
        return (
            OpenAI(
                api_key=settings.kimi_api_key,
                base_url=settings.kimi_base_url,
            ),
            settings.kimi_model_pro,
        )
    raise ValueError(f"Unknown tier: {tier}")
