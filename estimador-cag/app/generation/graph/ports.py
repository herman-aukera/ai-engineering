"""
Injected service ports required by the Session 13 graph nodes.

The graph state stores JSON-safe data only. Runtime model and retrieval services
enter through these protocols and are owned by the application composition root.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from math import isfinite
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
class EstimationPolicy:
    """Deterministic evidence thresholds used by estimation nodes."""

    minimum_grounded_samples: int = 2
    low_confidence_dispersion_ratio: float = 0.5
    conflict_dispersion_ratio: float = 0.75

    def __post_init__(self) -> None:
        if (
            isinstance(self.minimum_grounded_samples, bool)
            or self.minimum_grounded_samples < 2
        ):
            raise ValueError(
                "minimum_grounded_samples must be at least 2"
            )

        low = self.low_confidence_dispersion_ratio
        conflict = self.conflict_dispersion_ratio

        if not isfinite(low) or low < 0:
            raise ValueError(
                "low_confidence_dispersion_ratio must be finite "
                "and non-negative"
            )

        if not isfinite(conflict) or conflict <= low:
            raise ValueError(
                "conflict_dispersion_ratio must be finite and "
                "greater than the low-confidence threshold"
            )


@dataclass(frozen=True)
class GraphNodeDependencies:
    """Runtime services and deterministic policy injected into graph nodes."""

    requirement_extractor: RequirementExtractor
    component_classifier: ComponentClassifier
    budget_searcher: BudgetSearcher
    search_k: int = 5
    estimation_policy: EstimationPolicy = field(
        default_factory=EstimationPolicy
    )

    def __post_init__(self) -> None:
        if self.search_k <= 0:
            raise ValueError("search_k must be positive")
