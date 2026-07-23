"""Deterministic reliability analyst for Session 13 Plus V6.

Scores component estimates on grounding quality, reference count,
dispersion, and confidence.  Returns a :class:`ReliabilityReport`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.schemas.v6_reliability import ComponentReliability, ReliabilityReport


def _score_component(estimate: Mapping[str, object]) -> ComponentReliability:
    """Score one component estimate on reliability dimensions."""
    component_id = str(estimate.get("component_id", "unknown"))
    grounding = str(estimate.get("grounding_status", "unknown"))
    confidence = float(estimate.get("confidence", 0))
    refs = estimate.get("reference_budget_ids", [])
    ref_count = len(refs) if isinstance(refs, list) else 0
    dispersion = estimate.get("dispersion")
    disp_val = float(dispersion) if isinstance(dispersion, (int, float)) and dispersion is not None else None

    flags: list[str] = []
    score = confidence

    if grounding == "no_data":
        flags.append("no_evidence")
        score = 0.0
    elif grounding == "conflict":
        flags.append("conflicting_evidence")
        score = max(0.0, min(0.3, score))
    elif grounding == "low_confidence":
        flags.append("low_confidence")
        score = max(0.0, min(0.5, score))

    if ref_count < 2:
        flags.append("single_reference")
        score = max(0.0, score - 0.15)

    if disp_val is not None and disp_val > 0.5:
        flags.append("high_dispersion")
        score = max(0.0, score - 0.15)

    return ComponentReliability(
        component_id=component_id,
        reliability_score=round(max(0.0, min(1.0, score)), 2),
        reference_count=ref_count,
        dispersion=disp_val,
        grounding_status=grounding,
        flags=flags,
    )


def analyse_reliability(
    component_estimates: Sequence[Mapping[str, object]],
) -> ReliabilityReport:
    """Produce a reliability report over component estimates.

    Returns a safe default (score 0, review required) when the list is empty.
    """
    if not component_estimates:
        return ReliabilityReport(
            components=[],
            overall_score=0.0,
            requires_human_review=True,
            summary="No component estimates to analyse.",
        )

    components = [_score_component(e) for e in component_estimates]
    total = sum(c.reliability_score for c in components)
    overall = round(total / len(components), 2)

    requires_review = (
        overall < 0.6
        or any(c.reliability_score < 0.4 for c in components)
        or any("no_evidence" in c.flags for c in components)
        or any("conflicting_evidence" in c.flags for c in components)
    )

    return ReliabilityReport(
        components=components,
        overall_score=overall,
        requires_human_review=requires_review,
        summary=(
            f"Analysed {len(components)} components. "
            f"Overall reliability: {overall:.0%}. "
            f"Flags: {sum(len(c.flags) for c in components)} total."
        ),
    )
