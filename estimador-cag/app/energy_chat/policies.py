"""Default Energy Aware Chat policies."""

from __future__ import annotations

from app.energy_chat.contracts import EnergyPolicy, RequestPolicyAssessment

REQUEST_POLICY_VERSION = "energy-chat-request-policy-1.0.0"

REFUSAL_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "show your chain of thought",
        "hidden_reasoning_request",
        "Hidden chain-of-thought cannot be provided; offer a concise reasoning summary.",
    ),
    (
        "reveal your chain of thought",
        "hidden_reasoning_request",
        "Hidden chain-of-thought cannot be provided; offer a concise reasoning summary.",
    ),
    (
        "use leaked source",
        "private_source_request",
        "Leaked or unauthorized source material cannot be used.",
    ),
    (
        "use stolen credentials",
        "stolen_credentials_request",
        "Stolen credentials cannot be used.",
    ),
)

ESCALATION_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "authorize production deployment",
        "production_authority_required",
        "Production deployment authorization requires an accountable human authority.",
    ),
    (
        "approve the production release",
        "production_authority_required",
        "Production release approval requires an accountable human authority.",
    ),
    (
        "override policy",
        "policy_override_requires_human",
        "Policy overrides require explicit human authority and an audit record.",
    ),
    (
        "make the final legal decision",
        "legal_authority_required",
        "Final legal decisions require qualified human authority.",
    ),
)


def default_chat_lite_policy() -> EnergyPolicy:
    """Return the deterministic MVP policy for chat_lite evaluations."""

    return EnergyPolicy()


def assess_request_policy(user_request: str) -> RequestPolicyAssessment:
    """Apply deterministic request-level refusal and authority rules."""

    normalized = " ".join(user_request.casefold().split())
    for marker, rule_id, reason in REFUSAL_RULES:
        if marker in normalized:
            return RequestPolicyAssessment(
                version=REQUEST_POLICY_VERSION,
                directive="refuse",
                rule_id=rule_id,
                reason=reason,
            )
    for marker, rule_id, reason in ESCALATION_RULES:
        if marker in normalized:
            return RequestPolicyAssessment(
                version=REQUEST_POLICY_VERSION,
                directive="escalate",
                rule_id=rule_id,
                reason=reason,
            )
    return RequestPolicyAssessment(
        version=REQUEST_POLICY_VERSION,
        directive="continue",
        rule_id="request_allowed",
        reason="No deterministic refusal or human-authority rule matched.",
    )
