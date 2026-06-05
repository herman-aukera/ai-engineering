"""
LAYER: embedding_pipeline comparison
RESPONSIBILITY: Compare chunking strategies over the same budget corpus.
WHY IT EXISTS: Session 07 live focuses on learning how chunking strategy changes
               chunk counts, token distribution, and future retrieval behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from pydantic import BaseModel, Field

from app.embedding_pipeline.chunker import JSONStructuralChunker, _encoding_for_embedding_model
from app.embedding_pipeline.schemas import Budget, Chunk


class BudgetChunker(Protocol):
    """Small protocol shared by chunking strategies used in comparisons."""

    def chunk(self, budgets: list[Budget]) -> list[Chunk]:
        """Return chunks for the supplied budgets."""


class WholeBudgetChunker:
    """
    Deliberately broad baseline: one whole budget becomes one chunk.

    This strategy is useful for learning because it shows the opposite of the
    structural component baseline. It should usually be worse for retrieval
    because unrelated components are blended into one vector.
    """

    strategy_name = "whole_budget"

    def __init__(self) -> None:
        self._encoding = _encoding_for_embedding_model()

    def chunk(self, budgets: list[Budget]) -> list[Chunk]:
        """Create one broad chunk per budget."""
        chunks: list[Chunk] = []

        for budget in budgets:
            text = self._build_budget_text(budget)
            chunks.append(
                Chunk(
                    chunk_id=f"{budget.budget_id}::whole_budget",
                    text=text,
                    metadata={
                        "chunking_strategy": self.strategy_name,
                        "budget_id": budget.budget_id,
                        "client_name": budget.client_metadata.name,
                        "client_sector": budget.client_metadata.sector,
                        "client_country": budget.client_metadata.country,
                        "main_technology": budget.main_technology,
                        "year": budget.year,
                        "total_estimated_hours": budget.total_estimated_hours,
                        "component_count": len(budget.components),
                        "component_ids": [
                            component.component_id for component in budget.components
                        ],
                    },
                    token_count=len(self._encoding.encode(text)),
                )
            )

        return chunks

    def _build_budget_text(self, budget: Budget) -> str:
        component_lines = []

        for component in budget.components:
            dependencies = ", ".join(component.dependencies) if component.dependencies else "none"
            component_lines.append(
                "\n".join(
                    [
                        f"- Component: {component.name}",
                        f"  Description: {component.description}",
                        f"  Tech stack: {', '.join(component.tech_stack)}",
                        f"  Complexity: {component.complexity}",
                        f"  Estimated hours: {component.estimated_hours}",
                        f"  Dependencies: {dependencies}",
                    ]
                )
            )

        return "\n".join(
            [
                f"Full budget: {budget.budget_id}",
                f"Project: {budget.project_summary}",
                (
                    f"Client sector: {budget.client_metadata.sector} | "
                    f"Country: {budget.client_metadata.country} | "
                    f"Year: {budget.year}"
                ),
                f"Main technology: {budget.main_technology}",
                f"Total estimated hours: {budget.total_estimated_hours}",
                "",
                "Components:",
                *component_lines,
            ]
        )


class ChunkingStrategySummary(BaseModel):
    """Aggregate stats for one chunking strategy."""

    strategy_name: str = Field(min_length=1)
    total_chunks: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    min_tokens: int = Field(ge=0)
    max_tokens: int = Field(ge=0)
    average_tokens: float = Field(ge=0)
    chunk_ids: list[str]


class ChunkingComparison(BaseModel):
    """Comparison result across multiple chunking strategies."""

    strategies: list[ChunkingStrategySummary] = Field(min_length=1)


class ChunkingComparisonService:
    """Run chunking strategies over the same budget corpus and summarize them."""

    def __init__(self, strategies: Mapping[str, BudgetChunker] | None = None) -> None:
        self._strategies = strategies or {
            "structural_component": JSONStructuralChunker(),
            "whole_budget": WholeBudgetChunker(),
        }

    def compare(self, budgets: list[Budget]) -> ChunkingComparison:
        """Compare all configured strategies on the same budgets."""
        return ChunkingComparison(
            strategies=[
                self._summarize(strategy_name=strategy_name, chunks=chunker.chunk(budgets))
                for strategy_name, chunker in self._strategies.items()
            ]
        )

    def _summarize(
        self,
        strategy_name: str,
        chunks: list[Chunk],
    ) -> ChunkingStrategySummary:
        token_counts = [chunk.token_count for chunk in chunks]
        total_tokens = sum(token_counts)

        return ChunkingStrategySummary(
            strategy_name=strategy_name,
            total_chunks=len(chunks),
            total_tokens=total_tokens,
            min_tokens=min(token_counts, default=0),
            max_tokens=max(token_counts, default=0),
            average_tokens=total_tokens / len(chunks) if chunks else 0,
            chunk_ids=[chunk.chunk_id for chunk in chunks],
        )
