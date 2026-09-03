"""Default Energy Aware Chat policies."""

from __future__ import annotations

from app.energy_chat.contracts import EnergyPolicy, RequestPolicyAssessment

REQUEST_POLICY_VERSION = "energy-chat-request-policy-1.1.0"

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
    (
        "patch the java source code",
        "l3_source_code_remediation",
        "Arbitrary Java source-code remediation is outside the EACHAT L2 support boundary; escalate to an authorized engineering workflow.",
    ),
    (
        "patch my java source",
        "l3_source_code_remediation",
        "Arbitrary Java source-code remediation is outside the EACHAT L2 support boundary; escalate to an authorized engineering workflow.",
    ),
    (
        "kubernetes",
        "unsupported_l2_technology",
        "Kubernetes cluster diagnosis and mutation are outside the EACHAT final-project L2 support scope.",
    ),
)

_EXACT_CAUSE_MARKERS = (
    "exact root cause",
    "exact cause",
    "tell me exactly why",
)

_MISSING_DIAGNOSTIC_MARKERS = (
    "no logs",
    "without logs",
    "no error message",
    "without an error message",
    "no stack trace",
    "without a stack trace",
    "no diagnostic",
)


def default_chat_lite_policy() -> EnergyPolicy:
    """Return the deterministic MVP policy for chat_lite evaluations."""

    return EnergyPolicy()


def assess_request_policy(user_request: str) -> RequestPolicyAssessment:
    """Apply deterministic request-level refusal, authority, and evidence rules."""

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
    if _requires_diagnostic_clarification(normalized):
        return RequestPolicyAssessment(
            version=REQUEST_POLICY_VERSION,
            directive="clarify",
            rule_id="diagnostic_evidence_required",
            reason=(
                "An exact root-cause claim is not supportable without incident-specific "
                "diagnostic evidence; request logs, the concrete error, or equivalent evidence."
            ),
        )
    return RequestPolicyAssessment(
        version=REQUEST_POLICY_VERSION,
        directive="continue",
        rule_id="request_allowed",
        reason="No deterministic refusal, clarification, or human-authority rule matched.",
    )


def _requires_diagnostic_clarification(normalized: str) -> bool:
    asks_for_exact_cause = any(marker in normalized for marker in _EXACT_CAUSE_MARKERS)
    declares_missing_diagnostics = any(
        marker in normalized for marker in _MISSING_DIAGNOSTIC_MARKERS
    )
    return asks_for_exact_cause and declares_missing_diagnostics
