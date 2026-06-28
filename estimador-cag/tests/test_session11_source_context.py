from app.services.source_context import (
    RetrievedSourceChunk,
    build_line_citation_prompt_rules,
    render_source_context,
)


def test_render_source_context_includes_exact_chunk_id_document_id_and_content():
    chunks = [
        RetrievedSourceChunk(
            chunk_id="chunk-001",
            document_id="BUDGET-2024-0001",
            content="Payments module: 24 hours",
        ),
        RetrievedSourceChunk(
            chunk_id="chunk-002",
            document_id="BUDGET-2024-0002",
            content="Authentication: 16 hours",
        ),
    ]

    rendered = render_source_context(chunks)

    assert '<source id="chunk-001" document_id="BUDGET-2024-0001">' in rendered
    assert "Payments module: 24 hours" in rendered
    assert "</source>" in rendered
    assert '<source id="chunk-002" document_id="BUDGET-2024-0002">' in rendered
    assert "Authentication: 16 hours" in rendered


def test_render_source_context_escapes_xml_sensitive_characters():
    chunks = [
        RetrievedSourceChunk(
            chunk_id="chunk<&001",
            document_id='BUDGET-"2024"',
            content="Use <OAuth> & SSO",
        )
    ]

    rendered = render_source_context(chunks)

    assert "chunk&lt;&amp;001" in rendered
    assert "BUDGET-&quot;2024&quot;" in rendered
    assert "Use &lt;OAuth&gt; &amp; SSO" in rendered


def test_render_source_context_returns_clear_empty_context_marker():
    rendered = render_source_context([])

    assert rendered == "<retrieved_context>\nNO_RETRIEVED_CONTEXT\n</retrieved_context>"


def test_line_citation_prompt_rules_require_exact_ids_and_verbatim_evidence():
    rules = build_line_citation_prompt_rules()

    assert "Every grounded line must cite one or more exact source id values" in rules
    assert "chunk_id must be copied exactly from the source id attribute" in rules
    assert "document_id must be copied exactly from the source document_id attribute" in rules
    assert "evidence must be a verbatim span or figure from the cited source" in rules
    assert "Do not cite chunk ids that are not present in retrieved_context" in rules
    assert "Use grounded=false" in rules
    assert "Do not invent hours" in rules
