from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from uuid import UUID

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.generation.graph.build import build_estimation_graph
from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.ports import GraphNodeDependencies
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


@dataclass(frozen=True)
class Snapshot:
    values: dict[str, object]
    next: tuple[str, ...]


class RecordingGraph:
    def __init__(
        self,
        result: object,
        *,
        snapshot: Snapshot | None = None,
    ) -> None:
        self.result = result
        self.snapshot = snapshot or Snapshot(
            values={},
            next=(),
        )
        self.calls: list[dict[str, object]] = []
        self.state_calls: list[dict[str, object]] = []

    async def aget_state(
        self,
        config: dict[str, object],
    ) -> Snapshot:
        self.state_calls.append(deepcopy(config))
        return deepcopy(self.snapshot)

    async def ainvoke(
        self,
        input: dict[str, object] | None,
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



@pytest.mark.asyncio
async def test_completed_thread_returns_stored_state_without_reinvocation() -> None:
    estimation_id = UUID(
        "f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    stored_state = _terminal_state(str(estimation_id))
    graph = RecordingGraph(
        result=None,
        snapshot=Snapshot(
            values=stored_state,
            next=(),
        ),
    )
    service = GraphEstimationService(graph=graph)

    run = await service.estimate(
        transcript=TRANSCRIPT,
        estimation_id=estimation_id,
    )

    assert run.state == stored_state
    assert graph.calls == []
    assert graph.state_calls == [
        {
            "configurable": {
                "thread_id": run.thread_id,
            }
        }
    ]


@pytest.mark.asyncio
async def test_incomplete_thread_resumes_without_fresh_input() -> None:
    estimation_id = UUID(
        "f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    incomplete_state = new_estimation_graph_state(
        transcript=TRANSCRIPT,
        estimation_id=str(estimation_id),
    )
    incomplete_state["requirements"] = [
        {
            "requirement_id": "REQ-001",
            "text": "Users authenticate with JWT.",
        }
    ]

    graph = RecordingGraph(
        result=_terminal_state(str(estimation_id)),
        snapshot=Snapshot(
            values=incomplete_state,
            next=("classify_components",),
        ),
    )
    service = GraphEstimationService(graph=graph)

    run = await service.estimate(
        transcript=TRANSCRIPT,
        estimation_id=estimation_id,
    )

    assert run.state["status"] == "validated"
    assert graph.calls == [
        {
            "input": None,
            "config": {
                "configurable": {
                    "thread_id": run.thread_id,
                }
            },
        }
    ]


@pytest.mark.asyncio
async def test_existing_thread_rejects_different_transcript() -> None:
    estimation_id = UUID(
        "f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )
    stored_state = _terminal_state(str(estimation_id))
    stored_state["transcript"] = (
        "A completely different estimation transcript."
    )

    graph = RecordingGraph(
        result=None,
        snapshot=Snapshot(
            values=stored_state,
            next=(),
        ),
    )
    service = GraphEstimationService(graph=graph)

    with pytest.raises(
        GraphResultContractError,
        match="transcript",
    ):
        await service.estimate(
            transcript=TRANSCRIPT,
            estimation_id=estimation_id,
        )

    assert graph.calls == []


@pytest.mark.asyncio
async def test_completed_real_graph_is_idempotent_with_reducers() -> None:
    requirement = {
        "requirement_id": "REQ-001",
        "text": "Users authenticate with JWT.",
    }
    component = {
        "component_id": "CMP-001",
        "name": "JWT authentication",
        "category": "backend",
        "requirement_ids": ["REQ-001"],
    }
    matches = [
        {
            "component_id": "CMP-001",
            "budget_id": "BUD-101",
            "reference_component_id": "AUTH-01",
            "source_document_id": "DOC-10",
            "source_chunk_id": "CH-101",
            "recorded_hours": 32.0,
            "distance": 0.1,
            "score": 0.9,
            "retrieval_method": "hybrid",
        },
        {
            "component_id": "CMP-001",
            "budget_id": "BUD-102",
            "reference_component_id": "AUTH-02",
            "source_document_id": "DOC-11",
            "source_chunk_id": "CH-102",
            "recorded_hours": 40.0,
            "distance": 0.1,
            "score": 0.9,
            "retrieval_method": "hybrid",
        },
        {
            "component_id": "CMP-001",
            "budget_id": "BUD-103",
            "reference_component_id": "AUTH-03",
            "source_document_id": "DOC-12",
            "source_chunk_id": "CH-103",
            "recorded_hours": 48.0,
            "distance": 0.1,
            "score": 0.9,
            "retrieval_method": "hybrid",
        },
    ]

    extractor = FakeRequirementExtractor([requirement])
    classifier = FakeComponentClassifier([component])
    searcher = FakeBudgetSearcher(
        {"CMP-001": matches}
    )

    graph = build_estimation_graph(
        GraphNodeDependencies(
            requirement_extractor=extractor,
            component_classifier=classifier,
            budget_searcher=searcher,
        ),
        checkpointer=InMemorySaver(),
    )
    service = GraphEstimationService(graph=graph)

    estimation_id = UUID(
        "f5317c82-05ad-4df5-bf43-f9b286f70e82"
    )

    first = await service.estimate(
        transcript=TRANSCRIPT,
        estimation_id=estimation_id,
    )
    second = await service.estimate(
        transcript=TRANSCRIPT,
        estimation_id=estimation_id,
    )

    assert second.state == first.state
    assert len(second.state["budget_matches"]) == 3
    assert len(second.state["trace_events"]) == 5

    assert extractor.calls == [TRANSCRIPT]
    assert classifier.calls == [[requirement]]
    assert searcher.calls == [
        {
            "component_id": "CMP-001",
            "k": 5,
        }
    ]
