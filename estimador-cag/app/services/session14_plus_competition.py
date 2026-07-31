"""Deterministic conservative/aggressive competition for Session 14 Plus."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass

from app.schemas.session14_plus_competition import (
    CompetitionComponent,
    EstimateCompetitionAssessment,
    EstimateCompetitionCandidate,
    EstimateCompetitionOutcome,
)
from app.schemas.v3_energy import ConstraintObservation
from app.services.v3_estimation_energy import (
    calculate_constraint_energy,
    candidate_fingerprint,
)

COMPETITION_POLICY_VERSION = "session14-plus-competition-1.0.0"


@dataclass(frozen=True)
class EstimateCompetitionPolicy:
    """Bounded arithmetic policy owned by Python, not by model agents."""

    aggressive_discount: float = 0.10
    conservative_buffer: float = 0.15
    material_divergence_threshold: float = 0.25
    maximum_conservative_weight: float = 0.70

    def __post_init__(self) -> None:
        if not 0 < self.aggressive_discount < 1:
            raise ValueError("aggressive_discount must be between zero and one")
        if not 0 < self.conservative_buffer < 1:
            raise ValueError("conservative_buffer must be between zero and one")
        if not 0 < self.material_divergence_threshold <= 1:
            raise ValueError(
                "material_divergence_threshold must be between zero and one"
            )
        if not 0.5 <= self.maximum_conservative_weight <= 0.75:
            raise ValueError(
                "maximum_conservative_weight must be between 0.5 and 0.75"
            )


def build_estimate_competition(
    component_estimates: Sequence[Mapping[str, object]],
    *,
    estimation_id: str,
    policy: EstimateCompetitionPolicy | None = None,
) -> EstimateCompetitionOutcome:
    """Create bounded candidates, synthesize safely, and calculate energy."""

    normalized_estimation_id = estimation_id.strip()
    if not normalized_estimation_id:
        raise ValueError("estimation_id must not be blank")
    if not component_estimates:
        raise ValueError("component_estimates must not be empty")

    active_policy = policy or EstimateCompetitionPolicy()
    baseline_components = [
        _baseline_component(item)
        for item in component_estimates
    ]
    aggressive_components = [
        _scaled_component(
            item,
            variant="aggressive",
            policy=active_policy,
        )
        for item in component_estimates
    ]
    conservative_components = [
        _scaled_component(
            item,
            variant="conservative",
            policy=active_policy,
        )
        for item in component_estimates
    ]
    average_confidence = round(
        sum(component.confidence for component in baseline_components)
        / len(baseline_components),
        4,
    )
    conservative_weight = round(
        min(
            active_policy.maximum_conservative_weight,
            0.5 + (1.0 - average_confidence) * 0.2,
        ),
        4,
    )
    synthesized_components = _synthesize_components(
        aggressive_components,
        conservative_components,
        conservative_weight=conservative_weight,
    )

    baseline = _candidate(
        estimation_id=normalized_estimation_id,
        variant="baseline",
        components=baseline_components,
        assumptions=["Retain deterministic estimate-generator output."],
    )
    aggressive = _candidate(
        estimation_id=normalized_estimation_id,
        variant="aggressive",
        components=aggressive_components,
        assumptions=[
            "Apply a bounded delivery-optimized discount without crossing known lower evidence bounds."
        ],
    )
    conservative = _candidate(
        estimation_id=normalized_estimation_id,
        variant="conservative",
        components=conservative_components,
        assumptions=[
            "Apply a bounded risk buffer and respect known upper evidence bounds."
        ],
    )
    synthesized = _candidate(
        estimation_id=normalized_estimation_id,
        variant="synthesized",
        components=synthesized_components,
        assumptions=[
            f"Weight conservative candidate at {conservative_weight:.4f} from evidence confidence."
        ],
    )

    divergence_ratio = _divergence_ratio(
        baseline=baseline,
        aggressive=aggressive,
        conservative=conservative,
    )
    missing_components = [
        component.component_id
        for component in baseline.components
        if component.hours is None
    ]
    material_divergence = (
        divergence_ratio is not None
        and divergence_ratio > active_policy.material_divergence_threshold
    )
    observations = [
        ConstraintObservation(
            observation_id=f"{normalized_estimation_id}:competition:evidence",
            code="competition_component_hours_complete",
            status="missing" if missing_components else "pass",
            penalty=0,
            hard_blocking=bool(missing_components),
            evidence_refs=_all_evidence_refs(baseline.components),
            affected_refs=missing_components,
            summary=(
                "One or more components have no authoritative hours."
                if missing_components
                else "All competing components have authoritative hours."
            ),
        ),
        ConstraintObservation(
            observation_id=f"{normalized_estimation_id}:competition:divergence",
            code="competition_material_divergence",
            status="conflict" if material_divergence else "pass",
            penalty=0,
            hard_blocking=material_divergence,
            evidence_refs=_all_evidence_refs(baseline.components),
            affected_refs=[
                aggressive.candidate_id,
                conservative.candidate_id,
            ],
            summary=(
                "Conservative and aggressive totals diverge beyond the allowed threshold."
                if material_divergence
                else "Candidate divergence is within the deterministic threshold."
            ),
        ),
        ConstraintObservation(
            observation_id=f"{normalized_estimation_id}:competition:confidence",
            code="competition_low_average_confidence",
            status="fail" if average_confidence < 0.60 else "pass",
            penalty=(
                int(round((0.60 - average_confidence) * 1_000))
                if average_confidence < 0.60
                else 0
            ),
            hard_blocking=False,
            evidence_refs=_all_evidence_refs(baseline.components),
            affected_refs=[baseline.candidate_id],
            summary=(
                "Average evidence confidence is below the preferred synthesis threshold."
                if average_confidence < 0.60
                else "Average evidence confidence supports bounded synthesis."
            ),
        ),
    ]
    energy = calculate_constraint_energy(
        candidate_id=synthesized.candidate_id,
        policy_version=COMPETITION_POLICY_VERSION,
        energy_before=0,
        observations=observations,
    )
    review_required = bool(
        energy.hard_violations
        or energy.missing_evidence
        or energy.conflicts
    )
    selected = baseline if review_required else synthesized
    reason_codes: list[str] = []
    if missing_components:
        reason_codes.append("missing_component_hours")
    if material_divergence:
        reason_codes.append("material_candidate_divergence")
    if average_confidence < 0.60:
        reason_codes.append("low_average_confidence")
    if not reason_codes:
        reason_codes.append("bounded_synthesis_accepted")

    assessment_payload = {
        "policy_version": COMPETITION_POLICY_VERSION,
        "baseline_candidate_id": baseline.candidate_id,
        "aggressive_candidate_id": aggressive.candidate_id,
        "conservative_candidate_id": conservative.candidate_id,
        "synthesized_candidate_id": synthesized.candidate_id,
        "selected_candidate_id": selected.candidate_id,
        "divergence_ratio": divergence_ratio,
        "material_divergence_threshold": active_policy.material_divergence_threshold,
        "average_confidence": average_confidence,
        "conservative_weight": conservative_weight,
        "disposition": "human_review" if review_required else "accept_synthesized",
        "review_required": review_required,
        "reason_codes": reason_codes,
        "energy_snapshot_id": energy.snapshot_id,
    }
    assessment_id = (
        "competition:"
        + candidate_fingerprint(assessment_payload)[:24]
    )
    assessment = EstimateCompetitionAssessment(
        assessment_id=assessment_id,
        policy_version=COMPETITION_POLICY_VERSION,
        baseline_candidate_id=baseline.candidate_id,
        aggressive_candidate_id=aggressive.candidate_id,
        conservative_candidate_id=conservative.candidate_id,
        synthesized_candidate_id=synthesized.candidate_id,
        selected_candidate_id=selected.candidate_id,
        divergence_ratio=divergence_ratio,
        material_divergence_threshold=(
            active_policy.material_divergence_threshold
        ),
        average_confidence=average_confidence,
        conservative_weight=conservative_weight,
        disposition=(
            "human_review" if review_required else "accept_synthesized"
        ),
        review_required=review_required,
        reason_codes=reason_codes,
        energy_snapshot=energy,
    )
    selected_component_estimates = _selected_component_estimates(
        component_estimates,
        selected,
        review_required=review_required,
        reason_codes=reason_codes,
    )
    return EstimateCompetitionOutcome(
        candidates=[baseline, aggressive, conservative, synthesized],
        assessment=assessment,
        selected_component_estimates=selected_component_estimates,
    )


def _baseline_component(item: Mapping[str, object]) -> CompetitionComponent:
    component_id = str(item.get("component_id", "")).strip()
    name = str(item.get("name", "")).strip()
    if not component_id or not name:
        raise ValueError("component estimates require component_id and name")
    hours = _optional_non_negative_float(item.get("hours"))
    confidence = _confidence(item.get("confidence"))
    return CompetitionComponent(
        component_id=component_id,
        name=name,
        hours=hours,
        confidence=confidence,
        evidence_refs=_evidence_refs(item),
    )


def _scaled_component(
    item: Mapping[str, object],
    *,
    variant: str,
    policy: EstimateCompetitionPolicy,
) -> CompetitionComponent:
    baseline = _baseline_component(item)
    if baseline.hours is None:
        return baseline

    lower = _optional_non_negative_float(item.get("source_range_low"))
    upper = _optional_non_negative_float(item.get("source_range_high"))
    if variant == "aggressive":
        discounted = baseline.hours * (1.0 - policy.aggressive_discount)
        floor = lower if lower is not None else 0.0
        hours = min(baseline.hours, max(floor, discounted))
    elif variant == "conservative":
        buffered = baseline.hours * (1.0 + policy.conservative_buffer)
        ceiling = upper if upper is not None else 0.0
        hours = max(baseline.hours, buffered, ceiling)
    else:
        raise ValueError(f"unsupported competition variant: {variant}")
    return baseline.model_copy(update={"hours": round(hours, 2)})


def _synthesize_components(
    aggressive: Sequence[CompetitionComponent],
    conservative: Sequence[CompetitionComponent],
    *,
    conservative_weight: float,
) -> list[CompetitionComponent]:
    conservative_by_id = {
        component.component_id: component
        for component in conservative
    }
    result: list[CompetitionComponent] = []
    for low in aggressive:
        high = conservative_by_id[low.component_id]
        if low.hours is None or high.hours is None:
            hours = None
        else:
            hours = round(
                low.hours * (1.0 - conservative_weight)
                + high.hours * conservative_weight,
                2,
            )
        result.append(low.model_copy(update={"hours": hours}))
    return result


def _candidate(
    *,
    estimation_id: str,
    variant: str,
    components: Sequence[CompetitionComponent],
    assumptions: list[str],
) -> EstimateCompetitionCandidate:
    total_hours = (
        None
        if any(component.hours is None for component in components)
        else round(sum(float(component.hours) for component in components), 2)
    )
    fingerprint_payload = {
        "estimation_id": estimation_id,
        "variant": variant,
        "policy_version": COMPETITION_POLICY_VERSION,
        "components": [
            component.model_dump(mode="json")
            for component in components
        ],
        "total_hours": total_hours,
        "assumptions": assumptions,
    }
    fingerprint = candidate_fingerprint(fingerprint_payload)
    return EstimateCompetitionCandidate(
        candidate_id=(
            f"candidate:{estimation_id}:{variant}:{fingerprint[:16]}"
        ),
        variant=variant,
        policy_version=COMPETITION_POLICY_VERSION,
        components=list(components),
        total_hours=total_hours,
        fingerprint=fingerprint,
        assumptions=assumptions,
    )


def _divergence_ratio(
    *,
    baseline: EstimateCompetitionCandidate,
    aggressive: EstimateCompetitionCandidate,
    conservative: EstimateCompetitionCandidate,
) -> float | None:
    if (
        baseline.total_hours is None
        or aggressive.total_hours is None
        or conservative.total_hours is None
        or baseline.total_hours <= 0
    ):
        return None
    return round(
        (conservative.total_hours - aggressive.total_hours)
        / baseline.total_hours,
        4,
    )


def _selected_component_estimates(
    original: Sequence[Mapping[str, object]],
    selected: EstimateCompetitionCandidate,
    *,
    review_required: bool,
    reason_codes: Sequence[str],
) -> list[dict[str, object]]:
    selected_by_id = {
        component.component_id: component
        for component in selected.components
    }
    result: list[dict[str, object]] = []
    for raw_item in original:
        item = deepcopy(dict(raw_item))
        component_id = str(item.get("component_id", ""))
        selected_component = selected_by_id[component_id]
        item["hours"] = selected_component.hours
        item["derivation_method"] = (
            "session14_plus_competition_synthesis"
            if selected.variant == "synthesized"
            else str(item.get("derivation_method", "deterministic_baseline"))
        )
        existing_reasons = item.get("review_reasons", [])
        normalized_reasons = (
            [str(value) for value in existing_reasons]
            if isinstance(existing_reasons, list)
            else []
        )
        if review_required:
            normalized_reasons.extend(reason_codes)
        item["review_reasons"] = list(dict.fromkeys(normalized_reasons))
        result.append(item)
    return result


def _evidence_refs(item: Mapping[str, object]) -> list[str]:
    refs: list[str] = []
    for key, prefix in (
        ("reference_budget_ids", "budget"),
        ("reference_component_ids", "component"),
    ):
        values = item.get(key)
        if isinstance(values, list):
            refs.extend(
                f"{prefix}:{value}"
                for value in values
                if isinstance(value, str) and value
            )
    return list(dict.fromkeys(refs))


def _all_evidence_refs(
    components: Sequence[CompetitionComponent],
) -> list[str]:
    return list(
        dict.fromkeys(
            ref
            for component in components
            for ref in component.evidence_refs
        )
    )


def _confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("component confidence must be numeric")
    confidence = float(value)
    if not 0 <= confidence <= 1:
        raise ValueError("component confidence must be between zero and one")
    return confidence


def _optional_non_negative_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("component hours and ranges must be numeric or null")
    normalized = float(value)
    if normalized < 0:
        raise ValueError("component hours and ranges must be non-negative")
    return normalized
