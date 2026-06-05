from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.comparison import ChunkingComparisonService, WholeBudgetChunker
from app.embedding_pipeline.schemas import Budget


def load_sample_budgets() -> list[Budget]:
    payload = json.loads(Path("data/budgets_sample.json").read_text(encoding="utf-8"))
    return [Budget.model_validate(item) for item in payload]


def test_whole_budget_chunker_creates_one_chunk_per_budget() -> None:
    budgets = load_sample_budgets()

    chunks = WholeBudgetChunker().chunk(budgets)

    assert len(chunks) == len(budgets)
    assert all(chunk.token_count > 0 for chunk in chunks)
    assert chunks[0].chunk_id == f"{budgets[0].budget_id}::whole_budget"
    assert chunks[0].metadata["chunking_strategy"] == "whole_budget"
    assert chunks[0].metadata["budget_id"] == budgets[0].budget_id
    assert chunks[0].metadata["component_count"] == len(budgets[0].components)
    assert "Full budget:" in chunks[0].text
    assert "Components:" in chunks[0].text
    assert budgets[0].components[0].name in chunks[0].text


def test_comparison_service_reports_structural_against_whole_budget_baseline() -> None:
    budgets = load_sample_budgets()

    comparison = ChunkingComparisonService(
        strategies={
            "structural_component": JSONStructuralChunker(),
            "whole_budget": WholeBudgetChunker(),
        }
    ).compare(budgets)

    by_name = {summary.strategy_name: summary for summary in comparison.strategies}

    structural = by_name["structural_component"]
    whole_budget = by_name["whole_budget"]

    expected_component_count = sum(len(budget.components) for budget in budgets)

    assert structural.total_chunks == expected_component_count
    assert whole_budget.total_chunks == len(budgets)

    assert structural.total_tokens > 0
    assert whole_budget.total_tokens > 0

    assert structural.average_tokens == pytest.approx(
        structural.total_tokens / structural.total_chunks
    )
    assert whole_budget.average_tokens == pytest.approx(
        whole_budget.total_tokens / whole_budget.total_chunks
    )

    assert structural.min_tokens <= structural.max_tokens
    assert whole_budget.min_tokens <= whole_budget.max_tokens

    assert len(structural.chunk_ids) == structural.total_chunks
    assert len(whole_budget.chunk_ids) == whole_budget.total_chunks


def test_default_comparison_service_includes_structural_and_whole_budget_strategies() -> None:
    budgets = load_sample_budgets()

    comparison = ChunkingComparisonService().compare(budgets)

    strategy_names = [summary.strategy_name for summary in comparison.strategies]

    assert strategy_names == ["structural_component", "whole_budget"]
