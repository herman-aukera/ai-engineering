from __future__ import annotations

from copy import deepcopy
from uuid import UUID

import pytest

from app.generation.graph.state import new_estimation_graph_state
from app.services.graph_estimation import (
    GraphEstimationService,
    GraphResultContractError,
    thread_id_from_estimation_id,
)

TRANSCRIPT = (
    "The client needs JWT authentication and auditable "
    "logging for sensitive operations."
)


def _terminal_state(
    estimation_id: str,
) -> dict[str, object]:
    state = new_estimation_graph_state(
        transcript=TRANSCRIPT,
        estimation_id=estimation_id,
    )
    state.update(
        {
            "status": "validated",
            "review_required": False,
            "estimate": {
                "components": [],
                "subtotal_hours": 64.0,
                "contingency_hours": 0.0,
                "total_hours": 64.0,
                "total_cost_eur": None,
                "currency": "EUR",
            },
        }
    )
    return state


class RecordingGraph:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def ainvoke(
        self,
        input: dict[str, object],
        config: dict[str, object] | None = None,
    ) -> object:
        self.calls.append(
            {
                "input": deepcopy(input),
                "config": deepcopy(config),
            }
        )
        return deepcopy(self.result)


def test_thread_id_is_stable_and_bounded() -> None:
    estimation_id = "f5317c82-05ad-4df5-bf43-f9b286f70e82"

    first = thread_id_from_estimation_id(estimation_id)
    second = thread_id_from_estimation_id(estimation_id)

    assert first == second
    assert first == (
        "estimate:f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    assert len(first) <= 128


@pytest.mark.asyncio
async def test_service_generates_uuid_and_invokes_graph_with_thread() -> None:
    graph = RecordingGraph(result=None)
    service = GraphEstimationService(graph=graph)

    async def invoke_with_generated_result(
        input: dict[str, object],
        config: dict[str, object] | None = None,
    ) -> object:
        graph.calls.append(
            {
                "input": deepcopy(input),
                "config": deepcopy(config),
            }
        )
        return _terminal_state(str(input["estimation_id"]))

    graph.ainvoke = invoke_with_generated_result

    run = await service.estimate(transcript=TRANSCRIPT)

    UUID(run.estimation_id)

    assert run.thread_id == thread_id_from_estimation_id(
        run.estimation_id
    )
    assert run.state["status"] == "validated"

    assert graph.calls == [
        {
            "input": {
                "transcript": TRANSCRIPT,
                "estimation_id": run.estimation_id,
                "graph_version": "session13.v1",
                "requirements": [],
                "components": [],
                "budget_matches": [],
                "component_estimates": [],
                "status": "pending",
                "review_required": False,
                "errors": [],
                "trace_events": [],
                "provider_metadata": {},
                "execution_metadata": {},
            },
            "config": {
                "configurable": {
                    "thread_id": run.thread_id,
                }
            },
        }
    ]


@pytest.mark.asyncio
async def test_service_reuses_explicit_estimation_identifier() -> None:
    estimation_id = UUID(
        "f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    graph = RecordingGraph(
        _terminal_state(str(estimation_id))
    )
    service = GraphEstimationService(graph=graph)

    run = await service.estimate(
        transcript=TRANSCRIPT,
        estimation_id=estimation_id,
    )

    assert run.estimation_id == str(estimation_id)
    assert run.thread_id == (
        "estimate:f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    assert graph.calls[0]["config"] == {
        "configurable": {
            "thread_id": run.thread_id,
        }
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_result",
    [
        None,
        {
            **_terminal_state(
                "f5317c82-05ad-4df5-bf43-f9b286f70e82"
            ),
            "status": "pending",
        },
    ],
)
async def test_service_rejects_invalid_terminal_result(
    invalid_result: object,
) -> None:
    estimation_id = UUID(
        "f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    service = GraphEstimationService(
        graph=RecordingGraph(invalid_result)
    )

    with pytest.raises(GraphResultContractError):
        await service.estimate(
            transcript=TRANSCRIPT,
            estimation_id=estimation_id,
        )


@pytest.mark.asyncio
async def test_service_rejects_mismatched_estimation_id() -> None:
    requested_id = UUID(
        "f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    graph = RecordingGraph(
        _terminal_state(
            "04592acd-3d60-4e18-bb63-8d7ab80961d4"
        )
    )
    service = GraphEstimationService(graph=graph)

    with pytest.raises(
        GraphResultContractError,
        match="estimation_id",
    ):
        await service.estimate(
            transcript=TRANSCRIPT,
            estimation_id=requested_id,
        )
