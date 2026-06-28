import pytest
from pydantic import ValidationError

from app.schemas.estimation import EstimateLineItem, SourceReference


def test_source_reference_requires_chunk_document_and_evidence():
    source = SourceReference(
        chunk_id="chunk-001",
        document_id="BUDGET-2024-0001",
        evidence="Payments module: 24 hours",
    )

    assert source.chunk_id == "chunk-001"
    assert source.document_id == "BUDGET-2024-0001"
    assert source.evidence == "Payments module: 24 hours"


def test_grounded_line_requires_at_least_one_source():
    with pytest.raises(ValidationError, match="grounded lines must include at least one source"):
        EstimateLineItem(
            component="Payments module",
            hours=24.0,
            rationale="Similar historical payment module implementation.",
            grounded=True,
            sources=[],
        )


def test_ungrounded_line_cannot_carry_sources():
    with pytest.raises(ValidationError, match="ungrounded lines must not include sources"):
        EstimateLineItem(
            component="Unknown AI module",
            hours=None,
            rationale="No matching historical source was retrieved.",
            grounded=False,
            sources=[
                SourceReference(
                    chunk_id="chunk-001",
                    document_id="BUDGET-2024-0001",
                    evidence="Payments module: 24 hours",
                )
            ],
        )


def test_ungrounded_line_cannot_invent_hours():
    with pytest.raises(ValidationError, match="ungrounded lines must not include hours"):
        EstimateLineItem(
            component="Unknown AI module",
            hours=16.0,
            rationale="No matching historical source was retrieved.",
            grounded=False,
            sources=[],
        )


def test_ungrounded_line_can_mark_insufficient_data_without_hours_or_sources():
    line = EstimateLineItem(
        component="Unknown AI module",
        hours=None,
        rationale="No matching historical source was retrieved.",
        grounded=False,
        sources=[],
    )

    assert line.grounded is False
    assert line.hours is None
    assert line.sources == []


def test_grounded_line_with_source_and_hours_is_valid():
    line = EstimateLineItem(
        component="Payments module",
        hours=24.0,
        rationale="Grounded in a retrieved historical payment module estimate.",
        grounded=True,
        sources=[
            SourceReference(
                chunk_id="chunk-001",
                document_id="BUDGET-2024-0001",
                evidence="Payments module: 24 hours",
            )
        ],
    )

    assert line.grounded is True
    assert line.hours == 24.0
    assert line.sources[0].chunk_id == "chunk-001"
