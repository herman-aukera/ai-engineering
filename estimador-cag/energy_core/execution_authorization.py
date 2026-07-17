from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from energy_core.controlled_execution import ExecutionPlan
from energy_core.models import EnergyModel

AuthorizationAction = Literal["authorize"]


class AuthorizationScope(EnergyModel):
    executable: str
    working_directory: str
    execution_mode: Literal["dry_run", "fake"]
    timeout_seconds: int = Field(ge=1, le=300)
    max_output_chars: int = Field(ge=128, le=100_000)


class ExecutionAuthorization(EnergyModel):
    schema_version: str = "1.0.0"
    authorization_id: str = Field(min_length=1, max_length=160)
    action: AuthorizationAction = "authorize"
    actor: str = Field(min_length=1, max_length=240)
    plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=0)
    accepted_revision: int = Field(ge=0)
    scope: AuthorizationScope
    created_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=12, max_length=240)
    reason: str = Field(min_length=1, max_length=2_000)
    rollback_acknowledged: bool
    consumed: bool = False

    @model_validator(mode="after")
    def validate_temporal_and_revision_contract(self) -> ExecutionAuthorization:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        if self.accepted_revision != self.expected_revision:
            raise ValueError("accepted_revision must equal expected_revision")
        return self


class AuthorizationContext(EnergyModel):
    current_revision: int = Field(ge=0)
    trusted_actors: list[str] = Field(default_factory=list)
    consumed_nonce_hashes: list[str] = Field(default_factory=list)
    now: datetime

    @model_validator(mode="after")
    def validate_context(self) -> AuthorizationContext:
        if self.now.tzinfo is None or self.now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        if len(set(self.trusted_actors)) != len(self.trusted_actors):
            raise ValueError("trusted_actors must be unique")
        if len(set(self.consumed_nonce_hashes)) != len(self.consumed_nonce_hashes):
            raise ValueError("consumed_nonce_hashes must be unique")
        return self


class AuthorizationDecision(EnergyModel):
    authorization_id: str | None = None
    plan_hash: str
    authorized: bool
    reasons: list[str] = Field(default_factory=list)
    current_revision: int = Field(ge=0)
    execution_performed: bool = False


class AuthorizationReceipt(EnergyModel):
    schema_version: str = "1.0.0"
    receipt_id: str
    authorization_id: str
    actor: str
    plan_hash: str
    accepted_revision: int = Field(ge=0)
    nonce_hash: str
    consumed_at: datetime
    execution_performed: bool = False


def scope_for_plan(plan: ExecutionPlan) -> AuthorizationScope:
    return AuthorizationScope(
        executable=plan.executable,
        working_directory=plan.working_directory,
        execution_mode=plan.execution_mode,
        timeout_seconds=plan.timeout_seconds,
        max_output_chars=plan.max_output_chars,
    )


def verify_execution_authorization(
    plan: ExecutionPlan,
    authorization: ExecutionAuthorization | None,
    context: AuthorizationContext,
) -> AuthorizationDecision:
    """Verify exact, scoped, revision-guarded authority without executing anything."""

    reasons: list[str] = []
    if authorization is None:
        reasons.append("authorization_required")
        return AuthorizationDecision(
            plan_hash=plan.plan_hash,
            authorized=False,
            reasons=reasons,
            current_revision=context.current_revision,
            execution_performed=False,
        )

    if plan.disposition != "human_required":
        reasons.append("plan_does_not_require_human_authorization")
    if plan.execution_performed:
        reasons.append("plan_already_executed")
    if authorization.actor not in context.trusted_actors:
        reasons.append("untrusted_actor")
    if authorization.plan_hash != plan.plan_hash:
        reasons.append("plan_hash_mismatch")
    if authorization.expected_revision != context.current_revision:
        reasons.append("stale_expected_revision")
    if authorization.accepted_revision != context.current_revision:
        reasons.append("accepted_revision_mismatch")
    if authorization.created_at > context.now:
        reasons.append("authorization_created_in_future")
    if authorization.expires_at <= context.now:
        reasons.append("authorization_expired")
    if authorization.consumed:
        reasons.append("authorization_already_consumed")
    nonce_hash = hash_nonce(authorization.nonce)
    if nonce_hash in context.consumed_nonce_hashes:
        reasons.append("nonce_already_consumed")
    if not authorization.rollback_acknowledged:
        reasons.append("rollback_not_acknowledged")
    if authorization.scope != scope_for_plan(plan):
        reasons.append("authorization_scope_mismatch")

    return AuthorizationDecision(
        authorization_id=authorization.authorization_id,
        plan_hash=plan.plan_hash,
        authorized=not reasons,
        reasons=reasons,
        current_revision=context.current_revision,
        execution_performed=False,
    )


def consume_execution_authorization(
    plan: ExecutionPlan,
    authorization: ExecutionAuthorization | None,
    context: AuthorizationContext,
) -> tuple[ExecutionAuthorization, AuthorizationContext, AuthorizationReceipt]:
    """Consume one valid authorization and return replay-safe persisted records."""

    decision = verify_execution_authorization(plan, authorization, context)
    if authorization is None:
        raise PermissionError("execution authorization required")
    if not decision.authorized:
        raise PermissionError(
            "execution authorization denied: " + ", ".join(decision.reasons)
        )

    nonce_hash = hash_nonce(authorization.nonce)
    consumed = authorization.model_copy(update={"consumed": True})
    updated_context = context.model_copy(
        update={
            "consumed_nonce_hashes": [
                *context.consumed_nonce_hashes,
                nonce_hash,
            ]
        }
    )
    receipt = AuthorizationReceipt(
        receipt_id=f"receipt-{authorization.authorization_id}",
        authorization_id=authorization.authorization_id,
        actor=authorization.actor,
        plan_hash=authorization.plan_hash,
        accepted_revision=authorization.accepted_revision,
        nonce_hash=nonce_hash,
        consumed_at=context.now,
        execution_performed=False,
    )
    return consumed, updated_context, receipt


def hash_nonce(nonce: str) -> str:
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()
