"""Matched deterministic benchmark for EACODE governance contracts.

This benchmark does not compare language-model intelligence. It compares the same
synthetic findings under a single unchecked proposal baseline and the deterministic
Energy-Aware boss. It therefore proves contract behavior only.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from energy_core.models import EnergyModel
from energy_core.multi_agent import DeterministicBoss, MultiAgentRun

BenchmarkDisposition = Literal["accept", "repair", "reject", "escalate"]
BenchmarkMode = Literal["single_unchecked", "governed"]


class GovernanceBenchmarkCase(EnergyModel):
    """One matched synthetic governance case."""

    case_id: str = Field(min_length=1)
    description: str = ""
    findings: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    expected_disposition: BenchmarkDisposition


class GovernanceBenchmarkResult(EnergyModel):
    """Outcome for one mode on one case."""

    case_id: str
    mode: BenchmarkMode
    disposition: BenchmarkDisposition
    expected_disposition: BenchmarkDisposition
    correct: bool


class GovernanceBenchmarkReport(EnergyModel):
    """Matched aggregate report with an explicit claim boundary."""

    cases: tuple[GovernanceBenchmarkCase, ...]
    results: tuple[GovernanceBenchmarkResult, ...]
    single_correct: int = Field(ge=0)
    governed_correct: int = Field(ge=0)
    total_cases: int = Field(ge=1)
    governed_delta: int
    governance_improves_contract_accuracy: bool
    claim_boundary: str = (
        "Deterministic contract benchmark only; this is not evidence that any "
        "provider model or multi-agent configuration improves real-world quality."
    )


def default_governance_cases() -> tuple[GovernanceBenchmarkCase, ...]:
    """Return immutable matched fixtures for the governance boundary."""

    return (
        GovernanceBenchmarkCase(
            case_id="clean-candidate",
            description="Independent critics agree that all gates passed.",
            findings=(
                {"owner": "critic-policy", "disposition": "accept"},
                {"owner": "critic-evidence", "disposition": "accept"},
            ),
            expected_disposition="accept",
        ),
        GovernanceBenchmarkCase(
            case_id="hard-constraint-violation",
            description="Consensus says accept, but one critic records a hard violation.",
            findings=(
                {"owner": "proposer", "disposition": "accept"},
                {
                    "owner": "critic-policy",
                    "disposition": "accept",
                    "hard_constraint_violation": True,
                },
            ),
            expected_disposition="reject",
        ),
        GovernanceBenchmarkCase(
            case_id="missing-evidence",
            description="The proposal looks acceptable but evidence remains incomplete.",
            findings=(
                {"owner": "proposer", "disposition": "accept"},
                {"owner": "critic-evidence", "disposition": "repair"},
            ),
            expected_disposition="repair",
        ),
        GovernanceBenchmarkCase(
            case_id="blocking-disagreement",
            description="A reviewer identifies a reject-level disagreement.",
            findings=(
                {"owner": "proposer", "disposition": "accept"},
                {"owner": "critic-security", "disposition": "reject"},
            ),
            expected_disposition="reject",
        ),
    )


def run_governance_benchmark(
    cases: tuple[GovernanceBenchmarkCase, ...] | None = None,
) -> GovernanceBenchmarkReport:
    """Run identical findings through unchecked and governed decision modes."""

    selected_cases = default_governance_cases() if cases is None else cases
    if not selected_cases:
        raise ValueError("At least one benchmark case is required.")

    boss = DeterministicBoss()
    results: list[GovernanceBenchmarkResult] = []

    for case in selected_cases:
        single = _single_unchecked_disposition(case.findings)
        governed_run = boss.aggregate(
            MultiAgentRun(run_id=f"benchmark-{case.case_id}"),
            findings=[dict(finding) for finding in case.findings],
        )
        governed = governed_run.final_disposition or "escalate"

        results.append(
            GovernanceBenchmarkResult(
                case_id=case.case_id,
                mode="single_unchecked",
                disposition=single,
                expected_disposition=case.expected_disposition,
                correct=single == case.expected_disposition,
            )
        )
        results.append(
            GovernanceBenchmarkResult(
                case_id=case.case_id,
                mode="governed",
                disposition=governed,
                expected_disposition=case.expected_disposition,
                correct=governed == case.expected_disposition,
            )
        )

    single_correct = sum(
        result.correct for result in results if result.mode == "single_unchecked"
    )
    governed_correct = sum(
        result.correct for result in results if result.mode == "governed"
    )
    return GovernanceBenchmarkReport(
        cases=selected_cases,
        results=tuple(results),
        single_correct=single_correct,
        governed_correct=governed_correct,
        total_cases=len(selected_cases),
        governed_delta=governed_correct - single_correct,
        governance_improves_contract_accuracy=governed_correct > single_correct,
    )


def _single_unchecked_disposition(
    findings: tuple[dict[str, Any], ...],
) -> BenchmarkDisposition:
    """Model an unsafe baseline that trusts the first proposal disposition."""

    if not findings:
        return "escalate"
    disposition = findings[0].get("disposition")
    if disposition in ("accept", "repair", "reject", "escalate"):
        return disposition
    return "escalate"
