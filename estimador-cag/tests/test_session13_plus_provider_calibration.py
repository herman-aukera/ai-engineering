"""Provider calibration smoke tests for Session 13 Plus.

These tests require valid API keys (available in GitHub CI).
When keys are absent, tests are skipped gracefully.
"""

from __future__ import annotations

import os

import pytest


def _has_deepseek_key() -> bool:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    return bool(key) and key not in ("dummy", "fake")


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
