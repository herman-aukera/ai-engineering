from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.v2_estimation import TaskEstimateV2, TaskV2, WorkModuleV2
from app.services.v2_estimation_adapter import canonical_estimation_from_run
from scripts.session13_plus_demo_api import build_demo_service


def test_task_and_module_totals_are_python_owned() -> None:
    task = TaskV2(
        task_id="task-auth",
        name="Authentication",
        category="backend",
        estimate=TaskEstimateV2(
            hours_low=32,
            hours_expected=40,
            hours_high=48,
            hourly_rate_eur=100,
            confidence=0.9,
        ),
    )
    module = WorkModuleV2(
        module_id="module-auth",
        name="Authentication",
        tasks=[task],
    )

    assert task.estimate.cost_eur == 4000
    assert module.total_hours == 40
    assert module.total_cost_eur == 4000


def test_invalid_hour_range_is_rejected() -> None:
    with pytest.raises(ValidationError, match="hours_low"):
        TaskEstimateV2(
            hours_low=48,
            hours_expected=40,
            hours_high=32,
            hourly_rate_eur=100,
            confidence=0.9,
        )


@pytest.mark.asyncio
async def test_reviewed_graph_has_one_canonical_v2_projection() -> None:
    run = await build_demo_service().start(
        transcript="Build secure authentication with an auditable event trail.",
        human_review_mode="required",
    )

    canonical = canonical_estimation_from_run(run)

    assert str(canonical.estimation_id) == run.estimation_id
    assert canonical.thread_id == run.thread_id
    assert canonical.stage == "structure"
    assert canonical.execution_status == "paused"
    assert canonical.requirements[0].requirement_id == "req-auth"
    assert canonical.modules[0].module_id == "cmp-auth"
    assert canonical.modules[0].tasks[0].task_id == "task:cmp-auth"
