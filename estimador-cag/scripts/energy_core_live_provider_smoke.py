"""Live provider smoke test — uses real API keys when available in CI secrets.

Skips gracefully when keys are test placeholders or missing.
Records served-model evidence with exact provider, model, effort, tokens, latency, cost.
Safe: single short message, low max_tokens, timeout per call.
"""

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from energy_core.live_adapter import (  # noqa: E402
    DeepSeekAdapter,
    KimiCodeAdapter,
    LiveAdapterConfig,
    OpenAIAdapter,
)
from energy_core.provider_registry import (  # noqa: E402
    CapabilityRegistry,
    ProviderSelection,
)


def _is_real_key(value: str | None) -> bool:
    """Return True if the value looks like a real API key, not a test placeholder."""
    if value is None:
        return False
    return len(value) > 10 and value != "test"


def _check(condition: bool, label: str) -> int:
    if not condition:
        print(f"  FAIL: {label}")
        return 1
    print(f"  PASS: {label}")
    return 0


def _test_provider(
    name: str,
    adapter_class: type,
    env_var: str,
    provider: str,
    profile: str,
    registry: CapabilityRegistry,
) -> int:
    """Test one live provider. Returns 0 if skipped, 1+ on failure."""
    fails = 0
    key = os.environ.get(env_var, "")

    if not _is_real_key(key):
        print(f"\n  SKIP {name}: {env_var} is a test placeholder or missing")
        return 0

    print(f"\n  TEST {name} (live, {provider}/{profile}):")
    config = LiveAdapterConfig(
        enabled=True,
        provider=provider,
        api_key_env_var=env_var,
        registry=registry,
    )
    adapter = adapter_class(config)
    selection = ProviderSelection(
        provider=provider,
        profile=profile,
        expected_input_tokens=50,
        expected_output_tokens=50,
        max_cost_usd="0.50",
        max_latency_ms=30_000,
    )

    result = adapter.invoke(selection, messages=[{"role": "user", "content": "Say hello in one word."}])

    fails += _check(result.execution_performed, "execution_performed=True")
    fails += _check(result.served_model_id != "", f"served_model_id={result.served_model_id}")
    fails += _check(result.attempts[0].status == "success", f"status={result.attempts[0].status}")
    fails += _check(result.tokens.input_tokens > 0, f"input_tokens={result.tokens.input_tokens}")
    fails += _check(result.tokens.output_tokens > 0, f"output_tokens={result.tokens.output_tokens}")
    fails += _check(result.latency_ms > 0, f"latency={result.latency_ms}ms")
    fails += _check(result.cost_usd >= 0, f"cost=${result.cost_usd}")
    fails += _check(result.circuit_state == "closed", "circuit=closed")
    fails += _check(result.safe_provider_request_ref != "", "has request ref")

    if result.attempts and result.attempts[0].status == "failed":
        err = result.attempts[0].error_message or "unknown"
        print(f"  DIAG: attempt error: {err[:200]}")

    return fails


def main() -> int:
    registry = CapabilityRegistry()
    fails = 0

    print("Live Provider Smoke Test")
    print("=" * 50)
    print(f"DEEPSEEK_API_KEY present: {_is_real_key(os.environ.get('DEEPSEEK_API_KEY', ''))}")
    print(f"KIMI_API_KEY present:     {_is_real_key(os.environ.get('KIMI_API_KEY', ''))}")
    print(f"OPENAI_API_KEY present:   {_is_real_key(os.environ.get('OPENAI_API_KEY', ''))}")

    fails += _test_provider("DeepSeek", DeepSeekAdapter, "DEEPSEEK_API_KEY", "deepseek", "medium", registry)
    fails += _test_provider("Kimi Code", KimiCodeAdapter, "KIMI_API_KEY", "kimi", "max", registry)
    fails += _test_provider("OpenAI", OpenAIAdapter, "OPENAI_API_KEY", "openai", "medium", registry)

    tested = sum(1 for v in ["DEEPSEEK_API_KEY", "KIMI_API_KEY", "OPENAI_API_KEY"]
                 if _is_real_key(os.environ.get(v, "")))

    print(f"\n{'=' * 50}")
    if tested == 0:
        print("All providers skipped — no real API keys available (expected in local/dev)")
        return 0
    if fails == 0:
        print(f"Live smoke: ALL PASSED ({tested} providers tested)")
        return 0
    print(f"Live smoke: {fails} FAILURES across {tested} providers")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
