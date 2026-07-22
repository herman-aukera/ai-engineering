"""Sequential LangGraph runtime over product-local Energy Aware Chat nodes."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.energy_chat.audit_models import (
    DecisionLedgerEntry,
    EnergyCardV2,
    FinalAnswerProjection,
)
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
    RequestPolicyAssessment,
    SourceNeedResult,
)
from app.energy_chat.evaluation_nodes import (
    calculate_energy,
    decide_candidate,
    run_critic_panel,
)
from app.energy_chat.evidence_hardening import (
    CandidateCitationValidation,
    EvidenceBodyMetadata,
    build_project_evidence_metadata,
    metadata_without_body,
    validate_candidate_citations,
)
from app.energy_chat.evidence_nodes import (
    EvidenceRoute,
    determine_evidence_need,
    route_evidence,
    select_evidence_route,
)
from app.energy_chat.finalization_nodes import build_final_projection, record_decision
from app.energy_chat.graph_nodes import interpret_request, load_policy_and_constraints
from app.energy_chat.graph_state import (
    CandidateVersion,
    CostBudget,
    CriticPanelRecord,
    DecisionOutcome,
    EnergyChatGraphState,
    EnergyScoreRecord,
    ErrorRecord,
    GraphStatus,
    ProviderMetrics,
    RepairRequest,
    RepairResultRecord,
    RetryBudget,
    TraceEvent,
    append_unique_records,
    append_unique_values,
)
from app.energy_chat.human_gate import (
    HumanActionRequest,
    HumanGateMode,
    enable_human_gates,
)
from app.energy_chat.observability import NodeSpan
from app.energy_chat.repair_nodes import (
    RepairStrategy,
    apply_repair,
    finalize_repair,
    plan_repair,
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


def _reduce_repair_results(
    current: list[RepairResultRecord], incoming: list[RepairResultRecord]
) -> list[RepairResultRecord]:
    return append_unique_records(current, incoming, id_field="result_id")


def _reduce_trace_events(
    current: list[TraceEvent], incoming: list[TraceEvent]
) -> list[TraceEvent]:
    return append_unique_records(current, incoming, id_field="event_id")


def _reduce_node_spans(
    current: list[NodeSpan], incoming: list[NodeSpan]
) -> list[NodeSpan]:
    return append_unique_records(current, incoming, id_field="span_id")


def _reduce_evidence_metadata(
    current: list[EvidenceBodyMetadata], incoming: list[EvidenceBodyMetadata]
) -> list[EvidenceBodyMetadata]:
    return append_unique_records(current, incoming, id_field="evidence_ref")


def _reduce_citation_validations(
    current: list[CandidateCitationValidation],
    incoming: list[CandidateCitationValidation],
) -> list[CandidateCitationValidation]:
    return append_unique_records(current, incoming, id_field="candidate_id")


def _reduce_ledger_entries(
    current: list[DecisionLedgerEntry], incoming: list[DecisionLedgerEntry]
) -> list[DecisionLedgerEntry]:
    return append_unique_records(current, incoming, id_field="ledger_entry_id")


def _reduce_errors(
    current: list[ErrorRecord], incoming: list[ErrorRecord]
) -> list[ErrorRecord]:
    return append_unique_records(current, incoming, id_field="error_id")


class EnergyChatRuntimeState(TypedDict):
    """LangGraph wiring schema; domain validation remains authoritative."""

    schema_version: str
    contract_version: str
    thread_id: str
    request_id: str
    trace_id: str
    user_request: str
    mode: Mode
    policy_version: str
    request_policy: RequestPolicyAssessment | None
    constraints: list[str]
    evidence_refs: Annotated[list[str], _reduce_evidence_refs]
    evidence_body_metadata: Annotated[
        list[EvidenceBodyMetadata], _reduce_evidence_metadata
    ]
    citation_validations: Annotated[
        list[CandidateCitationValidation], _reduce_citation_validations
    ]
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
    repair_results: Annotated[list[RepairResultRecord], _reduce_repair_results]
    retry_budget: RetryBudget
    cost_budget: CostBudget
    trace_events: Annotated[list[TraceEvent], _reduce_trace_events]
    node_spans: Annotated[list[NodeSpan], _reduce_node_spans]
    decision_ledger_entries: Annotated[list[DecisionLedgerEntry], _reduce_ledger_entries]
    errors: Annotated[list[ErrorRecord], _reduce_errors]
    final_answer: str | None
    energy_card: EnergyCard | None
    energy_card_v2: EnergyCardV2 | None
    final_projection: FinalAnswerProjection | None
    human_action_request: HumanActionRequest | None
    human_action_result: HumanActionRequest | None
    human_action_turn: int
    status: GraphStatus


def build_energy_chat_graph(
    *,
    provider: CandidateProvider | None = None,
    budget: ProviderBudget | None = None,
    repair_strategy: RepairStrategy | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    human_gate_mode: HumanGateMode = "disabled",
    clock: Callable[[], float] | None = None,
):
    """Compile the graph with bounded repair, evidence integrity, and spans."""

    active_provider = provider or DeterministicCandidateProvider()
    active_budget = budget or ProviderBudget()
    active_clock = clock or time.perf_counter
    builder = StateGraph(EnergyChatRuntimeState)

    def observed(
        node_name: str,
        handler: Callable[[EnergyChatRuntimeState], dict[str, Any]],
    ) -> Callable[[EnergyChatRuntimeState], dict[str, Any]]:
        def run(state: EnergyChatRuntimeState) -> dict[str, Any]:
            started_at_ms = max(0, round(active_clock() * 1000))
            update = handler(state)
            finished_at_ms = max(started_at_ms, round(active_clock() * 1000))
            occurrence = (
                sum(span.node_name == node_name for span in state.get("node_spans", []))
                + 1
            )
            update["node_spans"] = [
                NodeSpan(
                    span_id=f"{state['trace_id']}:{node_name}:{occurrence}",
                    node_name=node_name,
                    started_at_ms=started_at_ms,
                    finished_at_ms=finished_at_ms,
                )
            ]
            return update

        return run

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
            "request_policy": delta.request_policy,
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
        state: EnergyChatRuntimeState,
        expected_route: EvidenceRoute,
    ) -> dict[str, Any]:
        delta = route_evidence(_domain_state(state))
        if delta.route != expected_route:
            raise ValueError(
                f"Evidence branch changed from {expected_route!r} to {delta.route!r}"
            )
        metadata = build_project_evidence_metadata(delta.project_rag)
        hashed_refs = {item.evidence_ref for item in metadata}
        metadata.extend(
            metadata_without_body(
                evidence_ref,
                permitted=True,
            )
            for evidence_ref in delta.evidence_refs
            if evidence_ref not in hashed_refs
        )
        update: dict[str, Any] = {
            "evidence_refs": delta.evidence_refs,
            "evidence_body_metadata": metadata,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }
        if delta.project_rag is not None:
            update["project_rag"] = delta.project_rag
        return update

    def candidate_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = generate_candidate(
            _domain_state(state),
            provider=active_provider,
            budget=active_budget,
        )
        candidate = delta.candidate_versions[-1]
        validation = validate_candidate_citations(
            candidate_id=candidate.candidate_id,
            answer_text=candidate.answer,
            known_evidence_refs=candidate.evidence_refs,
        )
        return {
            "candidate_versions": delta.candidate_versions,
            "active_candidate_id": delta.active_candidate_id,
            "provider_metrics": delta.provider_metrics,
            "evidence_refs": delta.evidence_refs,
            "citation_validations": [validation],
            "cost_budget": delta.cost_budget,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def critic_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        domain = _domain_state(state)
        if domain.active_candidate_id is None:
            raise ValueError("Critic panel requires an active candidate")
        candidate = next(
            item
            for item in domain.candidate_versions
            if item.candidate_id == domain.active_candidate_id
        )
        validation = validate_candidate_citations(
            candidate_id=candidate.candidate_id,
            answer_text=candidate.answer,
            known_evidence_refs=candidate.evidence_refs,
        )
        delta = run_critic_panel(domain)
        return {
            "critic_panels": delta.critic_panels,
            "critic_findings": delta.critic_panels[0].findings,
            "citation_validations": [validation],
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

    def repair_plan_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = plan_repair(_domain_state(state), strategy=repair_strategy)
        return {
            "repair_requests": delta.repair_requests,
            "repair_results": delta.repair_results,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def repair_apply_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = apply_repair(_domain_state(state))
        return {
            "candidate_versions": delta.candidate_versions,
            "active_candidate_id": delta.active_candidate_id,
            "retry_budget": delta.retry_budget,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def repair_finalize_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = finalize_repair(_domain_state(state))
        return {
            "repair_results": delta.repair_results,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def human_action_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        domain = _domain_state(state)
        turn = domain.human_action_turn + 1
        last_decision = domain.decision_outcomes[-1]
        action_type: str = "clarify_response"
        if last_decision.disposition == "escalate":
            action_type = "escalate_response"
        request = HumanActionRequest(
            action_id=f"{domain.trace_id}:human:{turn}",
            action=action_type,  # type: ignore[arg-type]
            reason=(
                f"Decision {last_decision.decision_id} requires human action: "
                f"{last_decision.reason}"
            ),
            expected_revision=turn,
        )
        response = interrupt(request)
        if not isinstance(response, HumanActionRequest):
            raise ValueError(
                "Human gate resume requires a HumanActionRequest, "
                f"got {type(response).__name__}"
            )
        return {
            "human_action_request": request,
            "human_action_result": response,
            "human_action_turn": turn,
            "status": "evaluated",
        }

    def ledger_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = record_decision(_domain_state(state))
        return {
            "decision_ledger_entries": delta.decision_ledger_entries,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    def projection_node(state: EnergyChatRuntimeState) -> dict[str, Any]:
        delta = build_final_projection(_domain_state(state))
        return {
            "final_answer": delta.final_answer,
            "energy_card": delta.energy_card,
            "energy_card_v2": delta.energy_card_v2,
            "final_projection": delta.final_projection,
            "status": delta.status,
            "trace_events": delta.trace_events,
        }

    builder.add_node("interpret_request", observed("interpret_request", interpret_node))
    builder.add_node(
        "load_policy_and_constraints",
        observed("load_policy_and_constraints", policy_node),
    )
    builder.add_node(
        "determine_evidence_need",
        observed("determine_evidence_need", evidence_need_node),
    )
    builder.add_node(
        "skip_evidence",
        observed(
            "skip_evidence",
            lambda state: evidence_route_node(state, "skip"),
        ),
    )
    builder.add_node(
        "retrieve_project_evidence",
        observed(
            "retrieve_project_evidence",
            lambda state: evidence_route_node(state, "retrieve_project"),
        ),
    )
    builder.add_node(
        "await_external_evidence",
        observed(
            "await_external_evidence",
            lambda state: evidence_route_node(state, "external_required"),
        ),
    )
    builder.add_node("generate_candidate", observed("generate_candidate", candidate_node))
    builder.add_node("run_critic_panel", observed("run_critic_panel", critic_node))
    builder.add_node("calculate_energy", observed("calculate_energy", score_node))
    builder.add_node("decide_candidate", observed("decide_candidate", decision_node))
    builder.add_node("plan_repair", observed("plan_repair", repair_plan_node))
    builder.add_node("apply_repair", observed("apply_repair", repair_apply_node))
    builder.add_node("finalize_repair", observed("finalize_repair", repair_finalize_node))
    builder.add_node(
        "request_human_action",
        observed("request_human_action", human_action_node),
    )
    builder.add_node("record_decision", observed("record_decision", ledger_node))
    builder.add_node(
        "build_final_projection",
        observed("build_final_projection", projection_node),
    )

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

    def route_decision(
        state: EnergyChatRuntimeState,
    ) -> Literal["end", "repair", "finalize", "human"]:
        domain = _domain_state(state)
        if domain.active_candidate_id is None:
            return "end"
        decision = next(
            item
            for item in reversed(domain.decision_outcomes)
            if item.candidate_id == domain.active_candidate_id
        )
        repaired_candidate = any(
            request.target_candidate_id == domain.active_candidate_id
            for request in domain.repair_requests
        )
        if repaired_candidate:
            return "finalize"
        if decision.disposition == "repair":
            return "repair" if domain.retry_budget.remaining > 0 else "finalize"
        if decision.disposition in ("clarify", "escalate") and enable_human_gates(
            human_gate_mode
        ):
            return "human"
        return "end"

    builder.add_conditional_edges(
        "decide_candidate",
        route_decision,
        {
            "end": "record_decision",
            "repair": "plan_repair",
            "finalize": "finalize_repair",
            "human": "request_human_action",
        },
    )
    builder.add_conditional_edges(
        "plan_repair",
        _repair_plan_route,
        {"apply": "apply_repair", "end": "record_decision"},
    )
    builder.add_edge("apply_repair", "run_critic_panel")
    builder.add_edge("finalize_repair", "record_decision")
    builder.add_edge("request_human_action", "record_decision")
    builder.add_edge("record_decision", "build_final_projection")
    builder.add_edge("build_final_projection", END)
    return builder.compile(checkpointer=checkpointer)


def run_energy_chat_graph(
    state: EnergyChatGraphState,
    *,
    provider: CandidateProvider | None = None,
    budget: ProviderBudget | None = None,
    repair_strategy: RepairStrategy | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    human_gate_mode: HumanGateMode = "disabled",
    clock: Callable[[], float] | None = None,
) -> EnergyChatGraphState:
    """Run and validate the complete graph state."""

    config: dict[str, object] | None = None
    if checkpointer is not None:
        config = {"configurable": {"thread_id": state.thread_id}}
    result = build_energy_chat_graph(
        provider=provider,
        budget=budget,
        repair_strategy=repair_strategy,
        checkpointer=checkpointer,
        human_gate_mode=human_gate_mode,
        clock=clock,
    ).invoke(_runtime_payload(state), config)
    return EnergyChatGraphState.model_validate(result)


def _start_route(state: EnergyChatRuntimeState) -> Literal["run", "complete"]:
    projection = state.get("final_projection")
    return "complete" if state["status"] == "evaluated" and projection is not None else "run"


def _evidence_route(state: EnergyChatRuntimeState) -> EvidenceRoute:
    source_need = state.get("source_need")
    if source_need is None:
        raise ValueError("Evidence need is missing at the conditional route")
    return select_evidence_route(source_need)


def _repair_plan_route(state: EnergyChatRuntimeState) -> Literal["apply", "end"]:
    return "apply" if state["status"] == "repair_requested" else "end"


def _domain_state(state: EnergyChatRuntimeState) -> EnergyChatGraphState:
    return EnergyChatGraphState.model_validate(state)


def _runtime_payload(state: EnergyChatGraphState) -> EnergyChatRuntimeState:
    return {
        field_name: getattr(state, field_name)
        for field_name in EnergyChatRuntimeState.__annotations__
    }  # type: ignore[return-value]
