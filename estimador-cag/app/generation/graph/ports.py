"""
Injected service ports required by the Session 13 graph nodes.

The graph state stores JSON-safe data only. Runtime model and retrieval services
enter through these protocols and are owned by the application composition root.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.generation.graph.state import (
    BudgetMatch,
    ComponentItem,
    RequirementItem,
)


@runtime_checkable
class RequirementExtractor(Protocol):
    """Structured requirement extraction boundary."""

    async def extract_requirements(
        self,
        *,
        transcript: str,
    ) -> list[RequirementItem]:
        """Return atomic requirements without mutating graph state."""


@runtime_checkable
class ComponentClassifier(Protocol):
    """Structured component-classification boundary."""

    async def classify_components(
        self,
        *,
        requirements: Sequence[RequirementItem],
    ) -> list[ComponentItem]:
        """Return stable components linked to requirement identifiers."""


@runtime_checkable
class BudgetSearcher(Protocol):
    """Budget-reference retrieval boundary used by the graph."""

    async def search_budgets(
        self,
        *,
        component: ComponentItem,
        k: int,
    ) -> list[BudgetMatch]:
        """Return checkpoint-safe matches for one graph component."""


@dataclass(frozen=True)
class GraphNodeDependencies:
    """Runtime services injected into the required graph nodes."""

    requirement_extractor: RequirementExtractor
    component_classifier: ComponentClassifier
    budget_searcher: BudgetSearcher
    search_k: int = 5

    def __post_init__(self) -> None:
        if self.search_k <= 0:
            raise ValueError("search_k must be positive")
