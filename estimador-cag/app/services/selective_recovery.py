"""Selective agent-assisted recovery over server-owned budget evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import median
from typing import Protocol

from pydantic import BaseModel

from app.generation.graph.ports import BudgetSearcher
from app.generation.graph.state import BudgetMatch, ComponentItem
from app.schemas.agent_runtime import AgentRuntimeLimits, AgentToolSpec
from app.schemas.selective_recovery import (
    SearchRecoveryEvidenceArgs,
    SelectRecoveryEvidenceArgs,
    SelectiveRecoveryResult,
    ValidateRecoveryArgs,
)
from app.services.agent_tool_runtime import (
    AgentModelPort,
    RegisteredAgentTool,
    run_bounded_agent,
)

RECOVERY_SYSTEM_PROMPT = """\
You recover historical evidence only for the supplied flagged software components.
For each component, call search_recovery_evidence with a focused query. Reformulate
when useful. The tool returns a server-owned search_id and exact evidence records.
When a search is suitable, call select_recovery_evidence with that search_id. You
cannot submit hours or edit evidence: Python retains and validates the search result.
After processing every flagged component, call validate_recovery once and then stop.
Leave a component unresolved when no suitable evidence exists. Never invent hours.
"""


class SelectiveRecoveryApplication(Protocol):
    """Graph-facing boundary for bounded evidence recovery."""

    async def recover(
        self,
        *,
        components: Sequence[ComponentItem],
        existing_matches: Sequence[BudgetMatch],
    ) -> SelectiveRecoveryResult:
        """Return only novel accepted matches and bounded runtime evidence."""


def _provenance(match: Mapping[str, object]) -> tuple[str, str, str, str, str]:
    return (
        str(match.get("component_id") or ""),
        str(match.get("budget_id") or ""),
        str(match.get("reference_component_id") or ""),
        str(match.get("source_document_id") or ""),
        str(match.get("source_chunk_id") or ""),
    )


def _recorded_hours(matches: Sequence[BudgetMatch]) -> list[float]:
    return sorted(
        float(match["recorded_hours"])
        for match in matches
        if isinstance(match.get("recorded_hours"), (int, float))
        and not isinstance(match.get("recorded_hours"), bool)
    )


def _tool_spec(
    *,
    name: str,
    description: str,
    arguments_model: type[BaseModel],
) -> AgentToolSpec:
    return AgentToolSpec(
        name=name,
        description=description,
        parameters=arguments_model.model_json_schema(),
    )


@dataclass(frozen=True)
class SelectiveRecoveryService:
    """Let a bounded model reformulate retrieval without authoring arithmetic."""

    model_port: AgentModelPort
    budget_searcher: BudgetSearcher
    search_k: int = 8
    limits: AgentRuntimeLimits = AgentRuntimeLimits(
        max_iterations=8,
        max_tool_calls=16,
        max_elapsed_ms=90_000,
        max_cost_usd=0.5,
        max_model_output_chars=4_000,
        max_tool_output_chars=12_000,
    )

    def __post_init__(self) -> None:
        if self.search_k <= 0:
            raise ValueError("search_k must be positive")

    async def recover(
        self,
        *,
        components: Sequence[ComponentItem],
        existing_matches: Sequence[BudgetMatch],
    ) -> SelectiveRecoveryResult:
        component_map = {
            component["component_id"]: dict(component)
            for component in components
        }
        if len(component_map) != len(components):
            raise ValueError("flagged recovery component IDs must be unique")

        existing_provenance = {
            _provenance(match)
            for match in existing_matches
        }
        search_results: dict[str, list[BudgetMatch]] = {}
        accepted_matches: dict[str, list[BudgetMatch]] = {}
        search_counter = 0

        async def search_handler(arguments: BaseModel) -> dict[str, object]:
            nonlocal search_counter
            parsed = SearchRecoveryEvidenceArgs.model_validate(arguments)
            component = component_map.get(parsed.component_id)
            if component is None:
                raise ValueError("component_id is not in the flagged recovery set")

            search_counter += 1
            search_id = f"{parsed.component_id}:search:{search_counter}"
            query_component: ComponentItem = {
                "component_id": parsed.component_id,
                "name": parsed.query,
                "category": component["category"],
                "requirement_ids": list(component["requirement_ids"]),
            }
            raw_matches = await self.budget_searcher.search_budgets(
                component=query_component,
                k=self.search_k,
            )
            seen = set(existing_provenance)
            novel: list[BudgetMatch] = []
            for raw_match in raw_matches:
                match = BudgetMatch(**dict(raw_match))
                match["component_id"] = parsed.component_id
                key = _provenance(match)
                if key in seen:
                    continue
                seen.add(key)
                novel.append(match)
            search_results[search_id] = novel
            return {
                "search_id": search_id,
                "component_id": parsed.component_id,
                "count": len(novel),
                "matches": novel,
            }

        def select_handler(arguments: BaseModel) -> dict[str, object]:
            parsed = SelectRecoveryEvidenceArgs.model_validate(arguments)
            if parsed.component_id not in component_map:
                raise ValueError("component_id is not in the flagged recovery set")
            matches = search_results.get(parsed.search_id)
            if matches is None:
                raise ValueError("search_id is unknown or expired")
            if any(match["component_id"] != parsed.component_id for match in matches):
                raise ValueError("search_id belongs to a different component")

            hours = _recorded_hours(matches)
            if not hours:
                raise ValueError("selected search has no positive recorded-hours evidence")
            accepted_matches[parsed.component_id] = list(matches)
            estimate = round(float(median(hours)), 2)
            return {
                "component_id": parsed.component_id,
                "accepted_match_count": len(matches),
                "deterministic_median_hours": estimate,
                "source_range_low": min(hours),
                "source_range_high": max(hours),
                "budget_ids": sorted({match["budget_id"] for match in matches}),
            }

        def validate_handler(arguments: BaseModel) -> dict[str, object]:
            parsed = ValidateRecoveryArgs.model_validate(arguments)
            unknown = sorted(set(parsed.component_ids) - set(component_map))
            if unknown:
                raise ValueError(
                    "validation references unknown components: " + ", ".join(unknown)
                )
            recovered = sorted(
                component_id
                for component_id in parsed.component_ids
                if component_id in accepted_matches
            )
            unresolved = sorted(set(parsed.component_ids) - set(recovered))
            return {
                "ok": not unresolved,
                "recovered_component_ids": recovered,
                "unresolved_component_ids": unresolved,
            }

        tools = [
            RegisteredAgentTool(
                spec=_tool_spec(
                    name="search_recovery_evidence",
                    description=(
                        "Search historical budgets for one flagged component using a "
                        "focused or reformulated query."
                    ),
                    arguments_model=SearchRecoveryEvidenceArgs,
                ),
                arguments_model=SearchRecoveryEvidenceArgs,
                handler=search_handler,
            ),
            RegisteredAgentTool(
                spec=_tool_spec(
                    name="select_recovery_evidence",
                    description=(
                        "Accept one server-owned search result and calculate its "
                        "deterministic median without model-authored hours."
                    ),
                    arguments_model=SelectRecoveryEvidenceArgs,
                ),
                arguments_model=SelectRecoveryEvidenceArgs,
                handler=select_handler,
            ),
            RegisteredAgentTool(
                spec=_tool_spec(
                    name="validate_recovery",
                    description=(
                        "Check which flagged components have accepted evidence before "
                        "the recovery loop stops."
                    ),
                    arguments_model=ValidateRecoveryArgs,
                ),
                arguments_model=ValidateRecoveryArgs,
                handler=validate_handler,
            ),
        ]
        component_payload = [
            {
                "component_id": component["component_id"],
                "name": component["name"],
                "category": component["category"],
            }
            for component in components
        ]
        runtime = await run_bounded_agent(
            model_port=self.model_port,
            system_prompt=RECOVERY_SYSTEM_PROMPT,
            user_prompt=(
                "Recover evidence for these flagged components:\n"
                + "\n".join(
                    f"- {item['component_id']}: {item['name']} ({item['category']})"
                    for item in component_payload
                )
            ),
            tools=tools,
            limits=self.limits,
        )
        recovered_component_ids = sorted(accepted_matches)
        flagged_component_ids = sorted(component_map)
        recovered_matches = [
            match
            for component_id in recovered_component_ids
            for match in accepted_matches[component_id]
        ]
        return SelectiveRecoveryResult(
            flagged_component_ids=flagged_component_ids,
            recovered_component_ids=recovered_component_ids,
            unresolved_component_ids=sorted(
                set(flagged_component_ids) - set(recovered_component_ids)
            ),
            recovered_matches=recovered_matches,
            runtime=runtime,
        )
