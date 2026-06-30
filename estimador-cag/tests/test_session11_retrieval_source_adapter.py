from app.persistence.repository import ChunkLexicalSearchResult, ChunkSearchResult
from app.services.source_context import source_chunks_from_retrieval_results


def test_source_chunks_from_semantic_search_results_preserves_ids_and_content():
    results = [
        ChunkSearchResult(
            chunk_id=101,
            document_id=7,
            chunk_type="component",
            content="Payments module: 24 hours",
            distance=0.12,
            metadata={"budget_id": "BUDGET-2024-0007"},
        )
    ]

    source_chunks = source_chunks_from_retrieval_results(results)

    assert len(source_chunks) == 1
    assert source_chunks[0].chunk_id == "101"
    assert source_chunks[0].document_id == "7"
    assert source_chunks[0].content == "Payments module: 24 hours"


def test_source_chunks_from_lexical_search_results_preserves_ids_and_content():
    results = [
        ChunkLexicalSearchResult(
            chunk_id=202,
            document_id=8,
            chunk_type="component",
            content="Authentication: 16 hours",
            rank=0.88,
            metadata={"budget_id": "BUDGET-2024-0008"},
        )
    ]

    source_chunks = source_chunks_from_retrieval_results(results)

    assert len(source_chunks) == 1
    assert source_chunks[0].chunk_id == "202"
    assert source_chunks[0].document_id == "8"
    assert source_chunks[0].content == "Authentication: 16 hours"


def test_source_chunks_from_mixed_retrieval_results_is_deterministic():
    results = [
        ChunkSearchResult(
            chunk_id=101,
            document_id=7,
            chunk_type="component",
            content="Payments module: 24 hours",
            distance=0.12,
            metadata={},
        ),
        ChunkLexicalSearchResult(
            chunk_id=202,
            document_id=8,
            chunk_type="component",
            content="Authentication: 16 hours",
            rank=0.88,
            metadata={},
        ),
    ]

    source_chunks = source_chunks_from_retrieval_results(results)

    assert [chunk.chunk_id for chunk in source_chunks] == ["101", "202"]
    assert [chunk.document_id for chunk in source_chunks] == ["7", "8"]
