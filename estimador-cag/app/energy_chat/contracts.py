from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ChatMode(StrEnum):
    CHAT_LITE = "chat_lite"
    RESEARCH = "research"
    PROJECT = "project"
    TUTOR = "tutor"


class ConstraintType(StrEnum):
    HARD_REJECT = "hard_reject"
    HARD_REPAIR = "hard_repair"
    SOFT = "soft"


class DecisionType(StrEnum):
    ACCEPT = "accept"
    REPAIR = "repair"
    REJECT = "reject"
    CLARIFY = "clarify"


class EnergyChatRequest(BaseModel):
    user_message: str
    draft_answer: str
    mode: ChatMode = ChatMode.CHAT_LITE
    context: dict[str, str] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("user_message", "draft_answer")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text fields must not be empty")
        return cleaned


class CriticFinding(BaseModel):
    critic: str
    finding_id: str
    constraint_type: ConstraintType
    energy: int = Field(ge=0)
    message: str
    repair_hint: str | None = None
    evidence: list[str] = Field(default_factory=list)
    suggested_decision: DecisionType | None = None


class EnergyScore(BaseModel):
    energy: int = Field(ge=0)
    hard_reject_violations: list[str] = Field(default_factory=list)
    hard_repair_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)


class EnergyDecision(BaseModel):
    decision: DecisionType
    energy: int = Field(ge=0)
    hard_constraints_passed: bool
    repairs_required: list[str] = Field(default_factory=list)
    findings: list[CriticFinding] = Field(default_factory=list)
    reasoning_summary: str
    next_action: str


class EnergyCard(BaseModel):
    decision: DecisionType
    energy: int = Field(ge=0)
    hard_constraints_passed: bool
    repairs: int = Field(ge=0)
    evidence: list[str] = Field(default_factory=list)
    remaining_caveats: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    request: EnergyChatRequest
    score: EnergyScore
    decision: EnergyDecision
    energy_card: EnergyCard
