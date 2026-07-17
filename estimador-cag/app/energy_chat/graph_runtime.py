"""Sequential LangGraph runtime over product-local Energy Aware Chat nodes."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.energy_chat.candidate_node import generate_candidate
from app.energy_chat.candidate_provider import (
    CandidateProvider,
    DeterministicCandidateProvider,
    ProviderBudget,
)
from app.energy_chat.contracts import (
    CriticFinding,
    EnergyCard,
    Mode,
    ProjectRagResult,
    SourceNeedResult,
)
from app.energy_chat.evaluation_nodes import calculate_energy, decide_candidate, run_critic_panel
from app.energy_chat.evidence_nodes import (
    EvidenceRoute,
    determine_evidence_need,
    route_evidence,
    select_evidence_route,
)
from app.energy_chat.graph_nodes import interpret_request, load_policy_and_constraints
from app.energy_chat.graph_state import (
    CandidateVersion,
    CriticPanelRecord,
    DecisionOutcome,
    EnergyChatGraphState,
    EnergyScoreRecord,
    ErrorRecord,
    GraphStatus,
    ProviderMetrics,
    RepairRequest,
    TraceEvent,
    append_unique_records,
    append_unique_values,
)


def _reduce_evidence_refs(current: list[str], incoming: list[str]) -> list[str]:
    return append_unique_values(current, incoming)


def _reduce_candidates(
    current: list[CandidateVersion], incoming: list[CandidateVersion]
) -> list[CandidateVersion]:
    return append_unique_records(current, incoming, id_field="candidate_id")


def _reduce_provider_metrics(
    current: list[ProviderMetrics], incoming: list[ProviderMetrics]
) -> list[ProviderMetrics]:
    return append_unique_records(current, incoming, id_field="provider_call_id")


def _reduce_critic_panels(
    current: list[CriticPanelRecord], incoming: list[CriticPanelRecord]
) -> list[CriticPanelRecord]:
    return append_unique_records(current, incoming, id_field="panel_id")


def _reduce_energy_scores(
    current: list[EnergyScoreRecord], incoming: list[EnergyScoreRecord]
) -> list[EnergyScoreRecord]:
    return append_unique_records(current, incoming, id_field="score_id")


def _reduce_decisions(
    current: list[DecisionOutcome], incoming: list[DecisionOutcome]
) -> list[DecisionOutcome]:
    return append_unique_records(current, incoming, id_field="decision_id")


def _reduce_repairs(
    current: list[RepairRequest], incoming: list[RepairRequest]
) -> list[RepairRequest]:
    return append_unique_records(current, incoming, id_field="repair_id")


def _reduce_trace_events(
    current: list[TraceEvent], incoming: list[TraceEvent]
) -> list[TraceEvent]:
    return append_unique_records(current, incoming, id_field="event_id")


def _reduce_errors(
    current: list[ErrorRecord], incoming: list[ErrorRecord]
) -> list[ErrorRecord]:
    return append_unique_records(current, incoming, id_field="error_id")


class EnergyChatRuntimeState(TypedDict):
    """LangGraph wiring schema; domain validation remains in EnergyChatGraphState."""

    schema_version: str
    contract_version: str
    thread_id: str
    request_id: str
    trace_id: str
    user_request: str
    mode: Mode
    policy_version: str
    constraints: list[str]
    evidence_refs: Annotated[list[str], _reduce_evidence_refs]
    source_need: SourceNeedResult | None
    project_rag: ProjectRagResult | None
    candidate_versions: Annotated[list[CandidateVersion], _reduce_candidates]
    active_candidate_id: str | None
    provider_metrics: Annotated[list[ProviderMetrics], _reduce_provider_metrics]
    critic_findings: list[CriticFinding]
    critic_panels: Annotated[list[CriticPanelRecord], _reduce_critic_panels]
    energy_scores: Annotated[list[EnergyScoreRecord], _reduce_energy_scores]
    decision_outcomes: Annotated[list[DecisionOutcome], _reduce_decisions]
    repair_requests: Annotated[list[RepairRequest], _reduce_repairs]
    trace_events: Annotated[list[TraceEvent], _reduce_trace_events]
    errors: Annotated[list[ErrorRecord], _reduce_errors]
    final_answer: str | None
    energy_card: EnergyCard | None
    status: GraphStatus


def build_energy_chat_graph(
    *,
    provider: CandidateProvider | None = None,
    budget: ProviderBudget | None = None,
):
    """Compile the provider-injected sequential graph without persistence or repair loops."""

    active_provider = provider or DeterministicCandidateProvider()
    active_budget = budget or ProviderBudget()
    builder = StateGraph(EnergyChatRuntimeState)

    def interpret_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = interpret_request(_domain_state(state))
        return {
            "user_request": delta.user_request,
            "mode": delta.mode,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def policy_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = load_policy_and_constraints(_domain_state(state))
        return {
            "policy_version": delta.policy_version,
            "constraints": delta.constraints,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def evidence_need_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = determine_evidence_need(_domain_state(state))
        return {
            "source_need": delta.source_need,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def evidence_route_node(
        state: EnergyChatRuntimeState, expected_route: EvidenceRoute
    ) -> dict[str, Any]:
        delta = route_evidence(_domain_state(state))
        if delta.route != expected_route:
            raise ValueError(
                f"Evidence branch changed from {expected_route!r} to {delta.route!r}"
            )
        update: dict[str, Any] = {
            "evidence_refs": delta.evidence_refs,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }
        if delta.project_rag is not None:
            update["project_rag"] = delta.project_rag
        return update

    def candidate_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = generate_candidate(
            _domain_state(state), provider=active_provider, budget=active_budget
        )
        return {
            "candidate_versions": delta.candidate_versions,
            "active_candidate_id": delta.active_candidate_id,
            "provider_metrics": delta.provider_metrics,
            "evidence_refs": delta.evidence_refs,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def critic_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = run_critic_panel(_domain_state(state))
        return {
            "critic_panels": delta.critic_panels,
            "critic_findings": delta.critic_panels[0].findings,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def score_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = calculate_energy(_domain_state(state))
        return {
            "energy_scores": delta.energy_scores,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def decision_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = decide_candidate(_domain_state(state))
        return {
            "decision_outcomes": delta.decision_outcomes,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    builder.add_node("interpret_request", interpret_node)
    builder.add_node("load_policy_and_constraints", policy_node)
    builder.add_node("determine_evidence_need", evidence_need_node)
    builder.add_node(
        "skip_evidence", lambda state: evidence_route_node(state, "skip")
    )
    builder.add_node(
        "retrieve_project_evidence",
        lambda state: evidence_route_node(state, "retrieve_project"),
    )
    builder.add_node(
        "await_external_evidence",
        lambda state: evidence_route_node(state, "external_required"),
    )
    builder.add_node("generate_candidate", candidate_node)
    builder.add_node("run_critic_panel", critic_node)
    builder.add_node("calculate_energy", score_node)
    builder.add_node("decide_candidate", decision_node)

    builder.add_conditional_edges(
        START,
        _start_route,
        {"run": "interpret_request", "complete": END},
    )
    builder.add_edge("interpret_request", "load_policy_and_constraints")
    builder.add_edge("load_policy_and_constraints", "determine_evidence_need")
    builder.add_conditional_edges(
        "determine_evidence_need",
        _evidence_route,
        {
            "skip": "skip_evidence",
            "retrieve_project": "retrieve_project_evidence",
            "external_required": "await_external_evidence",
        },
    )
    builder.add_edge("skip_evidence", "generate_candidate")
    builder.add_edge("retrieve_project_evidence", "generate_candidate")
    builder.add_edge("await_external_evidence", END)
    builder.add_edge("generate_candidate", "run_critic_panel")
    builder.add_edge("run_critic_panel", "calculate_energy")
    builder.add_edge("calculate_energy", "decide_candidate")
    builder.add_edge("decide_candidate", END)
    return builder.compile()


def run_energy_chat_graph(
    state: EnergyChatGraphState,
    *,
    provider: CandidateProvider | None = None,
    budget: ProviderBudget | None = None,
) -> EnergyChatGraphState:
    """Run the sequential graph and validate its complete domain state output."""

    result = build_energy_chat_graph(provider=provider, budget=budget).invoke(
        _runtime_payload(state)
    )
    return EnergyChatGraphState.model_validate(result)


def _start_route(state: EnergyChatRuntimeState) -> Literal["run", "complete"]:
    return "complete" if state["status"] == "evaluated" else "run"


def _evidence_route(state: EnergyChatRuntimeState) -> EvidenceRoute:
    source_need = state.get("source_need")
    if source_need is None:
        raise ValueError("Evidence need is missing at the conditional route")
    return select_evidence_route(source_need)


def _domain_state(state: EnergyChatRuntimeState) -> EnergyChatGraphState:
    return EnergyChatGraphState.model_validate(state)


def _runtime_payload(state: EnergyChatGraphState) -> EnergyChatRuntimeState:
    return {
        field_name: getattr(state, field_name)
        for field_name in EnergyChatRuntimeState.__annotations__
    }  # type: ignore[return-value]
