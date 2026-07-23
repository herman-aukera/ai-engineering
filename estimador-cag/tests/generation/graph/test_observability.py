from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

import app.generation.graph.observability as observability_module
from app.generation.graph.build import (
    GRAPH_NAME,
    REQUIRED_NODE_NAMES,
    build_estimation_graph,
)
from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.observability import (
    NODE_SPAN_NAME,
    ROOT_SPAN_NAME,
    LogfireGraphTracer,
    get_logfire_graph_tracer,
    instrument_graph_node,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.services.graph_estimation import GraphEstimationService

PRIVATE_TRANSCRIPT = (
    "PRIVATE TRANSCRIPT: implement JWT authentication "
    "with auditable administrative operations."
)

REQUIREMENTS = [
    {
        "requirement_id": "REQ-001",
        "text": "Users authenticate with JWT.",
    }
]

COMPONENTS = [
    {
        "component_id": "CMP-001",
        "name": "JWT authentication",
        "category": "backend",
        "requirement_ids": ["REQ-001"],
    }
]

MATCHES = [
    {
        "component_id": "CMP-001",
        "budget_id": "BUD-101",
        "reference_component_id": "AUTH-01",
        "source_document_id": "DOC-101",
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
        "source_document_id": "DOC-102",
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
        "source_document_id": "DOC-103",
        "source_chunk_id": "CH-103",
        "recorded_hours": 48.0,
        "distance": 0.1,
        "score": 0.9,
        "retrieval_method": "hybrid",
    },
]


@dataclass
class SpanRecord:
    record_id: int
    name: str
    attributes: dict[str, object]
    parent_id: int | None
    exited: bool = False
    exception_type: str | None = None


class RecordingSpan:
    def __init__(
        self,
        tracer: RecordingTracer,
        record: SpanRecord,
    ) -> None:
        self._tracer = tracer
        self._record = record

    def __enter__(self) -> RecordingSpan:
        self._tracer.stack.append(self._record.record_id)
        return self

    def __exit__(
        self,
        exception_type,
        exception,
        traceback,
    ) -> bool:
        active_record_id = self._tracer.stack.pop()
        assert active_record_id == self._record.record_id

        self._record.exited = True

        if exception_type is not None:
            self._record.exception_type = (
                exception_type.__name__
            )

        return False

    def set_attribute(
        self,
        name: str,
        value: object,
    ) -> None:
        self._record.attributes[name] = value


@dataclass
class RecordingTracer:
    records: list[SpanRecord] = field(default_factory=list)
    stack: list[int] = field(default_factory=list)
    next_record_id: int = 1

    def span(
        self,
        name: str,
        **attributes: object,
    ) -> RecordingSpan:
        parent_id = (
            self.stack[-1]
            if self.stack
            else None
        )
        record = SpanRecord(
            record_id=self.next_record_id,
            name=name,
            attributes=dict(attributes),
            parent_id=parent_id,
        )
        self.next_record_id += 1
        self.records.append(record)
        return RecordingSpan(self, record)

    def clear(self) -> None:
        assert self.stack == []
        self.records.clear()
        self.next_record_id = 1


def _service(
    tracer: RecordingTracer,
) -> tuple[
    GraphEstimationService,
    FakeRequirementExtractor,
    FakeComponentClassifier,
    FakeBudgetSearcher,
]:
    extractor = FakeRequirementExtractor(REQUIREMENTS)
    classifier = FakeComponentClassifier(COMPONENTS)
    searcher = FakeBudgetSearcher(
        {"CMP-001": MATCHES}
    )
    dependencies = GraphNodeDependencies(
        requirement_extractor=extractor,
        component_classifier=classifier,
        budget_searcher=searcher,
        search_k=5,
    )
    graph = build_estimation_graph(
        dependencies,
        checkpointer=InMemorySaver(),
        tracer=tracer,
    )

    return (
        GraphEstimationService(
            graph=graph,
            tracer=tracer,
        ),
        extractor,
        classifier,
        searcher,
    )


def _serialized_attributes(
    tracer: RecordingTracer,
) -> str:
    return repr(
        [
            record.attributes
            for record in tracer.records
        ]
    )


def test_logfire_configuration_is_private_and_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_configure(**kwargs: object) -> None:
        calls.append(dict(kwargs))

    monkeypatch.setattr(
        observability_module.logfire,
        "configure",
        fake_configure,
    )

    get_logfire_graph_tracer.cache_clear()

    try:
        first = get_logfire_graph_tracer()
        second = get_logfire_graph_tracer()
    finally:
        get_logfire_graph_tracer.cache_clear()

    assert isinstance(first, LogfireGraphTracer)
    assert first is second
    assert calls == [
        {
            "send_to_logfire": "if-token-present",
            "service_name": "estimador-cag",
            "console": False,
            "inspect_arguments": False,
        }
    ]


@pytest.mark.asyncio
async def test_node_span_records_only_sanitized_metadata() -> None:
    tracer = RecordingTracer()

    async def node(state):
        assert state["transcript"] == PRIVATE_TRANSCRIPT
        return {
            "status": "pending",
            "errors": [],
            "trace_events": [],
        }

    instrumented = instrument_graph_node(
        graph_name=GRAPH_NAME,
        node_name="test_node",
        node=node,
        tracer=tracer,
    )

    result = await instrumented(
        {
            "transcript": PRIVATE_TRANSCRIPT,
            "estimation_id": "estimate-001",
            "graph_version": "session13.v1",
        }
    )

    assert result["status"] == "pending"
    assert len(tracer.records) == 1

    record = tracer.records[0]

    assert record.name == NODE_SPAN_NAME
    assert record.parent_id is None
    assert record.exited is True
    assert record.exception_type is None
    assert record.attributes["graph_name"] == GRAPH_NAME
    assert record.attributes["node_name"] == "test_node"
    assert record.attributes["estimation_id"] == (
        "estimate-001"
    )
    assert record.attributes["graph_version"] == (
        "session13.v1"
    )
    assert record.attributes["state_delta_keys"] == [
        "errors",
        "status",
        "trace_events",
    ]
    assert PRIVATE_TRANSCRIPT not in _serialized_attributes(
        tracer
    )


@pytest.mark.asyncio
async def test_new_run_emits_root_and_five_child_spans() -> None:
    tracer = RecordingTracer()
    service, extractor, classifier, searcher = _service(
        tracer
    )
    estimation_id = uuid4()

    result = await service.estimate(
        transcript=PRIVATE_TRANSCRIPT,
        estimation_id=estimation_id,
    )

    assert result.state["status"] == "validated"
    assert result.state["estimate"]["total_hours"] == 40.0

    root_records = [
        record
        for record in tracer.records
        if record.name == ROOT_SPAN_NAME
    ]
    node_records = [
        record
        for record in tracer.records
        if record.name == NODE_SPAN_NAME
    ]

    assert len(root_records) == 1
    assert len(node_records) == 5

    root = root_records[0]

    assert root.parent_id is None
    assert root.exited is True
    assert root.attributes["graph_name"] == GRAPH_NAME
    assert root.attributes["execution_mode"] == "new"
    assert root.attributes["terminal_status"] == "validated"
    assert root.attributes["review_required"] is False
    assert root.attributes["requirement_count"] == 1
    assert root.attributes["component_count"] == 1
    assert root.attributes["budget_match_count"] == 3
    assert root.attributes["error_count"] == 0
    assert root.attributes["trace_event_count"] == 5
    assert root.attributes["total_hours"] == 40.0

    assert [
        record.attributes["node_name"]
        for record in node_records
    ] == list(REQUIRED_NODE_NAMES)

    assert all(
        record.parent_id == root.record_id
        for record in node_records
    )
    assert all(
        record.exited
        for record in node_records
    )

    assert len(extractor.calls) == 1
    assert len(classifier.calls) == 1
    assert len(searcher.calls) == 1

    assert PRIVATE_TRANSCRIPT not in _serialized_attributes(
        tracer
    )


@pytest.mark.asyncio
async def test_completed_duplicate_emits_root_only() -> None:
    tracer = RecordingTracer()
    service, extractor, classifier, searcher = _service(
        tracer
    )
    estimation_id: UUID = uuid4()

    first = await service.estimate(
        transcript=PRIVATE_TRANSCRIPT,
        estimation_id=estimation_id,
    )

    tracer.clear()

    second = await service.estimate(
        transcript=PRIVATE_TRANSCRIPT,
        estimation_id=estimation_id,
    )

    assert second.state == first.state
    assert len(tracer.records) == 1

    root = tracer.records[0]

    assert root.name == ROOT_SPAN_NAME
    assert root.parent_id is None
    assert root.attributes["execution_mode"] == "completed"
    assert root.attributes["terminal_status"] == "validated"

    assert len(extractor.calls) == 1
    assert len(classifier.calls) == 1
    assert len(searcher.calls) == 1

    assert PRIVATE_TRANSCRIPT not in _serialized_attributes(
        tracer
    )
