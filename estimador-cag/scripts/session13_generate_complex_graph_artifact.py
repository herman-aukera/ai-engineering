"""Generate deterministic Session 13 complex-graph evidence."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self
from uuid import UUID

from langgraph.checkpoint.memory import InMemorySaver

from app.generation.graph.build import (
    REQUIRED_NODE_NAMES,
    build_estimation_graph,
)
from app.generation.graph.fakes import (
    FakeBudgetSearcher,
    FakeComponentClassifier,
    FakeRequirementExtractor,
)
from app.generation.graph.ports import GraphNodeDependencies
from app.generation.graph.state import (
    BudgetMatch,
    ComponentItem,
    RequirementItem,
)
from app.services.graph_estimation import GraphEstimationService

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    PROJECT_ROOT
    / "evals"
    / "session12_agentic"
    / "sample_transcript_complex.txt"
)

DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "artifacts"
    / "session13"
    / "complex_graph_execution_deterministic.json"
)

ESTIMATION_ID = UUID(
    "00000000-0000-4000-8000-000000000013"
)

REQUIREMENTS: list[RequirementItem] = [
    {
        "requirement_id": "REQ-001",
        "text": (
            "Provide JWT authentication with role-based "
            "access for administrators and analysts."
        ),
    },
    {
        "requirement_id": "REQ-002",
        "text": (
            "Record auditable logs for sensitive actions "
            "and data exports."
        ),
    },
    {
        "requirement_id": "REQ-003",
        "text": (
            "Provide an administrative dashboard for "
            "uploaded records and failed validations."
        ),
    },
    {
        "requirement_id": "REQ-004",
        "text": (
            "Import monthly reconciliation files in CSV "
            "format."
        ),
    },
    {
        "requirement_id": "REQ-005",
        "text": (
            "Provide basic deployment documentation and "
            "handoff notes."
        ),
    },
]

COMPONENTS: list[ComponentItem] = [
    {
        "component_id": "CMP-001",
        "name": "JWT authentication and RBAC",
        "category": "backend",
        "requirement_ids": ["REQ-001"],
    },
    {
        "component_id": "CMP-002",
        "name": "Audit logging",
        "category": "backend",
        "requirement_ids": ["REQ-002"],
    },
    {
        "component_id": "CMP-003",
        "name": "Administrative dashboard",
        "category": "frontend",
        "requirement_ids": ["REQ-003"],
    },
    {
        "component_id": "CMP-004",
        "name": "CSV reconciliation import",
        "category": "data",
        "requirement_ids": ["REQ-004"],
    },
    {
        "component_id": "CMP-005",
        "name": "Deployment documentation and handoff",
        "category": "delivery",
        "requirement_ids": ["REQ-005"],
    },
]

HOURS_BY_COMPONENT = {
    "CMP-001": (36.0, 40.0, 44.0),
    "CMP-002": (20.0, 24.0, 28.0),
    "CMP-003": (48.0, 56.0, 64.0),
    "CMP-004": (28.0, 32.0, 36.0),
    "CMP-005": (14.0, 16.0, 18.0),
}


@dataclass
class SpanRecord:
    record_id: int
    name: str
    attributes: dict[str, object]
    parent_id: int | None
    exited: bool = False
    exception_type: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "name": self.name,
            "attributes": dict(self.attributes),
            "parent_id": self.parent_id,
            "exited": self.exited,
            "exception_type": self.exception_type,
        }


class RecordingSpan:
    def __init__(
        self,
        tracer: RecordingTracer,
        record: SpanRecord,
    ) -> None:
        self._tracer = tracer
        self._record = record

    def __enter__(self) -> Self:
        self._tracer.stack.append(
            self._record.record_id
        )
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> bool:
        active_record_id = self._tracer.stack.pop()

        if active_record_id != self._record.record_id:
            raise RuntimeError(
                "telemetry span stack is inconsistent"
            )

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
    records: list[SpanRecord] = field(
        default_factory=list
    )
    stack: list[int] = field(default_factory=list)
    next_record_id: int = 1

    def span(
        self,
        name: str,
        **attributes: object,
    ) -> AbstractContextManager[RecordingSpan]:
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


def _matches_by_component(
) -> dict[str, list[BudgetMatch]]:
    matches_by_component: dict[
        str,
        list[BudgetMatch],
    ] = {}

    for component_id, source_hours in (
        HOURS_BY_COMPONENT.items()
    ):
        matches: list[BudgetMatch] = []

        for index, recorded_hours in enumerate(
            source_hours,
            start=1,
        ):
            distance = round(0.05 * index, 2)

            matches.append(
                {
                    "component_id": component_id,
                    "budget_id": (
                        f"BUD-{component_id}-{index:02d}"
                    ),
                    "reference_component_id": (
                        f"REF-{component_id}-{index:02d}"
                    ),
                    "source_document_id": (
                        f"DOC-{component_id}-{index:02d}"
                    ),
                    "source_chunk_id": (
                        f"CHK-{component_id}-{index:02d}"
                    ),
                    "recorded_hours": recorded_hours,
                    "distance": distance,
                    "score": round(
                        1.0 / (1.0 + distance),
                        6,
                    ),
                    "retrieval_method": (
                        "deterministic_fixture"
                    ),
                }
            )

        matches_by_component[component_id] = matches

    return matches_by_component


def _sha256(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


async def build_complex_graph_artifact(
    *,
    source_path: Path = SOURCE_PATH,
) -> dict[str, object]:
    transcript = source_path.read_text(
        encoding="utf-8"
    )

    extractor = FakeRequirementExtractor(REQUIREMENTS)
    classifier = FakeComponentClassifier(COMPONENTS)
    searcher = FakeBudgetSearcher(
        _matches_by_component()
    )
    tracer = RecordingTracer()

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
    service = GraphEstimationService(
        graph=graph,
        tracer=tracer,
    )

    run = await service.estimate(
        transcript=transcript,
        estimation_id=ESTIMATION_ID,
    )
    state = run.state

    telemetry_records = [
        record.as_dict()
        for record in tracer.records
    ]

    node_span_records = [
        record
        for record in telemetry_records
        if record["name"] == "session13.graph.node"
    ]

    artifact: dict[str, object] = {
        "schema_version": (
            "session13.complex_graph_evidence.v1"
        ),
        "scenario_id": "sample_transcript_complex",
        "source": {
            "path": str(
                source_path.relative_to(PROJECT_ROOT)
            ),
            "sha256": _sha256(transcript),
            "character_count": len(transcript),
        },
        "execution": {
            "provider_backend": "deterministic_fakes",
            "persistence_backend": "in_memory",
            "telemetry_backend": "recording_tracer",
            "telemetry_exported": False,
            "uses_live_provider": False,
            "uses_live_postgres": False,
            "uses_remote_logfire": False,
        },
        "result": {
            "estimation_id": run.estimation_id,
            "thread_id": run.thread_id,
            "status": state["status"],
            "review_required": state[
                "review_required"
            ],
            "requirements": state["requirements"],
            "components": state["components"],
            "budget_matches": state[
                "budget_matches"
            ],
            "component_estimates": state[
                "component_estimates"
            ],
            "estimate": state["estimate"],
            "errors": state["errors"],
            "execution_metadata": state[
                "execution_metadata"
            ],
            "trace_events": state["trace_events"],
        },
        "execution_evidence": {
            "extractor_call_count": len(
                extractor.calls
            ),
            "classifier_call_count": len(
                classifier.calls
            ),
            "search_call_count": len(
                searcher.calls
            ),
            "searched_component_ids": [
                call["component_id"]
                for call in searcher.calls
            ],
            "domain_node_order": [
                event["node"]
                for event in state["trace_events"]
            ],
            "telemetry_node_order": [
                record["attributes"]["node_name"]
                for record in node_span_records
            ],
            "root_span_count": sum(
                record["name"]
                == "session13.graph.run"
                for record in telemetry_records
            ),
            "node_span_count": len(
                node_span_records
            ),
        },
        "telemetry_trace": telemetry_records,
    }

    validate_complex_graph_artifact(artifact)
    return artifact


def validate_complex_graph_artifact(
    artifact: dict[str, object],
) -> None:
    if artifact.get("schema_version") != (
        "session13.complex_graph_evidence.v1"
    ):
        raise ValueError(
            "complex graph artifact schema is invalid"
        )

    execution = artifact.get("execution")
    result = artifact.get("result")
    evidence = artifact.get("execution_evidence")
    telemetry = artifact.get("telemetry_trace")

    if not isinstance(execution, dict):
        raise ValueError("execution evidence is missing")
    if not isinstance(result, dict):
        raise ValueError("graph result is missing")
    if not isinstance(evidence, dict):
        raise ValueError(
            "execution call evidence is missing"
        )
    if not isinstance(telemetry, list):
        raise ValueError("telemetry trace is missing")

    if execution.get("persistence_backend") != (
        "in_memory"
    ):
        raise ValueError(
            "deterministic artifact must use memory persistence"
        )
    if execution.get("telemetry_exported") is not False:
        raise ValueError(
            "deterministic artifact must not claim export"
        )
    if execution.get("uses_live_postgres") is not False:
        raise ValueError(
            "deterministic artifact must not claim PostgreSQL"
        )
    if execution.get("uses_remote_logfire") is not False:
        raise ValueError(
            "deterministic artifact must not claim remote Logfire"
        )

    if result.get("status") != "validated":
        raise ValueError(
            "complex graph run must be validated"
        )
    if result.get("review_required") is not False:
        raise ValueError(
            "complex graph run unexpectedly requires review"
        )
    if result.get("errors") != []:
        raise ValueError(
            "complex graph run contains errors"
        )

    estimate = result.get("estimate")

    if not isinstance(estimate, dict):
        raise ValueError("estimate is missing")
    if estimate.get("total_hours") != 168.0:
        raise ValueError(
            "complex graph total is unexpected"
        )

    expected_lengths = {
        "requirements": 5,
        "components": 5,
        "budget_matches": 15,
        "component_estimates": 5,
        "trace_events": 5,
    }

    for field_name, expected_length in (
        expected_lengths.items()
    ):
        value = result.get(field_name)

        if (
            not isinstance(value, list)
            or len(value) != expected_length
        ):
            raise ValueError(
                f"{field_name} count is unexpected"
            )

    expected_order = list(REQUIRED_NODE_NAMES)

    if evidence.get("domain_node_order") != (
        expected_order
    ):
        raise ValueError(
            "domain trace node order is invalid"
        )
    if evidence.get("telemetry_node_order") != (
        expected_order
    ):
        raise ValueError(
            "telemetry trace node order is invalid"
        )
    if evidence.get("root_span_count") != 1:
        raise ValueError(
            "exactly one root span is required"
        )
    if evidence.get("node_span_count") != 5:
        raise ValueError(
            "exactly five node spans are required"
        )

    root_records = [
        record
        for record in telemetry
        if (
            isinstance(record, dict)
            and record.get("name")
            == "session13.graph.run"
        )
    ]
    node_records = [
        record
        for record in telemetry
        if (
            isinstance(record, dict)
            and record.get("name")
            == "session13.graph.node"
        )
    ]

    root_record_id = root_records[0].get(
        "record_id"
    )

    if any(
        record.get("parent_id") != root_record_id
        for record in node_records
    ):
        raise ValueError(
            "node spans are not children of the root span"
        )

    serialized = json.dumps(
        artifact,
        sort_keys=True,
    )

    transcript = SOURCE_PATH.read_text(
        encoding="utf-8"
    )

    if transcript in serialized:
        raise ValueError(
            "raw transcript leaked into artifact telemetry"
        )

    forbidden_fragments = (
        "postgresql" + "://",
        "Bearer" + " ",
        "BEGIN " + "PRIVATE KEY",
    )

    if any(
        fragment in serialized
        for fragment in forbidden_fragments
    ):
        raise ValueError(
            "artifact contains credential-shaped data"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic Session 13 "
            "complex graph evidence."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    artifact = asyncio.run(
        build_complex_graph_artifact()
    )

    output_path: Path = args.output
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    result = artifact["result"]
    evidence = artifact["execution_evidence"]

    print(
        json.dumps(
            {
                "artifact_path": str(output_path),
                "status": result["status"],
                "total_hours": result[
                    "estimate"
                ]["total_hours"],
                "component_count": len(
                    result["components"]
                ),
                "root_span_count": evidence[
                    "root_span_count"
                ],
                "node_span_count": evidence[
                    "node_span_count"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
