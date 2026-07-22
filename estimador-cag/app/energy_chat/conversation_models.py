"""Strict public and persistence contracts for multi-turn EACHAT conversations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.energy_chat.api_v2_contracts import (
    ContextProfile,
    EffortProfile,
    EnergyChatV2Response,
    ExecutionProfile,
    OrchestrationMode,
    ProviderPreference,
)
from app.energy_chat.contracts import Mode

ConversationRole = Literal["user", "assistant"]


class ConversationRecord(BaseModel):
    """One durable conversation with immutable ordered graph turns."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(min_length=1, max_length=128)
    revision: int = Field(default=0, ge=0)
    turns: list[ConversationTurn] = Field(default_factory=list)


class ConversationTurn(BaseModel):
    """One immutable user/assistant exchange tied to one graph checkpoint thread."""

    model_config = ConfigDict(extra="forbid")

    turn_id: str = Field(min_length=1, max_length=128)
    turn_index: int = Field(ge=1)
    graph_thread_id: str = Field(min_length=1, max_length=128)
    user_message: str = Field(min_length=1, max_length=10_000)
    assistant_message: str = Field(min_length=1)
    memory_message_count: int = Field(default=0, ge=0)
    graph_response: EnergyChatV2Response


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
    fallback_provider_allowlist: list[str] = Field(default_factory=list)
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)


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
