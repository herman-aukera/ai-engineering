"""Quality evaluation framework for Energy Aware Chat.

Milestone 19: defines a fixed benchmark corpus, evaluation rubric across
multiple dimensions, and a measurement-only comparison framework. No
provider quality claims are made without controlled evaluation evidence.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Evaluation dimensions ───────────────────────────────────────────────

RubricDimension = Literal[
    "constraint_satisfaction",
    "source_grounding",
    "repair_effectiveness",
    "answer_usefulness",
    "latency_ms",
    "cost_usd",
    "failure_rate",
    "context_retention",
    "human_preference",
]


class DimensionScore(BaseModel):
    """Score for one evaluation dimension, with supporting evidence."""

    dimension: RubricDimension
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: str = ""
    notes: str = ""


class QualityRubric(BaseModel):
    """Weighted multi-dimensional evaluation rubric.

    Weights sum to 1.0. Every dimension must have a documented rationale.
    Scores are measurements, not quality claims — the rubric provides
    the scoring framework, not the interpretation.
    """

    rubric_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    dimensions: list[DimensionScore] = Field(default_factory=list)
    claim_status: str = "measurement_only_no_quality_claim"


DEFAULT_RUBRIC = QualityRubric(
    rubric_id="eachat-quality-v1",
    version="1.0.0",
    dimensions=[
        DimensionScore(
            dimension="constraint_satisfaction", score=0.0, weight=0.25,
            evidence="Deterministic critics measure hard/soft constraint violations.",
        ),
        DimensionScore(
            dimension="source_grounding", score=0.0, weight=0.15,
            evidence="Evidence references are checked against known sources.",
        ),
        DimensionScore(
            dimension="repair_effectiveness", score=0.0, weight=0.15,
            evidence="Repair delta measures energy reduction after repair.",
        ),
        DimensionScore(
            dimension="answer_usefulness", score=0.0, weight=0.20,
            evidence="Structural completeness: Decision, Tradeoffs, Next action.",
        ),
        DimensionScore(
            dimension="latency_ms", score=0.0, weight=0.10,
            evidence="Wall-clock latency from provider metrics.",
        ),
        DimensionScore(
            dimension="cost_usd", score=0.0, weight=0.05,
            evidence="Provider call cost in USD.",
        ),
        DimensionScore(
            dimension="failure_rate", score=0.0, weight=0.05,
            evidence="Rate of refused/rejected/escalated dispositions.",
        ),
        DimensionScore(
            dimension="context_retention", score=0.0, weight=0.05,
            evidence="Evidence reference and ledger ID preservation.",
        ),
    ],
)


# ── Benchmark case ──────────────────────────────────────────────────────


class QualityBenchmarkCase(BaseModel):
    """One case in the quality evaluation corpus.

    The *gold_constraints* and *gold_evidence_refs* are authoritative
    expectations. Deviations are measured, not penalised without evidence.
    """

    case_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    user_message: str = Field(min_length=1)
    gold_constraints: list[str] = Field(default_factory=list)
    gold_evidence_refs: list[str] = Field(default_factory=list)
    gold_disposition: str = "accept"
    max_acceptable_energy: int = 120
    max_acceptable_latency_ms: int = 30_000
    max_acceptable_cost_usd: float = 0.05


class QualityBenchmarkResult(BaseModel):
    """Per-case quality measurement result."""

    case_id: str
    disposition: str
    energy: int
    energy_pass: bool
    latency_ms: int | None = None
    latency_pass: bool = True
    cost_usd: float | None = None
    cost_pass: bool = True
    evidence_refs_found: list[str] = Field(default_factory=list)
    evidence_match: bool = False
    passed: bool = False
    limitations: list[str] = Field(default_factory=list)


class QualityBenchmarkRun(BaseModel):
    """Measurement-only quality benchmark run result.

    Stores no provider quality claim. Every measurement must be
    reproducible from deterministic or sanitized provider evidence.
    """

    run_id: str = Field(min_length=1)
    rubric: QualityRubric
    provider: str = ""
    model: str = ""
    cases_total: int = 0
    cases_passed: int = 0
    pass_rate: float = 0.0
    results: list[QualityBenchmarkResult] = Field(default_factory=list)
    claim_status: str = "measurement_only_no_quality_claim"
    limitations: list[str] = Field(default_factory=list)


def evaluate_quality_case(
    case: QualityBenchmarkCase,
    *,
    disposition: str,
    energy: int,
    latency_ms: int | None = None,
    cost_usd: float | None = None,
    evidence_refs: list[str] | None = None,
) -> QualityBenchmarkResult:
    """Score one benchmark case against its gold expectations.

    This is a measurement function. It does not make quality claims.
    """
    refs = evidence_refs or []
    energy_ok = energy <= case.max_acceptable_energy
    latency_ok = latency_ms is None or latency_ms <= case.max_acceptable_latency_ms
    cost_ok = cost_usd is None or cost_usd <= case.max_acceptable_cost_usd
    evidence_ok = all(ref in refs for ref in case.gold_evidence_refs)
    disposition_ok = disposition == case.gold_disposition
    all_ok = energy_ok and disposition_ok and evidence_ok and latency_ok and cost_ok
    return QualityBenchmarkResult(
        case_id=case.case_id,
        disposition=disposition,
        energy=energy,
        energy_pass=energy_ok,
        latency_ms=latency_ms,
        latency_pass=latency_ok,
        cost_usd=cost_usd,
        cost_pass=cost_ok,
        evidence_refs_found=refs,
        evidence_match=evidence_ok,
        passed=all_ok,
    )


def build_quality_benchmark_run(
    *,
    run_id: str,
    provider: str,
    model: str,
    rubric: QualityRubric | None = None,
    results: list[QualityBenchmarkResult],
) -> QualityBenchmarkRun:
    """Aggregate per-case results into a measurement-only run summary."""
    active_rubric = rubric or DEFAULT_RUBRIC
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    return QualityBenchmarkRun(
        run_id=run_id,
        rubric=active_rubric,
        provider=provider,
        model=model,
        cases_total=total,
        cases_passed=passed,
        pass_rate=passed / total if total > 0 else 0.0,
        results=results,
        limitations=["Provider comparison requires credentialed adapters (M17) for live data"],
    )
