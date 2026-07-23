"""
Deterministic Session 13 service fakes.

These adapters support unit tests and local graph evidence without model,
network, embedding, or database calls.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy

from app.generation.graph.state import (
    BudgetMatch,
    ComponentItem,
    RequirementItem,
)
from app.schemas.session14_supervision import (
    SupervisorProposalDestination,
    SupervisorRouteProposal,
    SupervisorStateDigest,
)


class FakeRequirementExtractor:
    """Return configured requirements and record sanitized calls."""

    def __init__(self, requirements: Sequence[RequirementItem]) -> None:
        self._requirements = deepcopy(list(requirements))
        self.calls: list[str] = []

    async def extract_requirements(
        self,
        *,
        transcript: str,
    ) -> list[RequirementItem]:
        self.calls.append(transcript)
        return deepcopy(self._requirements)


class FakeComponentClassifier:
    """Return configured components and record requirement inputs."""

    def __init__(self, components: Sequence[ComponentItem]) -> None:
        self._components = deepcopy(list(components))
        self.calls: list[list[RequirementItem]] = []

    async def classify_components(
        self,
        *,
        requirements: Sequence[RequirementItem],
    ) -> list[ComponentItem]:
        self.calls.append(deepcopy(list(requirements)))
        return deepcopy(self._components)


class FakeBudgetSearcher:
    """Return configured matches keyed by graph component identifier."""

    def __init__(
        self,
        matches_by_component_id: Mapping[str, Sequence[BudgetMatch]],
    ) -> None:
        self._matches_by_component_id = {
            component_id: deepcopy(list(matches))
            for component_id, matches in matches_by_component_id.items()
        }
        self.calls: list[dict[str, str | int]] = []

    async def search_budgets(
        self,
        *,
        component: ComponentItem,
        k: int,
    ) -> list[BudgetMatch]:
        component_id = component["component_id"]
        self.calls.append(
            {
                "component_id": component_id,
                "k": k,
            }
        )
        matches = self._matches_by_component_id.get(component_id, [])
        return deepcopy(matches[:k])


class FakeSupervisorRouteProposer:
    """Return configured typed proposals and record sanitized routing inputs."""

    def __init__(
        self,
        destinations: Sequence[SupervisorProposalDestination],
    ) -> None:
        self._destinations = list(destinations)
        self.calls: list[dict[str, object]] = []

    async def propose_route(
        self,
        *,
        digest: SupervisorStateDigest,
        candidates: Sequence[SupervisorProposalDestination],
    ) -> SupervisorRouteProposal:
        self.calls.append(
            {
                "digest": digest.model_dump(mode="json"),
                "candidates": list(candidates),
            }
        )
        if not self._destinations:
            raise RuntimeError("no fake supervisor proposal remains")
        return SupervisorRouteProposal(
            next_agent=self._destinations.pop(0),
            reason="Configured deterministic fake route proposal.",
        )
