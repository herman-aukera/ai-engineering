"""Unified additive API over the durable reviewed estimation graph."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.generation.graph.nodes.final_estimate_review import StaleFinalEstimateReviewError
from app.generation.graph.nodes.structure_review import StaleStructureReviewError
from app.routers.reviewed_graph_estimations import get_reviewed_graph_estimation_service
from app.schemas.human_review import FinalEstimateReviewDecision, StructureReviewDecision
from app.schemas.reviewed_graph_estimation import (
    ReviewedScenarioBranchRequest,
    ReviewedScenarioComparisonRequest,
)
from app.schemas.v2_estimation import (
    CheckpointSummaryV2,
    EstimationV2ActionRequest,
    EstimationV2CheckpointHistory,
    EstimationV2CreateRequest,
    EstimationV2Response,
)
from app.services.audit_export import build_estimation_audit_packet
from app.services.reviewed_graph_estimation import (
    ReviewedGraphEstimationApplication,
    ReviewedGraphNotFoundError,
)
from app.services.v2_estimation_adapter import canonical_estimation_from_run, policy_for_profile

router = APIRouter(prefix="/api/v2", tags=["estimations-v2"])


def _response(run) -> EstimationV2Response:
    estimation = canonical_estimation_from_run(run)
    if estimation.stage == "structure":
        next_actions = ["approve", "edit", "reject", "regenerate"]
    elif estimation.stage == "human_approval":
        next_actions = ["approve", "override", "request_recovery", "reject"]
    else:
        next_actions = []
    return EstimationV2Response(
        estimation=estimation,
        next_actions=next_actions,
        interrupts=list(run.interrupts),
    )


@router.post("/estimations", response_model=EstimationV2Response)
async def create_estimation_v2(
    payload: EstimationV2CreateRequest,
    service: ReviewedGraphEstimationApplication = Depends(get_reviewed_graph_estimation_service),
) -> EstimationV2Response:
    policy = policy_for_profile(payload.profile)
    run = await service.start(
        transcript=payload.context.transcript,
        human_review_mode=policy.human_review_mode,
        estimation_id=payload.estimation_id,
        v2_profile=payload.profile,
    )
    return _response(run)


@router.get("/estimations/{estimation_id}", response_model=EstimationV2Response)
async def inspect_estimation_v2(
    estimation_id: UUID,
    service: ReviewedGraphEstimationApplication = Depends(get_reviewed_graph_estimation_service),
) -> EstimationV2Response:
    try:
        return _response(await service.inspect(estimation_id=estimation_id))
    except ReviewedGraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _structure_decision(payload: EstimationV2ActionRequest) -> StructureReviewDecision:
    requirements = (
        [item.model_dump(mode="json") for item in payload.requirements]
        if payload.requirements is not None
        else None
    )
    components = None
    if payload.modules is not None:
        components = [
            {
                "component_id": module.module_id,
                "name": module.name,
                "category": module.tasks[0].category if module.tasks else "uncategorized",
                "requirement_ids": sorted(
                    {
                        requirement_id
                        for task in module.tasks
                        for requirement_id in task.requirement_ids
                    }
                ),
            }
            for module in payload.modules
        ]
    return StructureReviewDecision.model_validate(
        {
            "action": payload.action,
            "expected_revision": payload.expected_revision,
            "reason": payload.reason,
            "requirements": requirements,
            "components": components,
        }
    )


def _final_decision(payload: EstimationV2ActionRequest) -> FinalEstimateReviewDecision:
    return FinalEstimateReviewDecision.model_validate(
        {
            "action": payload.action,
            "expected_revision": payload.expected_revision,
            "actor": payload.actor,
            "reason": payload.reason,
            "overrides": payload.overrides,
        }
    )


@router.post("/estimations/{estimation_id}/actions", response_model=EstimationV2Response)
async def act_on_estimation_v2(
    estimation_id: UUID,
    payload: EstimationV2ActionRequest,
    service: ReviewedGraphEstimationApplication = Depends(get_reviewed_graph_estimation_service),
) -> EstimationV2Response:
    try:
        if payload.gate == "structure":
            run = await service.resume_structure_review(
                estimation_id=estimation_id,
                decision=_structure_decision(payload),
            )
        else:
            run = await service.resume_final_review(
                estimation_id=estimation_id,
                decision=_final_decision(payload),
            )
        return _response(run)
    except ReviewedGraphNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (StaleStructureReviewError, StaleFinalEstimateReviewError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


@router.get(
    "/estimations/{estimation_id}/checkpoints",
    response_model=EstimationV2CheckpointHistory,
)
async def list_estimation_v2_checkpoints(
    estimation_id: UUID,
    limit: int = 50,
    service: ReviewedGraphEstimationApplication = Depends(get_reviewed_graph_estimation_service),
) -> EstimationV2CheckpointHistory:
    try:
        records = await service.checkpoint_history(estimation_id=estimation_id, limit=limit)
    except (LookupError, ReviewedGraphNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    checkpoints = []
    for item in records:
        state = item.state
        if state.get("final_review_status") in {"approved", "skipped"}:
            stage = "completed"
        elif state.get("component_estimates"):
            stage = "human_approval"
        elif state.get("components"):
            stage = "structure"
        else:
            stage = "context"
        checkpoints.append(
            CheckpointSummaryV2(
                checkpoint_id=item.checkpoint_id,
                created_at=item.created_at,
                next_nodes=list(item.next_nodes),
                stage=stage,
            )
        )
    return EstimationV2CheckpointHistory(estimation_id=estimation_id, checkpoints=checkpoints)


@router.post("/estimations/{estimation_id}/scenarios", response_model=EstimationV2Response)
async def branch_estimation_v2_scenario(
    estimation_id: UUID,
    payload: ReviewedScenarioBranchRequest,
    service: ReviewedGraphEstimationApplication = Depends(get_reviewed_graph_estimation_service),
) -> EstimationV2Response:
    try:
        return _response(
            await service.branch_scenario(
                estimation_id=estimation_id,
                checkpoint_id=payload.checkpoint_id,
                scenario_id=payload.scenario_id,
            )
        )
    except (LookupError, ReviewedGraphNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/estimations/scenarios/compare")
async def compare_estimation_v2_scenarios(
    payload: ReviewedScenarioComparisonRequest,
    service: ReviewedGraphEstimationApplication = Depends(get_reviewed_graph_estimation_service),
) -> dict[str, object]:
    return {
        "left_estimation_id": payload.left_estimation_id,
        "right_estimation_id": payload.right_estimation_id,
        "comparison": await service.compare_scenarios(
            left_estimation_id=payload.left_estimation_id,
            right_estimation_id=payload.right_estimation_id,
        ),
    }


@router.get("/estimations/{estimation_id}/audit")
async def export_estimation_v2_audit(
    estimation_id: UUID,
    service: ReviewedGraphEstimationApplication = Depends(get_reviewed_graph_estimation_service),
) -> dict[str, object]:
    try:
        run = await service.inspect(estimation_id=estimation_id)
        history = await service.checkpoint_history(estimation_id=estimation_id, limit=1)
    except (LookupError, ReviewedGraphNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    checkpoint_id = history[0].checkpoint_id if history else "unavailable"
    return {
        "packet": build_estimation_audit_packet(
            run.state,
            thread_id=run.thread_id,
            checkpoint_id=checkpoint_id,
            limitations=["V2 currently projects one task per reviewed graph component."],
        )
    }
