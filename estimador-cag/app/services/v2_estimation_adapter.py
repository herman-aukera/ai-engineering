"""Project one durable reviewed graph run into the canonical V2 domain."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from app.schemas.v2_estimation import (
    AuditMetadataV2,
    BudgetEvidenceV2,
    EstimationStage,
    EstimationV2,
    ExecutionPolicyV2,
    HumanDecisionV2,
    ProviderUsageV2,
    RequirementV2,
    ScenarioLineageV2,
    SourceProvenanceV2,
    TaskEstimateV2,
    TaskV2,
    WorkModuleV2,
)
from app.services.reviewed_graph_estimation import ReviewedGraphRun

PROFILE_POLICIES: dict[str, ExecutionPolicyV2] = {
    "cost_first": ExecutionPolicyV2(
        profile="cost_first", primary_provider="deepseek", fallback_provider="kimi",
        retry_limit=1, timeout_seconds=30, max_concurrency=4, tool_call_limit=4,
        cost_limit_usd=0.25, confidence_threshold=0.65, human_review_mode="risk_based",
    ),
    "balanced": ExecutionPolicyV2(
        profile="balanced", primary_provider="deepseek", fallback_provider="kimi",
        retry_limit=2, timeout_seconds=45, max_concurrency=4, tool_call_limit=8,
        cost_limit_usd=1.0, confidence_threshold=0.75, human_review_mode="risk_based",
    ),
    "quality_first": ExecutionPolicyV2(
        profile="quality_first", primary_provider="kimi", fallback_provider="deepseek",
        retry_limit=2, timeout_seconds=60, max_concurrency=6, tool_call_limit=12,
        cost_limit_usd=3.0, confidence_threshold=0.85, human_review_mode="risk_based",
    ),
    "human_controlled": ExecutionPolicyV2(
        profile="human_controlled", primary_provider="deepseek", fallback_provider="kimi",
        retry_limit=1, timeout_seconds=45, max_concurrency=4, tool_call_limit=8,
        cost_limit_usd=1.0, confidence_threshold=0.75, human_review_mode="required",
    ),
}


def policy_for_profile(profile: str) -> ExecutionPolicyV2:
    return PROFILE_POLICIES[profile].model_copy(deep=True)


def _stage(run: ReviewedGraphRun) -> EstimationStage:
    gates = [item.get("value", {}).get("gate") for item in run.interrupts]
    if "structure_review" in gates:
        return "structure"
    if "final_estimate_review" in gates:
        return "human_approval"
    if run.execution_status == "completed":
        return "completed"
    return "estimation"


def _evidence_by_component(state: Mapping[str, Any]) -> dict[str, list[BudgetEvidenceV2]]:
    grouped: dict[str, list[BudgetEvidenceV2]] = defaultdict(list)
    for raw in state.get("budget_matches", []) or []:
        if not isinstance(raw, Mapping):
            continue
        component_id = str(raw.get("component_id") or "")
        evidence_id = ":".join(
            str(raw.get(key) or "unknown")
            for key in ("budget_id", "source_document_id", "source_chunk_id")
        )
        grouped[component_id].append(
            BudgetEvidenceV2(
                evidence_id=evidence_id,
                recorded_hours=raw.get("recorded_hours"),
                provenance=SourceProvenanceV2(
                    evidence_id=evidence_id,
                    budget_id=raw.get("budget_id"),
                    source_document_id=raw.get("source_document_id"),
                    source_chunk_id=raw.get("source_chunk_id"),
                    retrieval_method=raw.get("retrieval_method"),
                    score=raw.get("score"),
                ),
            )
        )
    return grouped


def _modules(state: Mapping[str, Any]) -> list[WorkModuleV2]:
    estimates = {
        str(item.get("component_id")): item
        for item in state.get("component_estimates", []) or []
        if isinstance(item, Mapping)
    }
    evidence = _evidence_by_component(state)
    modules: list[WorkModuleV2] = []
    for raw in state.get("components", []) or []:
        if not isinstance(raw, Mapping):
            continue
        component_id = str(raw.get("component_id"))
        estimate = estimates.get(component_id)
        task_estimate = None
        if estimate:
            expected = estimate.get("hours")
            low = estimate.get("source_range_low")
            high = estimate.get("source_range_high")
            task_estimate = TaskEstimateV2(
                hours_low=low if low is not None else expected,
                hours_expected=expected,
                hours_high=high if high is not None else expected,
                hourly_rate_eur=0,
                confidence=float(estimate.get("confidence") or 0),
                derivation_method=estimate.get("derivation_method"),
            )
        task = TaskV2(
            task_id=f"task:{component_id}",
            name=str(raw.get("name") or component_id),
            description=None,
            category=str(raw.get("category") or "uncategorized"),
            requirement_ids=list(raw.get("requirement_ids") or []),
            estimate=task_estimate,
            evidence=evidence.get(component_id, []),
            active_finding_codes=[
                str(issue.get("code"))
                for issue in (state.get("critic_report", {}) or {}).get("issues", [])
                if isinstance(issue, Mapping) and component_id in issue.get("component_ids", [])
            ],
            review_status=str(estimate.get("grounding_status") if estimate else "pending"),
        )
        modules.append(
            WorkModuleV2(
                module_id=component_id,
                name=str(raw.get("name") or component_id),
                tasks=[task],
            )
        )
    return modules


def _human_decisions(state: Mapping[str, Any]) -> list[HumanDecisionV2]:
    decisions: list[HumanDecisionV2] = []
    for gate, key in (("structure", "structure_review_record"), ("final", "final_review_record")):
        raw = state.get(key)
        if isinstance(raw, Mapping) and raw.get("action"):
            decisions.append(
                HumanDecisionV2(
                    gate=gate,
                    action=str(raw["action"]),
                    revision=int(raw.get("revision") or 0),
                    actor=raw.get("actor"),
                    reason=raw.get("reason"),
                    changes=list(raw.get("changes") or []),
                )
            )
    return decisions


def canonical_estimation_from_run(
    run: ReviewedGraphRun,
    *,
    profile: str | None = None,
    checkpoint_count: int = 0,
) -> EstimationV2:
    state: dict[str, Any] = dict(run.state)
    for interrupt_payload in run.interrupts:
        value = interrupt_payload.get("value")
        if not isinstance(value, Mapping):
            continue
        if value.get("gate") == "structure_review":
            if not state.get("requirements"):
                state["requirements"] = list(value.get("requirements") or [])
            if not state.get("components"):
                state["components"] = list(value.get("components") or [])
    resolved_profile = profile or str(state.get("v2_profile") or "balanced")
    policy = policy_for_profile(resolved_profile)
    policy = policy.model_copy(
        update={"human_review_mode": state.get("human_review_mode", policy.human_review_mode)}
    )
    provider = state.get("provider_metadata") or {}
    usage = []
    if isinstance(provider, Mapping) and provider.get("provider"):
        usage.append(ProviderUsageV2(provider=str(provider["provider"]), model=provider.get("model")))
    return EstimationV2(
        estimation_id=run.estimation_id,
        thread_id=run.thread_id,
        execution_status=run.execution_status,
        stage=_stage(run),
        graph_status=state.get("status", "pending"),
        revision=max(
            int(state.get("structure_review_revision") or 0),
            int(state.get("final_review_revision") or 0),
        ),
        requirements=[
            RequirementV2.model_validate(item) for item in state.get("requirements", []) or []
        ],
        modules=_modules(state),
        critic_report=dict(state.get("critic_report") or {}),
        boss_decision=dict(state.get("boss_decision") or {}),
        human_decisions=_human_decisions(state),
        execution_policy=policy,
        provider_usage=usage,
        lineage=ScenarioLineageV2(
            scenario_id=state.get("scenario_id"),
            parent_estimation_id=state.get("parent_estimation_id"),
            parent_checkpoint_id=state.get("parent_checkpoint_id"),
        ),
        audit=AuditMetadataV2(
            graph_version=str(state.get("graph_version") or "unknown"),
            checkpoint_count=checkpoint_count,
        ),
    )
