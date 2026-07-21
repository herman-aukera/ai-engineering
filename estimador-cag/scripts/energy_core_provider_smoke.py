"""Provider pipeline smoke test — deterministic, no keys, CI-safe.

Exercises: registry -> selector -> fake adapter -> served evidence -> CLI -> API.
Uses fake adapters only. Requires no provider keys or network access.

Usage:
    uv run python scripts/energy_core_provider_smoke.py
"""

import sys
from decimal import Decimal  # noqa: I001
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from energy_core.provider_adapter import FakeProviderAdapter  # noqa: E402, I001
from energy_core.provider_registry import CapabilityRegistry, ProviderSelection  # noqa: E402
from energy_core.selector_api import SelectRequest, SelectorAPI  # noqa: E402


def _check(condition: bool, label: str) -> int:
    if not condition:
        print(f"FAIL: {label}")
        return 1
    print(f"  PASS: {label}")
    return 0


def main() -> int:
    fails = 0

    # 1. Registry loads all expected models
    registry = CapabilityRegistry()
    models = registry.list_available_models()
    model_ids = {m.model_id for m in models}
    fails += _check(len(models) >= 9, f"registry has {len(models)} available models")
    fails += _check("deepseek-v4-flash" in model_ids, "deepseek-v4-flash registered")
    fails += _check("k3" in model_ids, "kimi code k3 registered")
    fails += _check("gpt-5.6-sol" in model_ids, "gpt-5.6-sol registered")

    # 2. Profile resolution
    from energy_core.provider_registry import ProviderSelector
    selector = ProviderSelector(registry)

    deepseek_plan = selector.select(ProviderSelection(provider="deepseek", profile="max"))
    fails += _check(deepseek_plan.model_id == "deepseek-v4-pro", "deepseek max -> v4-pro")

    kimi_plan = selector.select(ProviderSelection(provider="kimi", profile="max"))
    fails += _check(kimi_plan.model_id == "k3", "kimi max -> k3")

    openai_plan = selector.select(ProviderSelection(provider="openai", profile="medium"))
    fails += _check(openai_plan.model_id == "gpt-5.6-terra", "openai medium -> terra")

    auto_plan = selector.select(ProviderSelection(provider="auto", profile="medium"))
    fails += _check(auto_plan.provider == "deepseek", "auto -> deepseek default")

    # 3. Budget enforcement
    try:
        selector.select(ProviderSelection(
            provider="openai", profile="max", max_cost_usd=Decimal("0.000001"),
            premium_reason="test",
        ))
        fails += _check(False, "openai tiny budget should fail")
    except ValueError:
        fails += _check(True, "openai tiny budget correctly rejected")

    # 4. Fake adapter produces served evidence
    adapter = FakeProviderAdapter(registry=registry)
    evidence = adapter.invoke(ProviderSelection(provider="kimi", profile="max"))
    fails += _check(evidence.served_model_id == "k3", "fake adapter serves k3")
    fails += _check(evidence.execution_performed is False, "fake adapter: execution_performed=False")
    fails += _check(len(evidence.attempts) == 1, "fake adapter: one attempt")
    fails += _check(evidence.attempts[0].status == "success", "fake adapter: attempt success")
    fails += _check(evidence.circuit_state == "closed", "fake adapter: circuit closed")

    # 5. Fake adapter with custom served model
    custom = FakeProviderAdapter(
        registry=registry,
        served_model_id="custom-model",
        inject_input_tokens=1000,
        inject_output_tokens=500,
    )
    custom_evidence = custom.invoke(ProviderSelection(provider="deepseek", profile="medium"))
    fails += _check(custom_evidence.served_model_id == "custom-model", "custom served model_id")
    fails += _check(custom_evidence.tokens.input_tokens == 1000, "custom input tokens")
    fails += _check(custom_evidence.tokens.output_tokens == 500, "custom output tokens")

    # 6. Fake adapter failure injection
    fail_adapter = FakeProviderAdapter(inject_failure=True)
    fail_evidence = fail_adapter.invoke(ProviderSelection())
    fails += _check(fail_evidence.circuit_state == "open", "injected failure: circuit open")
    fails += _check(fail_evidence.attempts[0].status == "failed", "injected failure: status failed")

    # 7. Selector API
    api = SelectorAPI(registry)
    api_resp = api.select(SelectRequest(provider="kimi", profile="max"))
    fails += _check(api_resp.status == "ok", "API select kimi/max ok")
    fails += _check(api_resp.route is not None, "API route not None")

    api_detail = api.get_model("gpt-5.6-sol")
    fails += _check(api_detail is not None, "API get_model returns detail")
    if api_detail:
        fails += _check(api_detail.context_window == 1_050_000, "API detail: context correct")

    # 8. Invalid profile returns error
    error_resp = api.select(SelectRequest(provider="deepseek", profile="unknown"))
    fails += _check(error_resp.status == "error", "API invalid profile -> error")

    # 9. Adapter call counting
    counter = FakeProviderAdapter()
    for _ in range(3):
        counter.invoke(ProviderSelection())
    fails += _check(counter.calls == 3, "adapter counts 3 calls")

    # Summary
    total = 22
    passed = total - fails
    print(f"\n{'='*40}")
    print(f"Provider pipeline smoke: {passed}/{total} passed")
    if fails:
        print(f"FAILED — {fails} checks failed")
    else:
        print("ALL PASSED")
    return 2 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
