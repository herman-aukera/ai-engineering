from app.prompts.loader import render_estimation_prompt
from app.schemas.estimation import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.services.source_context import RetrievedSourceChunk


def _request() -> EstimationRequest:
    return EstimationRequest(
        description="Build a web SaaS product with payments, authentication, and admin reporting.",
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.DETAILED,
        output_format=OutputFormat.LINE_ITEMS,
    )


def test_render_estimation_prompt_includes_line_citation_rules_when_sources_are_supplied():
    source_chunks = [
        RetrievedSourceChunk(
            chunk_id="chunk-001",
            document_id="BUDGET-2024-0001",
            content="Payments module: 24 hours",
        )
    ]

    system_prompt, user_prompt = render_estimation_prompt(
        _request(),
        version="v1",
        source_chunks=source_chunks,
    )

    assert "Line-level citation rules:" in system_prompt
    assert "Every grounded line must cite one or more exact source id values" in system_prompt
    assert "chunk_id must be copied exactly from the source id attribute" in system_prompt
    assert "document_id must be copied exactly from the source document_id attribute" in system_prompt
    assert "evidence must be a verbatim span or figure from the cited source" in system_prompt
    assert "Do not cite chunk ids that are not present in retrieved_context" in system_prompt
    assert "Use grounded=false" in system_prompt
    assert "Do not invent hours" in system_prompt

    assert '<source id="chunk-001" document_id="BUDGET-2024-0001">' in user_prompt
    assert "Payments module: 24 hours" in user_prompt
    assert "</retrieved_context>" in user_prompt


def test_render_estimation_prompt_without_sources_keeps_existing_prompt_shape():
    system_prompt, user_prompt = render_estimation_prompt(
        _request(),
        version="v1",
    )

    assert "Line-level citation rules:" not in system_prompt
    assert "<retrieved_context>" not in user_prompt
