"""Runtime binding between checkpointed stage routes and provider calls."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import litellm
from pydantic import BaseModel, ValidationError

from app.config import TierName, settings
from app.schemas.agent_runtime import AgentModelTurn, AgentToolSpec
from app.schemas.provider_readiness import BenchmarkSnapshot, GraphStage, StageRouteDecision
from app.schemas.v3_routing import ComplexityLevel
from app.schemas.v5_provider_selection import ProviderSelection
from app.services.agent_tool_runtime import AgentModelPort
from app.services.costs import estimate_cost_usd
from app.services.litellm_agent_model import (
    AgentProviderContractError,
    _content,
    _first_choice,
    _litellm_completion_model,
    _tool_calls,
    _tools_payload,
    _usage,
    _value,
)
from app.services.litellm_provider import LiteLLMProvider, ResolvedModel
from app.services.provider_readiness import StageRoutingPolicy

_PLACEHOLDER_KEYS = frozenset({"", "test", "dummy", "fake", "placeholder", "example"})
_ACTIVE_STAGE_ROUTE: ContextVar[StageRouteDecision | None] = ContextVar(
    "session13_plus_active_stage_route",
    default=None,
)


class ProviderCredentialUnavailableError(RuntimeError):
    """Raised before a provider call when the selected credential is unavailable."""


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    """Secret-bearing process configuration; never stored in graph state."""

    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_models: Mapping[str, str]
    kimi_api_key: str
    kimi_base_url: str
    kimi_models: Mapping[str, str]
    openai_api_key: str
    openai_base_url: str
    openai_models: Mapping[str, str]

    @classmethod
    def from_settings(cls) -> ProviderRuntimeConfig:
        kimi_models = {
            "flash": settings.kimi_model,
            "pro": settings.kimi_model_pro,
        }
        if settings.kimi_model_max.strip():
            kimi_models["max"] = settings.kimi_model_max.strip()
        return cls(
            deepseek_api_key=settings.deepseek_api_key,
            deepseek_base_url=settings.deepseek_base_url,
            deepseek_models={
                "flash": settings.deepseek_model,
                "pro": settings.deepseek_model_pro,
                "max": settings.deepseek_model_pro,
            },
            kimi_api_key=settings.kimi_api_key,
            kimi_base_url=settings.kimi_base_url,
            kimi_models=kimi_models,
            openai_api_key=settings.openai_api_key,
            openai_base_url=settings.openai_base_url,
            openai_models={
                "flash": settings.openai_model_luna,
                "pro": settings.openai_model_terra,
                "max": settings.openai_model_sol,
            },
        )

    def model_catalog(self) -> dict[str, Mapping[str, str]]:
        return {
            "deepseek": dict(self.deepseek_models),
            "moonshot": dict(self.kimi_models),
            "openai": dict(self.openai_models),
            "deterministic": {
                "flash": "python",
                "pro": "python",
                "max": "python",
            },
        }


def load_benchmark_snapshot(path: str) -> BenchmarkSnapshot | None:
    normalized = path.strip()
    if not normalized:
        return None
    snapshot_path = Path(normalized)
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return BenchmarkSnapshot.model_validate(payload)


@dataclass(frozen=True)
class StageRoutingRuntime:
    """Resolve one route per leaf stage and bind it during node execution."""

    policy: StageRoutingPolicy

    @classmethod
    def from_settings(cls) -> StageRoutingRuntime:
        config = ProviderRuntimeConfig.from_settings()
        snapshot = load_benchmark_snapshot(settings.provider_benchmark_snapshot_path)
        return cls(
            policy=StageRoutingPolicy(
                benchmark_snapshot=snapshot,
                model_catalog=config.model_catalog(),
            )
        )

    def resolve(
        self,
        *,
        stage: GraphStage,
        state: Mapping[str, object],
    ) -> StageRouteDecision:
        raw_selection = state.get("provider_selection")
        selection = ProviderSelection.model_validate(
            raw_selection if isinstance(raw_selection, Mapping) else {}
        )
        complexity = _complexity_from_state(state)
        return self.policy.resolve(
            stage=stage,
            selection=selection,
            complexity_level=complexity,
        )

    @contextmanager
    def bind(self, route: StageRouteDecision) -> Iterator[None]:
        token = _ACTIVE_STAGE_ROUTE.set(route)
        try:
            yield
        finally:
            _ACTIVE_STAGE_ROUTE.reset(token)


def _complexity_from_state(state: Mapping[str, object]) -> ComplexityLevel:
    for key, level_key in (
        ("arbitrated_assessment", "arbitrated_level"),
        ("v3_complexity", "level"),
    ):
        raw = state.get(key)
        if isinstance(raw, Mapping):
            candidate = raw.get(level_key)
            if candidate in {"C0", "C1", "C2", "C3", "C4", "C5"}:
                return candidate  # type: ignore[return-value]
    return "C2"


def current_stage_route() -> StageRouteDecision | None:
    """Return the route bound to the currently executing graph node."""

    return _ACTIVE_STAGE_ROUTE.get()


def _is_placeholder_key(value: str) -> bool:
    return value.strip().lower() in _PLACEHOLDER_KEYS


def _reasoning_kwargs(route: StageRouteDecision | None) -> dict[str, object]:
    if route is None or route.execution_kind != "model":
        return {}
    if route.provider == "deepseek":
        if route.effort == "none":
            return {"extra_body": {"thinking": {"type": "disabled"}}}
        return {
            "reasoning_effort": route.effort,
            "extra_body": {"thinking": {"type": "enabled"}},
        }
    if route.provider in {"openai", "moonshot"} and route.effort != "none":
        return {"extra_body": {"reasoning_effort": route.effort}}
    return {}


def _sampling_kwargs(
    *,
    route: StageRouteDecision | None,
    resolved: ResolvedModel,
) -> dict[str, object]:
    kwargs = _reasoning_kwargs(route)
    if route is None or route.provider == "deepseek":
        kwargs["temperature"] = resolved.temperature
    return kwargs


@dataclass(frozen=True)
class StageRoutedLiteLLMProvider(LiteLLMProvider):
    """Use the bound stage route instead of one process-wide logical tier."""

    runtime_config: ProviderRuntimeConfig = field(
        default_factory=ProviderRuntimeConfig.from_settings
    )

    def resolve_model(self, tier: TierName) -> ResolvedModel:
        route = current_stage_route()
        if route is None or route.execution_kind != "model":
            return super().resolve_model(tier)

        if route.provider == "deepseek":
            key = self.runtime_config.deepseek_api_key
            base_url = self.runtime_config.deepseek_base_url
            temperature = 0.3
        elif route.provider == "moonshot":
            key = self.runtime_config.kimi_api_key
            base_url = self.runtime_config.kimi_base_url
            temperature = 1.0
        elif route.provider == "openai":
            key = self.runtime_config.openai_api_key
            base_url = self.runtime_config.openai_base_url
            temperature = 0.2
        else:
            raise ProviderCredentialUnavailableError(
                f"Stage {route.stage} does not resolve to a model provider."
            )

        if _is_placeholder_key(key):
            raise ProviderCredentialUnavailableError(
                f"Credential unavailable for provider={route.provider}, stage={route.stage}."
            )

        model = route.model
        if route.provider == "moonshot" and not model.startswith("moonshot/"):
            model = f"moonshot/{model}"
        return ResolvedModel(
            tier=tier,
            provider=route.provider,
            model=model,
            api_key=key,
            base_url=base_url,
            temperature=temperature,
        )

    def complete_structured_messages(
        self,
        *,
        messages: list[dict[str, str]],
        tier: TierName,
        response_model: type[BaseModel],
        max_tokens: int = 2000,
    ) -> dict[str, object]:
        resolved = self.resolve_model(tier)
        route = current_stage_route()
        structured_messages = self._messages_with_json_schema_contract(
            messages=messages,
            response_model=response_model,
        )
        request_kwargs = _sampling_kwargs(route=route, resolved=resolved)
        response = litellm.completion(
            model=resolved.model,
            messages=structured_messages,
            api_key=resolved.api_key,
            api_base=resolved.base_url,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            **request_kwargs,
        )
        try:
            result = self._validated_structured_result(
                response=response,
                response_model=response_model,
            )
            final_response = response
        except (ValidationError, TypeError, ValueError) as exc:
            raw_content = self._extract_raw_message_content(response)
            if not raw_content:
                raise RuntimeError(
                    f"Invalid structured payload from {resolved.model}: {exc}"
                ) from exc
            final_response = litellm.completion(
                model=resolved.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Return exactly one valid JSON object matching the supplied "
                            "schema. No markdown or prose."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "schema": response_model.model_json_schema(),
                                "model_output": raw_content[:8000],
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                ],
                api_key=resolved.api_key,
                api_base=resolved.base_url,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                **request_kwargs,
            )
            result = self._validated_structured_result(
                response=final_response,
                response_model=response_model,
            )

        usage = self._extract_usage(final_response)
        input_tokens = usage["input_tokens"]
        output_tokens = usage["output_tokens"]
        cost = estimate_cost_usd(
            model=resolved.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return {
            "result": result,
            "model": resolved.model,
            "tier": resolved.tier,
            "provider": resolved.provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost["cost_usd"],
            "cost_source": cost["cost_source"],
            "pricing_model": cost["pricing_model"],
            "finish_reason": self._extract_finish_reason(final_response),
        }


@dataclass(frozen=True)
class StageRoutedAgentModel(AgentModelPort):
    """Bounded recovery model that consumes the same stage route context."""

    provider: StageRoutedLiteLLMProvider
    tier: TierName = "flash"
    max_tokens: int = 2000

    async def complete_turn(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[AgentToolSpec],
    ) -> AgentModelTurn:
        resolved = self.provider.resolve_model(self.tier)
        route = current_stage_route()
        response = await litellm.acompletion(
            model=_litellm_completion_model(
                provider=resolved.provider,
                model=resolved.model,
            ),
            messages=list(messages),
            tools=_tools_payload(tools),
            tool_choice="auto" if tools else None,
            api_key=resolved.api_key,
            api_base=resolved.base_url,
            max_tokens=self.max_tokens,
            **_sampling_kwargs(route=route, resolved=resolved),
        )
        choice = _first_choice(response)
        message = _value(choice, "message")
        if message is None:
            raise AgentProviderContractError(
                "provider choice does not contain a message"
            )
        input_tokens, output_tokens = _usage(response)
        cost = estimate_cost_usd(
            model=resolved.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        raw_cost = cost.get("cost_usd")
        normalized_cost = (
            max(0.0, float(raw_cost))
            if isinstance(raw_cost, (int, float)) and not isinstance(raw_cost, bool)
            else 0.0
        )
        finish_reason = _value(choice, "finish_reason")
        return AgentModelTurn(
            content=_content(message),
            tool_calls=_tool_calls(message),
            provider=resolved.provider,
            model=resolved.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=normalized_cost,
            finish_reason=(
                str(finish_reason) if finish_reason is not None else None
            ),
        )
