"""Provider-neutral semantic classifier port and deterministic fake for Session 13 V3."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Protocol, runtime_checkable

from app.schemas.v3_classifier import (
    ClassifierArbitration,
    SemanticAssessment,
    SemanticSignals,
)
from app.schemas.v3_routing import ComplexityAssessment, ComplexityLevel

FAKE_CLASSIFIER_VERSION = "session13-v3-semantic-fake-1.0.0"

_SECURITY_RISK_INDICATORS = frozenset({"security", "compliance"})
_COMPLEXITY_ORDER: dict[ComplexityLevel, int] = {
    "C0": 0,
    "C1": 1,
    "C2": 2,
    "C3": 3,
    "C4": 4,
    "C5": 5,
}
_SESSION_POLICY_RE = re.compile(r"^(session\d+)")


@runtime_checkable
class SemanticClassifier(Protocol):
    """Provider-neutral semantic-classification boundary.

    Concrete implementations may call an LLM, but the protocol itself carries
    no provider, model, or API details — those belong in the adapter layer.
    """

    def classify(self, transcript: str) -> SemanticAssessment:
        """Produce one checkpoint-safe semantic assessment from a transcript."""
        ...


class FakeSemanticClassifier:
    """Deterministic fake that returns a configurable assessment and records calls.

    When no ``default_assessment`` is supplied the fake returns a conservative
    C1 for every input, matching the invariant that deterministic CI must never
    depend on a live model.
    """

    def __init__(
        self,
        default_assessment: SemanticAssessment | None = None,
    ) -> None:
        self._default = deepcopy(default_assessment) if default_assessment is not None else None
        self.calls: list[str] = []

    def classify(self, transcript: str) -> SemanticAssessment:
        """Return the configured assessment or a safe C1 default."""
        self.calls.append(transcript)
        if self._default is not None:
            return deepcopy(self._default)
        return SemanticAssessment(
            level="C1",
            confidence=0.8,
            signals=SemanticSignals(
                domain_category="unknown",
                primary_modality="text",
                transcript_quality="well_structured",
            ),
            rationale="Deterministic fake classifier — no semantic analysis performed.",
            classifier_version=FAKE_CLASSIFIER_VERSION,
        )


def _policy_prefix(version: str) -> str | None:
    """Extract the session policy prefix, e.g. 'session13' from a classifier version."""
    match = _SESSION_POLICY_RE.match(version)
    return match.group(1) if match else None


def _has_security_risk(signals: SemanticSignals) -> bool:
    return bool(_SECURITY_RISK_INDICATORS.intersection(signals.risk_indicators))


def arbitrate_classification(
    *,
    deterministic: ComplexityAssessment,
    semantic: SemanticAssessment,
) -> ClassifierArbitration:
    """Resolve the authoritative complexity level from two independent assessments.

    Rules (applied in order):

    1. **Policy-prefix guard** — if both classifier versions carry a session
       prefix and they differ, raise :exc:`ValueError`.
    2. **C5 lock** — a deterministic C5 is never downgraded.
    3. **Security flag** — semantic risk indicators ``security`` or
       ``compliance`` force ``human_review_required``.
    4. **Level comparison** — the higher level wins; ties resolve as
       ``consensus`` with the deterministic level preserved.
    """

    det_prefix = _policy_prefix(deterministic.classifier_version)
    sem_prefix = _policy_prefix(semantic.classifier_version)
    if det_prefix is not None and sem_prefix is not None and det_prefix != sem_prefix:
        raise ValueError(
            f"Classifier policy-prefix mismatch: "
            f"deterministic={det_prefix}, semantic={sem_prefix}"
        )

    det_rank = _COMPLEXITY_ORDER[deterministic.level]
    sem_rank = _COMPLEXITY_ORDER[semantic.level]

    security_flagged = _has_security_risk(semantic.signals)

    # C5 lock — deterministic C5 is never downgraded.
    if deterministic.level == "C5":
        return ClassifierArbitration(
            arbitrated_level="C5",
            resolution="deterministic_override",
            resolution_reason=(
                "Deterministic C5 assessment is preserved; "
                "semantic classifier assessed " + semantic.level + "."
            ),
            human_review_required=True,
            deterministic_assessment_ref=deterministic.classifier_version,
            semantic_assessment_ref=semantic.classifier_version,
        )

    if det_rank == sem_rank:
        return ClassifierArbitration(
            arbitrated_level=deterministic.level,
            resolution="consensus",
            resolution_reason=(
                f"Both classifiers agree on {deterministic.level}."
            ),
            human_review_required=security_flagged or deterministic.human_review_required,
            deterministic_assessment_ref=deterministic.classifier_version,
            semantic_assessment_ref=semantic.classifier_version,
        )

    if sem_rank > det_rank:
        return ClassifierArbitration(
            arbitrated_level=semantic.level,
            resolution="semantic_escalation",
            resolution_reason=(
                f"Semantic classifier assessed {semantic.level} "
                f"(above deterministic {deterministic.level}): "
                + (semantic.rationale[:200] if len(semantic.rationale) > 200 else semantic.rationale)
            ),
            human_review_required=security_flagged or semantic.level == "C5",
            deterministic_assessment_ref=deterministic.classifier_version,
            semantic_assessment_ref=semantic.classifier_version,
        )

    return ClassifierArbitration(
        arbitrated_level=deterministic.level,
        resolution="deterministic_override",
        resolution_reason=(
            f"Deterministic structural evidence places complexity at "
            f"{deterministic.level} (above semantic {semantic.level})."
        ),
        human_review_required=security_flagged or deterministic.human_review_required,
        deterministic_assessment_ref=deterministic.classifier_version,
        semantic_assessment_ref=semantic.classifier_version,
    )
