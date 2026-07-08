"""
Manual Session 12 live-provider smoke runner.

This script is intentionally manual-only. Normal CI should test this file with
dry-run/fake paths only. Real provider calls require the explicit --live flag.
"""

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.generation.agentic.provider_adapters import (  # noqa: E402
    AgentPlannedStep,
    OpenAICompatibleProviderAdapter,
    ProviderAdapterRequest,
)

ProviderName = str
TierName = str


DEFAULT_MODEL_MATRIX: dict[ProviderName, dict[TierName, str]] = {
    "deepseek": {
        "cheap": "deepseek-v4-flash",
        "final": "deepseek-v4-pro",
    },
    "kimi": {
        "cheap": "kimi-k2.6",
        "final": "kimi-k2.7-code",
    },
    "openai": {
        "cheap": "gpt-5.4-mini",
        "final": "gpt-5.5",
    },
}

DEFAULT_TEMPERATURE_MATRIX: dict[ProviderName, dict[TierName, float]] = {
    "deepseek": {
        "cheap": 0.0,
        "final": 0.0,
    },
    "kimi": {
        "cheap": 1.0,
        "final": 1.0,
    },
    "openai": {
        "cheap": 0.0,
        "final": 0.0,
    },
}


MODEL_ENV_MATRIX: dict[ProviderName, dict[TierName, str]] = {
    "deepseek": {
        "cheap": "DEEPSEEK_MODEL_CHEAP",
        "final": "DEEPSEEK_MODEL_FINAL",
    },
    "kimi": {
        "cheap": "KIMI_MODEL_CHEAP",
        "final": "KIMI_MODEL_FINAL",
    },
    "openai": {
        "cheap": "OPENAI_MODEL_CHEAP",
        "final": "OPENAI_MODEL_FINAL",
    },
}

DEFAULT_BASE_URLS: dict[ProviderName, str | None] = {
    "deepseek": "https://api.deepseek.com/v1",
    "kimi": "https://api.moonshot.ai/v1",
    "openai": None,
}

BASE_URL_ENV_NAMES: dict[ProviderName, str] = {
    "deepseek": "DEEPSEEK_BASE_URL",
    "kimi": "KIMI_BASE_URL",
    "openai": "OPENAI_BASE_URL",
}

API_KEY_ENV_NAMES: dict[ProviderName, tuple[str, ...]] = {
    "deepseek": ("DEEPSEEK_API_KEY",),
    "kimi": ("KIMI_API_KEY", "MOONSHOT_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
}


@dataclass(frozen=True)
class ProviderSpec:
    """Resolved provider configuration for one smoke run."""

    provider: ProviderName
    tier: TierName
    model: str
    base_url: str | None
    api_key_env_names: tuple[str, ...]
    api_key: str | None = None
    temperature: float = 0.0


def _first_env_value(
    env: Mapping[str, str],
    names: Sequence[str],
) -> str | None:
    for name in names:
        value = env.get(name)
        if value:
            return value
    return None


def _selected_providers(provider: ProviderName) -> list[ProviderName]:
    if provider == "all":
        return ["deepseek", "kimi", "openai"]
    return [provider]


def resolve_provider_specs(
    *,
    provider: ProviderName,
    tier: TierName,
    model_override: str | None,
    env: Mapping[str, str],
    temperature_override: float | None = None,
) -> list[ProviderSpec]:
    """Resolve provider/model/base-url/key matrix without printing secrets."""

    providers = _selected_providers(provider)

    if model_override and len(providers) > 1:
        raise ValueError("--model can only be used with a single provider")

    specs: list[ProviderSpec] = []
    for provider_name in providers:
        model_env_name = MODEL_ENV_MATRIX[provider_name][tier]
        model = (
            model_override
            or env.get(model_env_name)
            or DEFAULT_MODEL_MATRIX[provider_name][tier]
        )

        base_url_env_name = BASE_URL_ENV_NAMES[provider_name]
        base_url = env.get(base_url_env_name) or DEFAULT_BASE_URLS[provider_name]

        temperature = temperature_override
        if temperature is None:
            temperature = DEFAULT_TEMPERATURE_MATRIX[provider_name][tier]

        api_key_env_names = API_KEY_ENV_NAMES[provider_name]
        api_key = _first_env_value(env, api_key_env_names)

        specs.append(
            ProviderSpec(
                provider=provider_name,
                tier=tier,
                model=model,
                base_url=base_url,
                api_key_env_names=api_key_env_names,
                api_key=api_key,
                temperature=temperature,
            )
        )

    return specs


def safe_spec_summary(spec: ProviderSpec) -> dict[str, object]:
    """Return a printable provider summary without secrets."""

    return {
        "provider": spec.provider,
        "tier": spec.tier,
        "model": spec.model,
        "base_url": spec.base_url,
        "temperature": spec.temperature,
        "api_key_present": bool(spec.api_key),
        "api_key_env_names": list(spec.api_key_env_names),
    }


def build_live_smoke_artifact(
    *,
    spec: ProviderSpec,
    steps: list[AgentPlannedStep],
    transcript: str,
) -> dict[str, object]:
    """Build a secret-free live smoke artifact."""

    transcript_digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()

    return {
        "schema_version": "session12.live_provider_smoke.v1",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "provider": spec.provider,
        "tier": spec.tier,
        "model": spec.model,
        "base_url": spec.base_url,
        "temperature": spec.temperature,
        "transcript_sha256": transcript_digest,
        "step_count": len(steps),
        "steps": [step.model_dump() for step in steps],
    }


def _build_openai_compatible_client(spec: ProviderSpec):
    """Build an OpenAI-compatible client only for explicit live calls."""

    from openai import OpenAI

    if not spec.api_key:
        env_names = ", ".join(spec.api_key_env_names)
        raise RuntimeError(f"Missing API key. Configure one of: {env_names}")

    if spec.base_url:
        return OpenAI(api_key=spec.api_key, base_url=spec.base_url)

    return OpenAI(api_key=spec.api_key)


def run_live_provider_smoke(
    *,
    spec: ProviderSpec,
    transcript: str,
    output_dir: Path,
) -> Path:
    """Execute one explicit live provider planning smoke run."""

    client = _build_openai_compatible_client(spec)
    adapter = OpenAICompatibleProviderAdapter(
        client=client,
        model=spec.model,
        provider=spec.provider,
        temperature=spec.temperature,
    )

    steps = adapter.plan(
        ProviderAdapterRequest(
            transcript=transcript,
            provider=spec.provider,
            model=spec.model,
        )
    )

    artifact = build_live_smoke_artifact(
        spec=spec,
        steps=steps,
        transcript=transcript,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{spec.tier}_{spec.provider}_plan.json"
    output_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manual Session 12 live-provider smoke runner.",
    )
    parser.add_argument(
        "--provider",
        choices=["deepseek", "kimi", "openai", "all"],
        required=True,
    )
    parser.add_argument(
        "--tier",
        choices=["cheap", "final"],
        required=True,
    )
    parser.add_argument(
        "--model",
        help="Override model for a single selected provider.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Override temperature for selected provider runs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved matrix without making live calls.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually call provider APIs. Required for external calls.",
    )
    parser.add_argument(
        "--transcript-file",
        default="evals/session12_agentic/sample_transcript_complex.txt",
    )
    parser.add_argument(
        "--output-dir",
        default="evals/session12_agentic/live_smoke",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    resolved_env = os.environ if env is None else env

    try:
        specs = resolve_provider_specs(
            provider=args.provider,
            tier=args.tier,
            model_override=args.model,
            env=resolved_env,
            temperature_override=args.temperature,
        )
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 2

    print("Resolved provider matrix:")
    for spec in specs:
        print(json.dumps(safe_spec_summary(spec), sort_keys=True))

    if not args.live:
        print("No live calls executed.")
        return 0

    transcript_path = Path(args.transcript_file)
    transcript = transcript_path.read_text(encoding="utf-8")
    output_dir = Path(args.output_dir)

    exit_code = 0
    for spec in specs:
        try:
            output_path = run_live_provider_smoke(
                spec=spec,
                transcript=transcript,
                output_dir=output_dir,
            )
        except Exception as exc:
            print(f"{spec.provider}: failed: {exc}")
            exit_code = 2
            continue

        print(f"{spec.provider}: wrote {output_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
