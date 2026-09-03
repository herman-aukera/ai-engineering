from __future__ import annotations

from app.energy_chat.candidate_provider import (
    CandidateGenerationResult,
    CandidateProviderRequest,
)
from app.energy_chat.graph_runtime import run_energy_chat_graph
from app.energy_chat.graph_state import EnergyChatGraphState, ProviderMetrics, RetryBudget
from app.energy_chat.policies import assess_request_policy


class SupportAnswerProvider:
    def generate(self, request: CandidateProviderRequest) -> CandidateGenerationResult:
        return CandidateGenerationResult(
            answer=(
                "The available evidence supports bounded diagnostic checks rather than an "
                "unverified conclusion. Next action: collect the missing incident evidence "
                "and continue through the authorized support workflow."
            ),
            evidence_refs=request.evidence_refs,
            metrics=ProviderMetrics(
                provider_call_id=request.provider_call_id,
                provider="fake",
                model="final-project-disposition-v1",
                tier="local",
            ),
        )


def _run(user_request: str):
    return run_energy_chat_graph(
        EnergyChatGraphState(
            thread_id="final-project-thread",
            request_id="final-project-request",
            trace_id="final-project-trace",
            user_request=user_request,
            mode="project",
            policy_version="unresolved",
            retry_budget=RetryBudget(max_attempts=1),
        ),
        provider=SupportAnswerProvider(),
    )


def test_missing_incident_evidence_clarifies_instead_of_inventing_root_cause() -> None:
    state = _run(
        "The service cannot connect to PostgreSQL. We have no logs or error message. "
        "Give me the exact root cause."
    )

    outcome = state.decision_outcomes[-1]
    assert outcome.disposition == "clarify"
    assert outcome.policy_rule_id == "diagnostic_evidence_required"
    assert "diagnostic evidence" in outcome.reason.casefold()


def test_java_source_patch_request_escalates_beyond_l2_authority() -> None:
    state = _run("Our Spring Boot service is failing. Patch the Java source code for me.")

    outcome = state.decision_outcomes[-1]
    assert outcome.disposition == "escalate"
    assert outcome.policy_rule_id == "l3_source_code_remediation"
    assert "l2 support boundary" in outcome.reason.casefold()


def test_kubernetes_request_escalates_as_unsupported_final_project_scope() -> None:
    state = _run(
        "Our Kubernetes deployment is crash-looping. Diagnose the cluster and change the deployment for me."
    )

    outcome = state.decision_outcomes[-1]
    assert outcome.disposition == "escalate"
    assert outcome.policy_rule_id == "unsupported_l2_technology"


def test_normal_supported_question_remains_allowed_by_request_policy() -> None:
    assessment = assess_request_policy(
        "Which PostgreSQL connection limits should I inspect when the pool is exhausted?"
    )

    assert assessment.directive == "continue"
    assert assessment.rule_id == "request_allowed"
