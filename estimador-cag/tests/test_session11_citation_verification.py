from app.schemas.estimation import EstimateLineItem, SourceReference
from app.services.citation_verification import verify_citations


def _grounded_line(component: str, chunk_id: str) -> EstimateLineItem:
    return EstimateLineItem(
        component=component,
        hours=24.0,
        rationale="Grounded in retrieved historical evidence.",
        grounded=True,
        sources=[
            SourceReference(
                chunk_id=chunk_id,
                document_id="BUDGET-2024-0001",
                evidence="Payments module: 24 hours",
            )
        ],
    )


def _insufficient_line(component: str) -> EstimateLineItem:
    return EstimateLineItem(
        component=component,
        hours=None,
        rationale="No matching historical source was retrieved.",
        grounded=False,
        sources=[],
    )


def test_verify_citations_accepts_all_retrieved_sources():
    lines = [
        _grounded_line("Payments module", "chunk-001"),
        _grounded_line("Authentication", "chunk-002"),
    ]

    report = verify_citations(lines, retrieved_chunk_ids={"chunk-001", "chunk-002"})

    assert report.total_lines == 2
    assert report.grounded_lines == 2
    assert report.dangling_lines == 0
    assert report.insufficient_lines == 0
    assert report.verified_citations == 2
    assert report.dangling_citations == []
    assert report.has_dangling is False
    assert [line.status for line in report.lines] == ["grounded", "grounded"]


def test_verify_citations_flags_dangling_line_citation():
    lines = [
        _grounded_line("Payments module", "chunk-001"),
        _grounded_line("Invented module", "chunk-999"),
    ]

    report = verify_citations(lines, retrieved_chunk_ids={"chunk-001"})

    assert report.total_lines == 2
    assert report.grounded_lines == 1
    assert report.dangling_lines == 1
    assert report.insufficient_lines == 0
    assert report.verified_citations == 1
    assert report.dangling_citations == ["chunk-999"]
    assert report.has_dangling is True

    dangling_line = report.lines[1]
    assert dangling_line.component == "Invented module"
    assert dangling_line.status == "dangling"
    assert dangling_line.cited_chunk_ids == ["chunk-999"]
    assert dangling_line.dangling_chunk_ids == ["chunk-999"]


def test_verify_citations_classifies_ungrounded_lines_as_insufficient():
    lines = [
        _grounded_line("Payments module", "chunk-001"),
        _insufficient_line("Unknown AI workflow"),
    ]

    report = verify_citations(lines, retrieved_chunk_ids={"chunk-001"})

    assert report.total_lines == 2
    assert report.grounded_lines == 1
    assert report.dangling_lines == 0
    assert report.insufficient_lines == 1
    assert report.verified_citations == 1
    assert report.has_dangling is False

    insufficient_line = report.lines[1]
    assert insufficient_line.component == "Unknown AI workflow"
    assert insufficient_line.status == "insufficient"
    assert insufficient_line.cited_chunk_ids == []
    assert insufficient_line.dangling_chunk_ids == []


def test_verify_citations_treats_empty_retrieved_set_as_dangling_for_grounded_lines():
    lines = [_grounded_line("Payments module", "chunk-001")]

    report = verify_citations(lines, retrieved_chunk_ids=set())

    assert report.total_lines == 1
    assert report.grounded_lines == 0
    assert report.dangling_lines == 1
    assert report.insufficient_lines == 0
    assert report.verified_citations == 0
    assert report.dangling_citations == ["chunk-001"]
    assert report.has_dangling is True


def test_verify_citations_deduplicates_dangling_citations_deterministically():
    lines = [
        _grounded_line("Payments module", "chunk-999"),
        _grounded_line("Authentication", "chunk-999"),
    ]

    report = verify_citations(lines, retrieved_chunk_ids={"chunk-001"})

    assert report.dangling_lines == 2
    assert report.dangling_citations == ["chunk-999"]
