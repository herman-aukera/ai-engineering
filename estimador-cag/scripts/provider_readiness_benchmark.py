"""Matched live-provider benchmark for Session 13 Plus readiness.

The runner emits sanitized JSON artifacts only. It never writes credentials,
prompts containing private project data, raw provider responses, or stack traces.
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import litellm

from app.schemas.provider_readiness import (
    BenchmarkSnapshot,
    ModelBenchmarkSummary,
)

OUT_DIR = Path(os.environ.get("PROVIDER_READINESS_OUT", "artifacts/provider-readiness"))
_PLACEHOLDERS = frozenset({"", "test", "dummy", "fake", "placeholder", "example"})
_CASES = (
    {
        "id": "exact_text",
        "system": "Return exactly the requested token. No punctuation or explanation.",
        "user": "Return exactly: READY",
    },
    {
        "id": "structured_json",
        "system": "Return exactly one valid JSON object. No markdown or prose.",
        "user": 'Return {"answer":4,"label":"sum"} with those exact values.',
    },
    {
        "id": "tool_call",
        "system": "Use the supplied function exactly once. Do not answer with prose.",
        "user": "Record value 7 with label seven.",
    },
)
_TOOL = {
    "type": "function",
    "function": {
        "name": "record_value",
        "description": "Record one benchmark value.",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {"type": "integer"},
                "label": {"type": "string"},
            },
            "required": ["value", "label"],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class Route:
    provider: str
    model: str
    effort: str
    api_key: str
    base_url: str

    @property
    def litellm_model(self) -> str:
        if self.provider == "moonshot" and not self.model.startswith("moonshot/"):
            return f"moonshot/{self.model}"
        return self.model


def _present(value: str) -> bool:
    return value.strip().lower() not in _PLACEHOLDERS


def _split_routes(value: str) -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for item in value.split(","):
        normalized = item.strip()
        if not normalized:
            continue
        model, separator, effort = normalized.partition(":")
        routes.append((model.strip(), effort.strip() if separator else "high"))
    return routes


def _discover_kimi_models(api_key: str, base_url: str) -> list[str]:
    if not _present(api_key):
        return []
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return []
    return sorted(
        str(item.get("id"))
        for item in data
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    )


def _routes() -> list[Route]:
    routes: list[Route] = []
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if _present(deepseek_key):
        for model, effort in _split_routes(
            os.environ.get(
                "DEEPSEEK_BENCHMARK_ROUTES",
                "deepseek-v4-flash:high,deepseek-v4-pro:max",
            )
        ):
            routes.append(
                Route(
                    provider="deepseek",
                    model=model,
                    effort=effort,
                    api_key=deepseek_key,
                    base_url=os.environ.get(
                        "DEEPSEEK_BASE_URL",
                        "https://api.deepseek.com/v1",
                    ),
                )
            )

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if _present(openai_key):
        for model, effort in _split_routes(
            os.environ.get(
                "OPENAI_BENCHMARK_ROUTES",
                "gpt-5.6-luna:low,gpt-5.6-terra:medium,gpt-5.6-sol:max",
            )
        ):
            routes.append(
                Route(
                    provider="openai",
                    model=model,
                    effort=effort,
                    api_key=openai_key,
                    base_url=os.environ.get(
                        "OPENAI_BASE_URL",
                        "https://api.openai.com/v1",
                    ),
                )
            )

    kimi_key = os.environ.get("KIMI_API_KEY", "")
    kimi_base = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.ai/v1")
    if _present(kimi_key):
        configured = _split_routes(os.environ.get("KIMI_BENCHMARK_ROUTES", ""))
        available = _discover_kimi_models(kimi_key, kimi_base)
        if configured:
            selected = [(model, effort) for model, effort in configured if model in available]
        else:
            k3 = [model for model in available if "k3" in model.lower()]
            if k3:
                selected = [(k3[-1], effort) for effort in ("low", "high", "max")]
            else:
                preferred = [
                    model
                    for model in available
                    if any(token in model.lower() for token in ("k2.6", "k2.5", "k2"))
                ]
                selected = [(preferred[-1], "high")] if preferred else []
        for model, effort in selected:
            routes.append(
                Route(
                    provider="moonshot",
                    model=model,
                    effort=effort,
                    api_key=kimi_key,
                    base_url=kimi_base,
                )
            )
    return routes


def _reasoning_kwargs(route: Route) -> dict[str, object]:
    if route.provider == "deepseek":
        return {
            "reasoning_effort": route.effort,
            "extra_body": {"thinking": {"type": "enabled"}},
        }
    return {"reasoning_effort": route.effort}


def _usage(response: object) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    prompt = getattr(usage, "prompt_tokens", 0) if usage is not None else 0
    completion = getattr(usage, "completion_tokens", 0) if usage is not None else 0
    return int(prompt or 0), int(completion or 0)


def _response_cost(response: object) -> float | None:
    hidden = getattr(response, "_hidden_params", None)
    if isinstance(hidden, dict):
        value = hidden.get("response_cost")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0.0, float(value))
    try:
        value = litellm.completion_cost(completion_response=response)
    except Exception:
        return None
    return max(0.0, float(value)) if isinstance(value, (int, float)) else None


def _first_message(response: object) -> object:
    choices = getattr(response, "choices", None)
    if not isinstance(choices, list) or not choices:
        raise ValueError("missing choices")
    message = getattr(choices[0], "message", None)
    if message is None:
        raise ValueError("missing message")
    return message


def _text(message: object) -> str:
    content = getattr(message, "content", None)
    return content.strip() if isinstance(content, str) else ""


def _tool_arguments(message: object) -> dict[str, Any] | None:
    tool_calls = getattr(message, "tool_calls", None)
    if not isinstance(tool_calls, list) or len(tool_calls) != 1:
        return None
    function = getattr(tool_calls[0], "function", None)
    name = getattr(function, "name", None)
    arguments = getattr(function, "arguments", None)
    if name != "record_value" or not isinstance(arguments, str):
        return None
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _case(route: Route, case: dict[str, str]) -> dict[str, object]:
    start = time.perf_counter()
    try:
        kwargs: dict[str, object] = {
            "model": route.litellm_model,
            "messages": [
                {"role": "system", "content": case["system"]},
                {"role": "user", "content": case["user"]},
            ],
            "api_key": route.api_key,
            "api_base": route.base_url,
            "temperature": 0,
            "max_tokens": 256,
            **_reasoning_kwargs(route),
        }
        if case["id"] == "structured_json":
            kwargs["response_format"] = {"type": "json_object"}
        if case["id"] == "tool_call":
            kwargs["tools"] = [_TOOL]
            kwargs["tool_choice"] = "auto"
        response = litellm.completion(**kwargs)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        message = _first_message(response)
        if case["id"] == "exact_text":
            passed = _text(message) == "READY"
        elif case["id"] == "structured_json":
            try:
                parsed = json.loads(_text(message))
            except json.JSONDecodeError:
                parsed = None
            passed = parsed == {"answer": 4, "label": "sum"}
        else:
            passed = _tool_arguments(message) == {"value": 7, "label": "seven"}
        input_tokens, output_tokens = _usage(response)
        return {
            "case_id": case["id"],
            "passed": passed,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": _response_cost(response),
            "error_type": None,
            "http_status": None,
        }
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if not isinstance(status, int):
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
        return {
            "case_id": case["id"],
            "passed": False,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": None,
            "error_type": type(exc).__name__,
            "http_status": status if isinstance(status, int) else None,
        }


def _summary(route: Route, results: list[dict[str, object]]) -> ModelBenchmarkSummary:
    pass_count = sum(result["passed"] is True for result in results)
    structured = next(result for result in results if result["case_id"] == "structured_json")
    tool = next(result for result in results if result["case_id"] == "tool_call")
    latencies = [float(result["latency_ms"]) for result in results]
    costs = [
        float(result["cost_usd"])
        for result in results
        if isinstance(result["cost_usd"], (int, float))
    ]
    if pass_count == len(results):
        status = "benchmark_calibrated"
    elif pass_count > 0 and structured["passed"] and tool["passed"]:
        status = "contract_verified"
    elif pass_count > 0:
        status = "reachable"
    else:
        status = "unavailable"
    return ModelBenchmarkSummary(
        provider=route.provider,
        model=route.model,
        effort=route.effort,
        status=status,
        sample_count=len(results),
        quality_score=pass_count / len(results),
        schema_pass_rate=1.0 if structured["passed"] else 0.0,
        tool_pass_rate=1.0 if tool["passed"] else 0.0,
        median_latency_ms=statistics.median(latencies),
        median_cost_usd=statistics.median(costs) if costs else None,
        failure_count=len(results) - pass_count,
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    routes = _routes()
    raw_routes: list[dict[str, object]] = []
    summaries: list[ModelBenchmarkSummary] = []
    for route in routes:
        results = [_case(route, case) for case in _CASES]
        summaries.append(_summary(route, results))
        raw_routes.append(
            {
                "provider": route.provider,
                "model": route.model,
                "effort": route.effort,
                "results": results,
            }
        )

    cases_json = json.dumps(_CASES, sort_keys=True, separators=(",", ":"))
    snapshot = BenchmarkSnapshot(
        version="session13-plus-live-v1",
        source_commit=os.environ.get("GITHUB_SHA", "local-readiness-run"),
        cases_hash=hashlib.sha256(cases_json.encode("utf-8")).hexdigest(),
        created_at=datetime.now(UTC),
        required_providers=["deepseek", "moonshot", "openai"],
        summaries=summaries,
    )
    report = {
        "snapshot": snapshot.model_dump(mode="json"),
        "auto_eligible": snapshot.has_complete_provider_coverage(),
        "configured_route_count": len(routes),
        "routes": raw_routes,
    }
    (OUT_DIR / "provider-readiness-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUT_DIR / "provider-benchmark-snapshot.json").write_text(
        snapshot.model_dump_json(indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "auto_eligible": report["auto_eligible"],
                "configured_route_count": len(routes),
                "summaries": [summary.model_dump(mode="json") for summary in summaries],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
