"""Provider-policy bootstrap and context-aware supervisor for Session 14 Plus."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy

from langgraph.types import Command

from app.generation.graph.nodes.session14_supervisor import build_supervisor_node
from app.generation.graph.ports import SupervisorRouteProposer
from app.generation.graph.session14_plus_state import (
    Session14PlusEstimationGraphState,
)
from app.schemas.session14_plus_policy import (
    ContextDetail,
    ModelCapabilityRegistry,
    Session14ContextSource,
)
from app.schemas.session14_supervision import SupervisorDestination
from app.schemas.v3_routing import ComplexitySignals, ExecutionProfileV3
from app.services.session14_human_review import (
    DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
)
from app.services.session14_plus_policy import (
    build_context_compaction_event,
    compact_session14_context,
    validate_routing_plan_capabilities,
)
from app.services.v3_complexity_router import (
    ROUTING_POLICY_VERSION,
    assess_complexity,
    build_model_routing_plan,
)

Session14PlusPolicyNode = Callable[
    [Session14PlusEstimationGraphState],
    Awaitable[Session14PlusEstimationGraphState],
]
Session14PlusSupervisorNode = Callable[
    [Session14PlusEstimationGraphState],
    Awaitable[Command[SupervisorDestination]],
]

_INTEGRATION_PATTERNS = (
    r"\bapi\b",
    r"\bintegrat(?:e|ion|ions)\b",
    r"\bkafka\b",
    r"\boauth\b",
    r"\bhsm\b",
    r"\bwebhook\b",
    r"\bthird[- ]party\b",
)
_NFR_PATTERNS = (
    r"\baudit(?:able|ability)?\b",
    r"\bavailability\b",
    r"\bcompliance\b",
    r"\blatency\b",
    r"\bperformance\b",
    r"\bsecurity\b",
    r"\bthroughput\b",
)
_AMBIGUITY_PATTERNS = (
    r"\bunknown\b",
    r"\bpending\b",
    r"\btbd\b",
    r"\bto be defined\b",
    r"\bnot specified\b",
)


def _pattern_count(text: str, patterns: tuple[str, ...]) -> int:
    return sum(
        len(re.findall(pattern, text, flags=re.IGNORECASE))
        for pattern in patterns
    )


def derive_session14_plus_complexity_signals(
    state: Mapping[str, object],
) -> ComplexitySignals:
    """Derive bounded deterministic signals without persisting raw transcript data."""

    transcript_value = state.get("transcript", "")
    transcript = transcript_value if isinstance(transcript_value, str) else ""
    requirements = state.get("requirements")
    components = state.get("components")
    requirement_count = len(requirements) if isinstance(requirements, list) else 0
    component_count = len(components) if isinstance(components, list) else 0
    ambiguity_count = _pattern_count(transcript, _AMBIGUITY_PATTERNS)
    integration_count = max(
        component_count,
        _pattern_count(transcript, _INTEGRATION_PATTERNS),
    )
    nfr_count = _pattern_count(transcript, _NFR_PATTERNS)
    lowered = transcript.lower()

    return ComplexitySignals(
        requirement_count=max(requirement_count, 1 if transcript.strip() else 0),
        integration_count=min(integration_count, 100),
        non_functional_requirement_count=min(nfr_count, 100),
        ambiguous_requirement_count=min(ambiguity_count, 100),
        missing_information_count=min(ambiguity_count, 100),
        contradiction_count=min(lowered.count("contradiction"), 100),
        attachment_count=0,
        detected_language_count=1,
        transcript_chars=len(transcript),
        compliance_or_security_critical=(
            "compliance" in lowered
            or "security critical" in lowered
            or "regulated" in lowered
        ),
        data_migration_required=(
            "data migration" in lowered or "migrate data" in lowered
        ),
        workflow_state_complexity=(
            "workflow" in lowered
            or "state machine" in lowered
            or "human review" in lowered
        ),
        evidence_scarcity=(
            state.get("budget_search_completed") is True
            and not state.get("budget_matches")
        ),
        novel_domain=("novel domain" in lowered),
    )


def _list_of_mappings(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _route_projection(state: Mapping[str, object]) -> dict[str, str]:
    raw_plan = state.get("plus_routing_plan")
    if not isinstance(raw_plan, Mapping):
        return {}
    raw_routes = raw_plan.get("routes_by_stage")
    if not isinstance(raw_routes, Mapping):
        return {}
    raw_route = raw_routes.get("proposal")
    if not isinstance(raw_route, Mapping):
        return {}
    projection: dict[str, str] = {}
    for key in ("provider", "model", "route_id", "mode", "effort"):
        value = raw_route.get(key)
        if isinstance(value, str) and value:
            projection[key] = value
    return projection


def build_session14_plus_context_source(
    state: Mapping[str, object],
    *,
    source_revision: int,
    repository_state: Mapping[str, str],
) -> Session14ContextSource:
    """Project graph state into the bounded authoritative input for compaction."""

    estimation_id = str(state.get("estimation_id", "")).strip()
    thread_id = str(state.get("thread_id", f"estimate:{estimation_id}")).strip()
    graph_version = str(state.get("graph_version", "session14.plus.v1")).strip()

    accepted_decisions: list[str] = []
    rejected_alternatives: list[str] = []
    for event in _list_of_mappings(state.get("route_events")):
        reason_code = str(event.get("reason_code", "unknown"))
        next_agent = str(event.get("next_agent", "unknown"))
        accepted_decisions.append(f"route:{reason_code}->{next_agent}")
        fallback = event.get("fallback_reason")
        proposed = event.get("proposed_agent")
        if fallback is not None:
            rejected_alternatives.append(
                f"proposal:{proposed or 'none'} rejected:{fallback}"
            )
    for action in _list_of_mappings(state.get("human_review_actions")):
        accepted_decisions.append(
            "human:"
            f"{action.get('action', 'unknown')}:"
            f"revision:{action.get('revision', 'unknown')}"
        )

    evidence_refs: list[str] = []
    for match in _list_of_mappings(state.get("budget_matches")):
        for prefix, key in (
            ("budget", "budget_id"),
            ("document", "source_document_id"),
            ("chunk", "source_chunk_id"),
        ):
            value = match.get(key)
            if isinstance(value, str) and value:
                evidence_refs.append(f"{prefix}:{value}")

    unresolved_questions = [
        f"review:{value}"
        for value in state.get("human_review_reason_codes", [])
        if isinstance(value, str) and value
    ]
    unresolved_questions.extend(
        f"issue:{item.get('code')}"
        for item in _list_of_mappings(state.get("errors"))
        if isinstance(item.get("code"), str) and item.get("code")
    )

    recent_events: list[str] = []
    for contribution in _list_of_mappings(state.get("agent_contributions")):
        recent_events.append(
            "agent:"
            f"{contribution.get('agent_id', 'unknown')}:"
            f"{contribution.get('execution_status', 'unknown')}"
        )
    recent_events.extend(accepted_decisions[-8:])

    validation = state.get("validation")
    validation_status = (
        str(validation.get("status", "unknown"))
        if isinstance(validation, Mapping)
        else "not_available"
    )
    next_agent = state.get("next_agent")
    next_action = (
        f"Execute {next_agent}."
        if isinstance(next_agent, str) and next_agent
        else "Await the next deterministic supervisor decision."
    )

    return Session14ContextSource(
        source_revision=source_revision,
        identity={
            "estimation_id": estimation_id,
            "thread_id": thread_id,
            "graph_version": graph_version,
        },
        objective="Produce an auditable, evidence-grounded estimate.",
        working_mode="LIDR coursework + Session 14 Plus",
        hard_constraints=[
            "Python owns authoritative arithmetic and hard policy.",
            "The model cannot modify privileges or approve its own human gate.",
            "Checkpoint, evidence, and decision records remain source of truth.",
            "Provider switching requires a fresh compacted context.",
        ],
        accepted_decisions=accepted_decisions,
        rejected_alternatives=rejected_alternatives,
        evidence_refs=evidence_refs,
        current_state={
            "status": str(state.get("status", "pending")),
            "review_required": bool(state.get("review_required", False)),
            "confidence": (
                float(state["confidence"])
                if isinstance(state.get("confidence"), (int, float))
                and not isinstance(state.get("confidence"), bool)
                else None
            ),
            "routing_steps": int(state.get("routing_steps", 0)),
            "current_agent": str(state.get("current_agent") or "none"),
            "next_agent": str(state.get("next_agent") or "none"),
        },
        unresolved_questions=unresolved_questions,
        execution_budgets={
            "routing_steps": int(state.get("routing_steps", 0)),
            "max_routing_steps": int(state.get("max_routing_steps", 12)),
        },
        provider_route=_route_projection(state),
        repository_state=dict(repository_state),
        validation_state={
            "graph_status": str(state.get("status", "pending")),
            "validation_status": validation_status,
            "human_review_status": str(
                state.get("human_review_status", "not_requested")
            ),
        },
        checkpoint_state={
            "revision": int(state.get("human_review_revision", 1)),
            "context_source_revision": source_revision,
            "thread_id": thread_id,
        },
        next_action=next_action,
        rollback_boundary="session-14/pre-work",
        claim_boundary=(
            "Provider routes are policy-authorized; no provider superiority or "
            "production-readiness claim is made."
        ),
        recent_events=recent_events,
    )


def _context_update(
    state: Mapping[str, object],
    *,
    detail: ContextDetail,
    repository_state: Mapping[str, str],
    source_revision: int,
) -> Session14PlusEstimationGraphState:
    source = build_session14_plus_context_source(
        state,
        source_revision=source_revision,
        repository_state=repository_state,
    )
    context = compact_session14_context(source, detail=detail)
    estimation_id = source.identity["estimation_id"]
    event = build_context_compaction_event(
        context,
        event_id=f"{estimation_id}:context:{source_revision}",
    )
    return Session14PlusEstimationGraphState(
        plus_context_source_revision=source_revision,
        plus_compacted_context=context.model_dump(mode="json"),
        plus_context_compaction_events=[event.model_dump(mode="json")],
    )


def _project_accumulator_updates(
    state: Mapping[str, object],
    update: Mapping[str, object],
) -> dict[str, object]:
    projected = deepcopy(dict(state))
    projected.update(deepcopy(dict(update)))
    for key in (
        "route_events",
        "agent_contributions",
        "human_review_actions",
        "plus_context_compaction_events",
    ):
        current_items = state.get(key)
        incoming_items = update.get(key)
        if isinstance(current_items, list) and isinstance(incoming_items, list):
            projected[key] = [*deepcopy(current_items), *deepcopy(incoming_items)]
    return projected


def build_session14_plus_policy_bootstrap_node(
    *,
    capability_registry: ModelCapabilityRegistry,
    execution_profile: ExecutionProfileV3 = "balanced",
    context_detail: ContextDetail = "medium",
    repository_state: Mapping[str, str],
) -> Session14PlusPolicyNode:
    """Build the server-owned Plus policy bootstrap node."""

    async def policy_bootstrap(
        state: Session14PlusEstimationGraphState,
    ) -> Session14PlusEstimationGraphState:
        assessment = assess_complexity(
            derive_session14_plus_complexity_signals(state)
        )
        plan = build_model_routing_plan(
            assessment,
            profile=execution_profile,
        )
        authorized = validate_routing_plan_capabilities(
            plan,
            capability_registry,
        )
        policy_update = Session14PlusEstimationGraphState(
            plus_policy_version=ROUTING_POLICY_VERSION,
            plus_execution_profile=execution_profile,
            plus_context_detail=context_detail,
            plus_complexity_assessment=assessment.model_dump(mode="json"),
            plus_routing_plan=plan.model_dump(mode="json"),
            plus_authorized_capabilities=authorized,
        )
        projected = _project_accumulator_updates(state, policy_update)
        return Session14PlusEstimationGraphState(
            **policy_update,
            **_context_update(
                projected,
                detail=context_detail,
                repository_state=repository_state,
                source_revision=1,
            ),
        )

    return policy_bootstrap


def build_session14_plus_supervisor_node(
    *,
    context_detail: ContextDetail,
    repository_state: Mapping[str, str],
    route_proposer: SupervisorRouteProposer | None = None,
    confidence_threshold: float = DEFAULT_SESSION14_CONFIDENCE_THRESHOLD,
) -> Session14PlusSupervisorNode:
    """Augment the mandatory supervisor with fresh bounded context evidence."""

    base_supervisor = build_supervisor_node(
        route_proposer=route_proposer,
        confidence_threshold=confidence_threshold,
    )

    async def plus_supervisor(
        state: Session14PlusEstimationGraphState,
    ) -> Command[SupervisorDestination]:
        command = await base_supervisor(state)
        raw_update = command.update or {}
        if not isinstance(raw_update, Mapping):
            raise ValueError("supervisor update must be a mapping")
        projected = _project_accumulator_updates(state, raw_update)
        source_revision = int(state.get("plus_context_source_revision", 0)) + 1
        context_update = _context_update(
            projected,
            detail=context_detail,
            repository_state=repository_state,
            source_revision=source_revision,
        )
        return Command(
            goto=command.goto,
            update={**dict(raw_update), **dict(context_update)},
        )

    return plus_supervisor
