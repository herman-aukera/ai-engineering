from __future__ import annotations

import pytest

from app.generation.graph.state import (
    BudgetMatch,
    DomainTraceEvent,
    GraphIssue,
    merge_budget_matches,
    merge_graph_issues,
    merge_trace_events,
)


def _budget_match(*, component_id: str = "component-a") -> BudgetMatch:
    return BudgetMatch(
        component_id=component_id,
        budget_id="budget-1",
        reference_component_id="reference-1",
        source_document_id="document-1",
        source_chunk_id="chunk-1",
        recorded_hours=8.0,
        distance=0.1,
        score=0.9,
        retrieval_method="hybrid",
    )


def test_budget_match_reducer_is_replay_safe_and_deterministic() -> None:
    first = _budget_match(component_id="component-b")
    second = _budget_match(component_id="component-a")

    left = merge_budget_matches([first], [second, first])
    right = merge_budget_matches([second], [first, second])

    assert len(left) == 2
    assert left == right


def test_budget_match_reducer_rejects_conflicting_identity_reuse() -> None:
    match = BudgetMatch(**{**_budget_match(), "match_id": "match-1"})
    conflict = BudgetMatch(**{**match, "score": 0.4})

    with pytest.raises(ValueError, match="conflicting budget match identity"):
        merge_budget_matches([match], [conflict])


def test_graph_issue_reducer_is_idempotent_and_fails_closed() -> None:
    issue = GraphIssue(
        issue_id="issue-1",
        code="missing_hours",
        message="Hours are missing.",
        node="validate_estimate",
        severity="error",
    )

    assert merge_graph_issues([issue], [issue]) == [issue]

    conflict = GraphIssue(**{**issue, "message": "Different meaning."})
    with pytest.raises(ValueError, match="conflicting graph issue identity"):
        merge_graph_issues([issue], [conflict])


def test_trace_event_reducer_is_idempotent_and_fails_closed() -> None:
    event = DomainTraceEvent(
        event_id="event-1",
        event_type="estimate_validated",
        node="validate_estimate",
        summary="Validated deterministic estimate.",
        evidence_refs=["estimate:1"],
        state_delta_keys=["status", "trace_events"],
    )

    assert merge_trace_events([event], [event]) == [event]

    conflict = DomainTraceEvent(**{**event, "summary": "Different meaning."})
    with pytest.raises(ValueError, match="conflicting trace event identity"):
        merge_trace_events([event], [conflict])
