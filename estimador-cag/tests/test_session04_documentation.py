"""
Documentation tests for the Session 04 live plus branch.

These tests protect the class-defense documentation from drifting behind the
actual architecture.
"""

from pathlib import Path

README = Path("README.md")
DEFENSE_DOC = Path("docs/session04-live-plus-defense.md")


def test_readme_documents_current_live_plus_architecture():
    text = README.read_text(encoding="utf-8")

    required = [
        "Session 04 Live Plus",
        "Structured JSON output",
        "DeepSeek flash → DeepSeek pro → Kimi 2.5 backup → Kimi 2.6 backup_pro",
        "Exact Redis cache runs before semantic cache",
        "Semantic cache shadow mode",
        "requested_tier",
        "served_tier",
        "fallback_used",
        "semantic_cache_mode",
        "semantic_candidate_found",
    ]

    for item in required:
        assert item in text


def test_readme_no_longer_claims_structured_guardrails_or_semantic_cache_are_missing():
    text = README.read_text(encoding="utf-8")

    forbidden = [
        "Structured JSON output from the LLM.",
        "Guardrails.",
        "Semantic cache.",
        "Intentionally not included because the exercise reserves them for live session",
    ]

    for item in forbidden:
        assert item not in text


def test_class_defense_doc_exists_and_covers_production_hardening_topics():
    assert DEFENSE_DOC.exists()

    text = DEFENSE_DOC.read_text(encoding="utf-8")

    required = [
        "Provider fallback ladder",
        "Structured output contract",
        "Aggregate normalization",
        "Fallback observability",
        "Exact cache first",
        "Semantic cache shadow mode",
        "Guardrails",
        "Runtime proof",
        "Known limitations",
    ]

    for item in required:
        assert item in text
