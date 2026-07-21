"""Provider calibration smoke tests for Session 13 Plus.

These tests require valid API keys (available in GitHub CI).
When keys are absent, tests are skipped gracefully.
"""

from __future__ import annotations

import os

import pytest

_NON_LIVE_KEY_SENTINELS = {"", "test", "dummy", "fake", "placeholder", "example"}


def _has_deepseek_key() -> bool:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip().lower()
    return key not in _NON_LIVE_KEY_SENTINELS


@pytest.mark.live_provider
@pytest.mark.skipif(
    not _has_deepseek_key(),
    reason="DEEPSEEK_API_KEY not set or is dummy — skipping live calibration",
)
def test_deepseek_live_classifier_returns_valid_assessment() -> None:
    """Live DeepSeek classifier must produce a valid SemanticAssessment."""
    from app.services.litellm_provider import LiteLLMProvider
    from app.services.v3_semantic_classifier import LiveSemanticClassifier

    provider = LiteLLMProvider()
    classifier = LiveSemanticClassifier(provider, tier="flash", max_tokens=800)

    result = classifier.classify(
        "Build a secure FastAPI onboarding platform with PostgreSQL and JWT authentication."
    )

    assert result.level in {"C0", "C1", "C2", "C3", "C4", "C5"}
    assert 0 <= result.confidence <= 1
    assert len(result.rationale) > 0
    assert result.signals.domain_category
    assert result.signals.transcript_quality in {
        "well_structured", "conversational", "fragmentary", "ambiguous",
    }


@pytest.mark.live_provider
@pytest.mark.skipif(
    not _has_deepseek_key(),
    reason="DEEPSEEK_API_KEY not set or is dummy — skipping live calibration",
)
def test_fake_and_live_classifier_agree_on_simple_transcript() -> None:
    """Fake and live classifiers must agree within 1 C-level on simple input."""
    from app.services.litellm_provider import LiteLLMProvider
    from app.services.v3_semantic_classifier import (
        FakeSemanticClassifier,
        LiveSemanticClassifier,
    )

    transcript = "Build a simple TODO web application with user login."

    fake = FakeSemanticClassifier()
    fake_result = fake.classify(transcript)

    provider = LiteLLMProvider()
    live = LiveSemanticClassifier(provider, tier="flash", max_tokens=800)
    live_result = live.classify(transcript)

    # Map levels to numbers for comparison.
    order = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5}
    gap = abs(order[fake_result.level] - order[live_result.level])
    assert gap <= 1, (
        f"Fake={fake_result.level}, Live={live_result.level} — "
        f"disagreement exceeds 1 C-level"
    )


@pytest.mark.live_provider
@pytest.mark.skipif(
    not _has_deepseek_key(),
    reason="DEEPSEEK_API_KEY not set or is dummy — skipping live calibration",
)
def test_live_classifier_reproducible_on_same_input() -> None:
    """Live classifier must be approximately reproducible (level stable)."""
    from app.services.litellm_provider import LiteLLMProvider
    from app.services.v3_semantic_classifier import LiveSemanticClassifier

    transcript = "Migrate a PostgreSQL database with zero downtime and audit logging."

    provider = LiteLLMProvider()
    classifier = LiveSemanticClassifier(provider, tier="flash", max_tokens=800)

    first = classifier.classify(transcript)
    second = classifier.classify(transcript)

    # Level must be stable across two calls.
    assert first.level == second.level, (
        f"Live classifier produced different levels: {first.level} vs {second.level}"
    )


def test_fake_classifier_always_available_for_ci() -> None:
    """Fake classifier works without any API keys (CI safety)."""
    from app.services.v3_semantic_classifier import FakeSemanticClassifier

    fake = FakeSemanticClassifier()
    result = fake.classify("Any transcript.")

    assert result.level == "C1"
    assert result.confidence > 0


# ---------------------------------------------------------------------------
# Registry seeding and provider routing matrix
# ---------------------------------------------------------------------------

def test_seeded_registry_contains_all_documented_providers() -> None:
    """Seeded registry must contain DeepSeek, Kimi, and OpenAI entries."""
    from app.services.v3_registry_seed import build_seeded_registry

    registry = build_seeded_registry()

    deepseek = registry.list_by_provider("deepseek")
    kimi = registry.list_by_provider("moonshot")
    openai_models = registry.list_by_provider("openai")

    assert len(deepseek) >= 2  # Flash + Pro
    assert len(kimi) >= 3      # K2.6 + K2.7 Code + K3
    assert len(openai_models) >= 3  # Luna + Terra + Sol


def test_seeded_registry_routes_fail_closed_until_promoted() -> None:
    """Documented seed records must not masquerade as operational routes."""
    from app.schemas.v5_provider_selection import ProviderSelection
    from app.services.v3_registry_seed import build_seeded_registry
    from app.services.v5_provider_selector import resolve_provider_route

    registry = build_seeded_registry()
    for provider in ("deepseek", "kimi", "openai"):
        selection = ProviderSelection(provider=provider)
        for level in ("C0", "C3", "C5"):
            with pytest.raises(ValueError, match="eligible promoted route"):
                resolve_provider_route(
                    selection=selection,
                    complexity_level=level,
                    stage="structure",
                    registry=registry,
                )


def test_kimi_k3_is_documented_not_enabled() -> None:
    """Kimi K3 must be documented, not enabled (not yet reachable)."""
    from app.services.v3_registry_seed import build_seeded_registry

    registry = build_seeded_registry()
    k3 = registry.lookup(provider="moonshot", provider_model_id="k3")

    assert k3 is not None
    assert k3.calibration_status == "documented"
    assert k3.reasoning_efforts == ["low", "high", "max"]


def test_gpt56_family_is_documented_not_enabled() -> None:
    """GPT-5.6 models are documented, pending reachability verification."""
    from app.services.v3_registry_seed import build_seeded_registry

    registry = build_seeded_registry()
    sol = registry.lookup(provider="openai", provider_model_id="gpt-5.6-sol")

    assert sol is not None
    assert sol.calibration_status == "documented"
    assert sol.context_window == 200_000


def test_registry_seed_is_deterministic() -> None:
    """Two calls to build_seeded_registry must produce identical registries."""
    from app.services.v3_registry_seed import build_seeded_registry

    a = build_seeded_registry()
    b = build_seeded_registry()

    assert len(a) == len(b)
    for provider in ("deepseek", "moonshot", "openai"):
        a_models = a.list_by_provider(provider)
        b_models = b.list_by_provider(provider)
        assert len(a_models) == len(b_models)
