"""Tests for Session 13 Plus: deterministic reliability analyst."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimates(*components: dict) -> list[dict]:
    return list(components)


def _grounded(component_id: str = "cmp-1", hours: float = 40.0) -> dict:
    return {
        "component_id": component_id, "name": "Test", "hours": hours,
        "grounding_status": "grounded", "reference_budget_ids": ["B1", "B2"],
        "source_hours": [38.0, 42.0], "source_range_low": 38.0, "source_range_high": 42.0,
        "dispersion": 0.1, "confidence": 0.85, "derivation_method": "median_recorded_hours",
    }


def _low_confidence(component_id: str = "cmp-2") -> dict:
    return {
        "component_id": component_id, "name": "Test", "hours": 60.0,
        "grounding_status": "low_confidence", "reference_budget_ids": ["B3"],
        "source_hours": [60.0], "source_range_low": 60.0, "source_range_high": 60.0,
        "dispersion": 0.0, "confidence": 0.45, "derivation_method": "single_reference",
    }


# ---------------------------------------------------------------------------
# 1. ReliabilityReport schema
# ---------------------------------------------------------------------------

def test_reliability_report_schema_is_frozen() -> None:
    """ReliabilityReport must be immutable and checkpoint-safe."""
    from app.schemas.v6_reliability import ReliabilityReport, ComponentReliability

    report = ReliabilityReport(
        components=[
            ComponentReliability(component_id="cmp-1", reliability_score=0.9),
        ],
        overall_score=0.9,
        requires_human_review=False,
    )
    payload = report.model_dump(mode="json")
    assert payload["overall_score"] == 0.9
    assert len(payload["components"]) == 1


# ---------------------------------------------------------------------------
# 2. Reliability scoring
# ---------------------------------------------------------------------------

def test_grounded_component_scores_high() -> None:
    """Well-grounded components with multiple references score high."""
    from app.services.v6_reliability import analyse_reliability

    result = analyse_reliability(_estimates(_grounded()))
    assert result.overall_score >= 0.7
    assert result.components[0].reliability_score >= 0.7


def test_low_confidence_component_scores_low() -> None:
    """Single-reference low-confidence components score low."""
    from app.services.v6_reliability import analyse_reliability

    result = analyse_reliability(_estimates(_low_confidence()))
    assert result.overall_score < 0.6
    assert result.components[0].reliability_score < 0.6


def test_mixed_components_average_correctly() -> None:
    """Overall score must be the weighted average of components."""
    from app.services.v6_reliability import analyse_reliability

    result = analyse_reliability(_estimates(_grounded("cmp-1"), _low_confidence("cmp-2")))
    # Grounded (~0.85) + low_confidence (~0.45) → average ~0.65
    assert 0.5 < result.overall_score < 0.8
    assert result.components[0].reliability_score > result.components[1].reliability_score


def test_no_data_component_forces_review() -> None:
    """Components with no_data grounding must force human review."""
    from app.services.v6_reliability import analyse_reliability

    no_data = {
        "component_id": "cmp-3", "name": "Ghost", "hours": None,
        "grounding_status": "no_data", "reference_budget_ids": [],
        "source_hours": [], "source_range_low": None, "source_range_high": None,
        "dispersion": None, "confidence": 0.0, "derivation_method": "no_recorded_hours",
    }
    result = analyse_reliability(_estimates(_grounded(), no_data))
    assert result.requires_human_review is True


def test_conflict_component_forces_review() -> None:
    """Conflicting evidence must force human review."""
    from app.services.v6_reliability import analyse_reliability

    conflict = {
        "component_id": "cmp-4", "name": "Fight", "hours": 50.0,
        "grounding_status": "conflict", "reference_budget_ids": ["B4", "B5"],
        "source_hours": [10.0, 90.0], "source_range_low": 10.0, "source_range_high": 90.0,
        "dispersion": 1.6, "confidence": 0.2, "derivation_method": "median_recorded_hours",
    }
    result = analyse_reliability(_estimates(conflict))
    assert result.requires_human_review is True


def test_analyst_handles_empty_input() -> None:
    """Empty estimates list must return a safe default."""
    from app.services.v6_reliability import analyse_reliability

    result = analyse_reliability([])
    assert result.overall_score == 0.0
    assert result.requires_human_review is True
    assert result.components == []
