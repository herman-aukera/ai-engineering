"""Strict public and persistence contracts for multi-turn EACHAT conversations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.energy_chat.api_v2_contracts import (
    ContextProfile,
    EffortProfile,
    EnergyChatV2Response,
    ExecutionProfile,
    FallbackProvider,
    OrchestrationMode,
    ProviderPreference,
)
from app.energy_chat.contracts import Mode

ConversationRole = Literal["user", "assistant"]


class ConversationTurn(BaseModel):
    """One immutable user/assistant exchange tied to one graph checkpoint thread."""

    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(min_length=1, max_length=128)
    turn_index: int = Field(ge=1)
    request_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    graph_thread_id: str = Field(min_length=1, max_length=128)
    user_message: str = Field(min_length=1, max_length=10_000)
    assistant_message: str = Field(min_length=1)
    memory_message_count: int = Field(default=0, ge=0)
    graph_response: EnergyChatV2Response


class ConversationRecord(BaseModel):
    """One durable conversation with immutable ordered graph turns."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(min_length=1, max_length=128)
    revision: int = Field(default=0, ge=0)
    turns: list[ConversationTurn] = Field(default_factory=list)


class ConversationCreateResponse(BaseModel):
    """Identity and initial revision for a new conversation."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    revision: Literal[0] = 0


class ConversationTurnRequest(BaseModel):
    """One new turn with revision and idempotency protection."""

    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_-]+$")
    expected_revision: int = Field(ge=0)
    user_message: str = Field(min_length=1, max_length=10_000)
    mode: Mode = "project"
    provider_preference: ProviderPreference = "deepseek"
    effort_profile: EffortProfile = "balanced"
    context_profile: ContextProfile = "balanced"
    orchestration_mode: OrchestrationMode = "critic"
    execution_profile: ExecutionProfile = "deterministic"
    allow_provider_fallback: bool = False
    fallback_provider_allowlist: list[FallbackProvider] = Field(default_factory=list)
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_fallback_contract(self) -> ConversationTurnRequest:
        self.fallback_provider_allowlist = list(
            dict.fromkeys(self.fallback_provider_allowlist)
        )
        if self.allow_provider_fallback and not self.fallback_provider_allowlist:
            raise ValueError(
                "fallback_provider_allowlist is required when provider fallback is enabled"
            )
        if not self.allow_provider_fallback and self.fallback_provider_allowlist:
            raise ValueError(
                "fallback_provider_allowlist requires allow_provider_fallback=true"
            )
        return self


class ConversationTurnResponse(BaseModel):
    """Stored turn plus the authoritative conversation revision."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    revision: int = Field(ge=1)
    replayed_idempotency_key: bool = False
    turn: ConversationTurn


class ConversationHistoryResponse(BaseModel):
    """Safe decrypted conversation history returned to its caller."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    revision: int = Field(ge=0)
    turns: list[ConversationTurn] = Field(default_factory=list)


class ConversationDeleteResponse(BaseModel):
    """Deletion acknowledgement for privacy and retention control."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    deleted: Literal[True] = True
