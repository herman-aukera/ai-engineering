"""
Citation verification for Session 11 line-level grounded estimates.

This module is deterministic: it does not ask the model whether citations are
valid. It compares cited chunk ids against the exact retrieved chunk ids that
were passed to generation.
"""

from collections.abc import Iterable

from app.schemas.estimation import CitationReport, EstimateLineItem, LineCitation


def verify_citations(
    estimate_lines: Iterable[EstimateLineItem],
    retrieved_chunk_ids: set[str],
) -> CitationReport:
    """
    Flag any grounded line whose cited chunk_id was never in retrieved context.

    Args:
        estimate_lines: Generated estimate line items with line-level sources.
        retrieved_chunk_ids: Exact chunk ids passed to the model as context.

    Returns:
        CitationReport with grounded, dangling, and insufficient line counts.
    """

    normalized_retrieved_ids = {str(chunk_id) for chunk_id in retrieved_chunk_ids}

    report_lines: list[LineCitation] = []
    grounded_lines = 0
    dangling_lines = 0
    insufficient_lines = 0
    verified_citations = 0
    dangling_citation_ids: set[str] = set()

    for line in estimate_lines:
        cited_chunk_ids = [str(source.chunk_id) for source in line.sources]
        dangling_ids = sorted(
            chunk_id for chunk_id in cited_chunk_ids if chunk_id not in normalized_retrieved_ids
        )

        if not line.grounded:
            insufficient_lines += 1
            status = "insufficient"
        elif dangling_ids:
            dangling_lines += 1
            status = "dangling"
            dangling_citation_ids.update(dangling_ids)
            verified_citations += len(cited_chunk_ids) - len(dangling_ids)
        else:
            grounded_lines += 1
            status = "grounded"
            verified_citations += len(cited_chunk_ids)

        report_lines.append(
            LineCitation(
                component=line.component,
                status=status,
                cited_chunk_ids=cited_chunk_ids,
                dangling_chunk_ids=dangling_ids,
            )
        )

    return CitationReport(
        total_lines=len(report_lines),
        grounded_lines=grounded_lines,
        dangling_lines=dangling_lines,
        insufficient_lines=insufficient_lines,
        verified_citations=verified_citations,
        dangling_citations=sorted(dangling_citation_ids),
        lines=report_lines,
    )
