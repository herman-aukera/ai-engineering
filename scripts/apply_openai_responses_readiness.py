"""Apply the exact OpenAI Responses readiness integration."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def replace_once(relative: str, old: str, new: str) -> None:
    content = read(relative)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match in {relative}, found {count}: {old[:100]!r}")
    write(relative, content.replace(old, new, 1))


def patch_provider_policy() -> None:
    replace_once(
        "estimador-cag/app/services/provider_readiness.py",
        'return {"minimal": "low", "medium": "medium", "max": "max"}[intent]',
        'return {"minimal": "low", "medium": "medium", "max": "xhigh"}[intent]',
    )


def patch_runtime() -> None:
    relative = "estimador-cag/app/services/stage_routing_runtime.py"
    content = read(relative)
    import_anchor = "from app.services.litellm_provider import LiteLLMProvider, ResolvedModel\n"
    import_line = (
        "from app.services.openai_responses_agent import "
        "complete_openai_responses_turn\n"
    )
    if import_line not in content:
        if import_anchor not in content:
            raise RuntimeError("Stage runtime import anchor missing")
        content = content.replace(import_anchor, import_anchor + import_line, 1)

    old = '''        resolved = self.provider.resolve_model(self.tier)\n        route = current_stage_route()\n        response = await litellm.acompletion(\n'''
    new = '''        resolved = self.provider.resolve_model(self.tier)\n        route = current_stage_route()\n        if route is not None and route.provider == "openai":\n            return await complete_openai_responses_turn(\n                api_key=resolved.api_key,\n                base_url=resolved.base_url,\n                model=resolved.model,\n                effort=route.effort,\n                messages=messages,\n                tools=tools,\n                max_output_tokens=self.max_tokens,\n            )\n        response = await litellm.acompletion(\n'''
    if old not in content:
        raise RuntimeError("StageRoutedAgentModel insertion anchor missing")
    content = content.replace(old, new, 1)
    write(relative, content)


def patch_benchmark() -> None:
    relative = "estimador-cag/scripts/provider_readiness_benchmark.py"
    content = read(relative)
    content = content.replace(
        '"gpt-5.6-luna:low,gpt-5.6-terra:medium,gpt-5.6-sol:max",',
        '"gpt-5.6-luna:low,gpt-5.6-terra:medium,gpt-5.6-sol:xhigh",',
        1,
    )

    import_anchor = "from app.schemas.provider_readiness import BenchmarkSnapshot, ModelBenchmarkSummary\n"
    helper_import = '''from app.services.openai_responses_agent import (\n    benchmark_openai_tool_call,\n    benchmark_responses_tool_arguments,\n)\n'''
    if helper_import not in content:
        if import_anchor not in content:
            raise RuntimeError("Benchmark import anchor missing")
        content = content.replace(import_anchor, import_anchor + helper_import, 1)

    constants_anchor = "_KIMI_K3_OUTPUT_USD_PER_MILLION = 15.0\n"
    constants = '''_OPENAI_PRICE_SOURCE = "https://openai.com/index/gpt-5-6/"\n_OPENAI_PRICES = {\n    "gpt-5.6-luna": (0.80, 4.80),\n    "gpt-5.6-terra": (2.00, 12.00),\n    "gpt-5.6-sol": (3.50, 21.00),\n}\n'''
    if constants not in content:
        if constants_anchor not in content:
            raise RuntimeError("Benchmark pricing anchor missing")
        content = content.replace(constants_anchor, constants_anchor + constants, 1)

    usage_old = '''def _usage(response: object) -> tuple[int, int]:\n    usage = getattr(response, "usage", None)\n    prompt = getattr(usage, "prompt_tokens", 0) if usage is not None else 0\n    completion = getattr(usage, "completion_tokens", 0) if usage is not None else 0\n    return int(prompt or 0), int(completion or 0)\n'''
    usage_new = '''def _usage(response: object) -> tuple[int, int]:\n    usage = getattr(response, "usage", None)\n    if usage is None:\n        return 0, 0\n    prompt = getattr(usage, "prompt_tokens", None)\n    completion = getattr(usage, "completion_tokens", None)\n    if prompt is None:\n        prompt = getattr(usage, "input_tokens", 0)\n    if completion is None:\n        completion = getattr(usage, "output_tokens", 0)\n    return int(prompt or 0), int(completion or 0)\n'''
    if usage_old not in content:
        raise RuntimeError("Benchmark usage function changed")
    content = content.replace(usage_old, usage_new, 1)

    cost_anchor = '''    if route.provider == "moonshot" and route.model.lower() in {"kimi-k3", "k3"}:\n'''
    openai_cost = '''    if route.provider == "openai" and route.model in _OPENAI_PRICES:\n        input_price, output_price = _OPENAI_PRICES[route.model]\n        cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000\n        return cost, "official_openai_gpt56_2026-07"\n'''
    if openai_cost not in content:
        if cost_anchor not in content:
            raise RuntimeError("Benchmark cost anchor missing")
        content = content.replace(cost_anchor, openai_cost + cost_anchor, 1)

    case_anchor = '''    try:\n        kwargs: dict[str, object] = {\n'''
    responses_case = '''    try:\n        if route.provider == "openai" and case["id"] == "tool_call":\n            response = benchmark_openai_tool_call(\n                api_key=route.api_key,\n                base_url=route.base_url,\n                model=route.model,\n                effort=route.effort,\n                instructions=case["system"],\n                user_input=case["user"],\n                tool=_TOOL,\n                max_output_tokens=256,\n            )\n            latency_ms = round((time.perf_counter() - start) * 1000, 2)\n            passed = benchmark_responses_tool_arguments(response) == {\n                "value": 7,\n                "label": "seven",\n            }\n            input_tokens, output_tokens = _usage(response)\n            cost_usd, cost_source = _response_cost(\n                route=route,\n                response=response,\n                input_tokens=input_tokens,\n                output_tokens=output_tokens,\n            )\n            return {\n                "case_id": case["id"],\n                "passed": passed,\n                "latency_ms": latency_ms,\n                "input_tokens": input_tokens,\n                "output_tokens": output_tokens,\n                "cost_usd": cost_usd,\n                "cost_source": cost_source,\n                "error_type": None,\n                "error_code": None,\n                "error_detail": None,\n                "http_status": None,\n            }\n        kwargs: dict[str, object] = {\n'''
    if case_anchor not in content:
        raise RuntimeError("Benchmark case anchor missing")
    content = content.replace(case_anchor, responses_case, 1)

    pricing_anchor = '''        "pricing_sources": {\n            "kimi_k3": {\n'''
    pricing_replacement = '''        "pricing_sources": {\n            "openai_gpt56": {\n                "source_url": _OPENAI_PRICE_SOURCE,\n                "models": {\n                    model: {\n                        "input_usd_per_million": prices[0],\n                        "output_usd_per_million": prices[1],\n                    }\n                    for model, prices in _OPENAI_PRICES.items()\n                },\n                "version": "2026-07",\n            },\n            "kimi_k3": {\n'''
    if pricing_anchor not in content:
        raise RuntimeError("Benchmark pricing report anchor missing")
    content = content.replace(pricing_anchor, pricing_replacement, 1)
    write(relative, content)


def main() -> None:
    patch_provider_policy()
    patch_runtime()
    patch_benchmark()


if __name__ == "__main__":
    main()
