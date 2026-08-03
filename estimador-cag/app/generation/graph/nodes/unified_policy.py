"""Calibrated provider and context bootstrap for the unified graph."""

from __future__ import annotations

from collections.abc import Mapping

from app.generation.graph.nodes.session14_plus_policy import (
    build_session14_plus_context_source,
    derive_session14_plus_complexity_signals,
)
from app.generation.graph.unified_state import UnifiedEstimationGraphState
from app.schemas.session14_plus_policy import (
    ContextDetail,
    ModelCapabilityRegistry,
)
from app.schemas.v3_routing import ExecutionProfileV3
from app.services.session14_plus_policy import (
    build_context_compaction_event,
    compact_session14_context,
)
from app.services.unified_routing_policy import (
    UNIFIED_ROUTING_POLICY_VERSION,
    build_unified_model_routing_plan,
    validate_unified_routing_plan_capabilities,
)
from app.services.v3_complexity_router import assess_complexity


def build_unified_policy_bootstrap_node(
    *,
    capability_registry: ModelCapabilityRegistry,
    execution_profile: ExecutionProfileV3,
    context_detail: ContextDetail,
    repository_state: Mapping[str, str],
):
    """Build the server-owned policy bootstrap for the unified graph."""

    async def policy_bootstrap(
        state: UnifiedEstimationGraphState,
    ) -> UnifiedEstimationGraphState:
        assessment = assess_complexity(
            derive_session14_plus_complexity_signals(state)
        )
        plan = build_unified_model_routing_plan(
            assessment,
            profile=execution_profile,
        )
        authorized = validate_unified_routing_plan_capabilities(
            plan,
            capability_registry,
        )
        policy_update = UnifiedEstimationGraphState(
            plus_policy_version=UNIFIED_ROUTING_POLICY_VERSION,
            plus_execution_profile=execution_profile,
            plus_context_detail=context_detail,
            plus_complexity_assessment=assessment.model_dump(mode="json"),
            plus_routing_plan=plan.model_dump(mode="json"),
            plus_authorized_capabilities=authorized,
            unified_phase="bootstrap",
        )
        projected = {**dict(state), **dict(policy_update)}
        source = build_session14_plus_context_source(
            projected,
            source_revision=1,
            repository_state=repository_state,
        )
        context = compact_session14_context(
            source,
            detail=context_detail,
        )
        event = build_context_compaction_event(
            context,
            event_id=f"{source.identity['estimation_id']}:context:1",
        )
        policy_update.update(
            plus_context_source_revision=1,
            plus_compacted_context=context.model_dump(mode="json"),
            plus_context_compaction_events=[event.model_dump(mode="json")],
        )
        return policy_update

    return policy_bootstrap
