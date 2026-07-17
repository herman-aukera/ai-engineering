"""Fixed deterministic benchmark for Energy Aware Chat quality gates.

This benchmark intentionally does not call DeepSeek or Kimi. It evaluates a
versioned dataset of baseline drafts so CI can prove the evaluator, repair seam,
and benchmark reporting stay stable. Live provider comparisons must be recorded
separately before making any quality-improvement claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.energy_chat.contracts import EnergyChatRequest, Mode
from app.energy_chat.evaluator import evaluate_with_one_pass_repair, run_evaluation

DEFAULT_FIXED_BENCHMARK_PATH = (
    Path(__file__).resolve().parents[2]
    / "evals"
    / "energy_chat"
    / "fixed_benchmark_cases.jsonl"
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FixedBenchmarkCase(BaseModel):
    """One deterministic benchmark case with a fixed baseline draft."""

    case_id: str
    category: str
    user_message: str
    mode: Mode = "chat_lite"
    required_constraints: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    baseline_draft_answer: str
    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)


class FixedBenchmarkCaseResult(BaseModel):
    """Per-case deterministic benchmark measurement."""

    case: FixedBenchmarkCase
    baseline_decision: str
    baseline_energy: int
    final_decision: str
    final_energy: int
    energy_delta_after_repair: int
    accepted_baseline: bool
    accepted_after_repair: bool
    repairs_attempted: bool
    hard_reject_violations: list[str] = Field(default_factory=list)
    hard_repair_violations: list[str] = Field(default_factory=list)
    soft_violations: list[str] = Field(default_factory=list)
    missing_expected_terms: list[str] = Field(default_factory=list)
    forbidden_terms_present: list[str] = Field(default_factory=list)


class FixedBenchmarkRunResult(BaseModel):
    """Deterministic benchmark run summary."""

    run_id: str
    dataset_path: str
    cases_total: int
    accepted_baseline: int
    accepted_after_repair: int
    repairs_attempted: int
    hard_rejects: int
    average_energy_delta_after_repair: float
    results: list[FixedBenchmarkCaseResult]
    metadata: dict[str, Any] = Field(default_factory=dict)


def load_fixed_benchmark_cases(
    path: Path = DEFAULT_FIXED_BENCHMARK_PATH,
) -> list[FixedBenchmarkCase]:
    """Load JSONL cases and validate each row with Pydantic."""

    cases: list[FixedBenchmarkCase] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        cases.append(FixedBenchmarkCase.model_validate(payload))
    if not cases:
        raise ValueError(f"Fixed benchmark dataset is empty: {path}")
    return cases


def run_fixed_benchmark(
    *,
    run_id: str = "energy-chat-fixed-benchmark-local",
    dataset_path: Path = DEFAULT_FIXED_BENCHMARK_PATH,
) -> FixedBenchmarkRunResult:
    """Run deterministic evaluator and one-pass repair against fixed cases."""

    cases = load_fixed_benchmark_cases(dataset_path)
    results: list[FixedBenchmarkCaseResult] = []
    for case in cases:
        request = EnergyChatRequest(
            user_message=case.user_message,
            draft_answer=case.baseline_draft_answer,
            mode=case.mode,
            required_constraints=case.required_constraints,
            required_sections=case.required_sections,
            evidence_refs=case.evidence_refs,
            metadata={
                "benchmark_family": "energy_chat_fixed_deterministic",
                "benchmark_case_id": case.case_id,
                "benchmark_category": case.category,
            },
        )
        baseline = run_evaluation(request)
        repaired = evaluate_with_one_pass_repair(request)
        final = repaired.final_result
        final_answer = final.request.draft_answer
        results.append(
            FixedBenchmarkCaseResult(
                case=case,
                baseline_decision=baseline.decision.decision,
                baseline_energy=baseline.score.total_energy,
                final_decision=final.decision.decision,
                final_energy=final.score.total_energy,
                energy_delta_after_repair=final.score.total_energy - baseline.score.total_energy,
                accepted_baseline=baseline.decision.decision == "accept",
                accepted_after_repair=final.decision.decision == "accept",
                repairs_attempted=repaired.repair_attempted,
                hard_reject_violations=baseline.score.hard_reject_violations,
                hard_repair_violations=baseline.score.hard_repair_violations,
                soft_violations=baseline.score.soft_violations,
                missing_expected_terms=_missing_terms(final_answer, case.must_include),
                forbidden_terms_present=_present_terms(final_answer, case.must_not_include),
            )
        )

    accepted_baseline = sum(result.accepted_baseline for result in results)
    accepted_after_repair = sum(result.accepted_after_repair for result in results)
    repairs_attempted = sum(result.repairs_attempted for result in results)
    hard_rejects = sum(bool(result.hard_reject_violations) for result in results)
    average_delta = sum(result.energy_delta_after_repair for result in results) / len(results)

    return FixedBenchmarkRunResult(
        run_id=run_id,
        dataset_path=_display_dataset_path(dataset_path),
        cases_total=len(results),
        accepted_baseline=accepted_baseline,
        accepted_after_repair=accepted_after_repair,
        repairs_attempted=repairs_attempted,
        hard_rejects=hard_rejects,
        average_energy_delta_after_repair=round(average_delta, 2),
        results=results,
        metadata={
            "benchmark_family": "energy_chat_fixed_deterministic",
            "claim_status": "measurement_only_no_quality_claim",
            "provider_calls": 0,
            "live_provider_required": False,
            "quality_claim_allowed": False,
        },
    )


def render_fixed_benchmark_markdown(result: FixedBenchmarkRunResult) -> str:
    """Render a reviewer-readable deterministic benchmark report."""

    lines = [
        "# Energy Aware Chat Fixed Benchmark Report",
        "",
        "status: generated-deterministic-evidence",
        f"run_id: `{result.run_id}`",
        f"dataset_path: `{result.dataset_path}`",
        "claim_status: `measurement_only_no_quality_claim`",
        "",
        "## Summary",
        "",
        f"- Cases total: {result.cases_total}",
        f"- Accepted baseline: {result.accepted_baseline}",
        f"- Accepted after repair: {result.accepted_after_repair}",
        f"- Repairs attempted: {result.repairs_attempted}",
        f"- Hard rejects: {result.hard_rejects}",
        f"- Average energy delta after repair: {result.average_energy_delta_after_repair}",
        "",
        "## Boundary",
        "",
        "This report is deterministic CI evidence. It does not prove live provider quality improvement.",
        "Use it to verify benchmark plumbing, case stability, evaluator behavior, and repair behavior.",
        "",
        "## Cases",
        "",
        "| Case | Category | Baseline | Final | Energy delta | Missing expected terms | Forbidden terms present |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in result.results:
        lines.append(
            "| "
            f"{item.case.case_id} | "
            f"{item.case.category} | "
            f"{item.baseline_decision} / {item.baseline_energy} | "
            f"{item.final_decision} / {item.final_energy} | "
            f"{item.energy_delta_after_repair} | "
            f"{', '.join(item.missing_expected_terms) or 'none'} | "
            f"{', '.join(item.forbidden_terms_present) or 'none'} |"
        )
    lines.extend(
        [
            "",
            "## Next step",
            "",
            "Run a separate live-provider benchmark over the same case IDs before making any quality-improvement claim.",
            "",
        ]
    )
    return "\n".join(lines)


def _display_dataset_path(dataset_path: Path) -> str:
    resolved = dataset_path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(dataset_path)


def _missing_terms(text: str, terms: list[str]) -> list[str]:
    lower_text = text.lower()
    return [term for term in terms if term.lower() not in lower_text]


def _present_terms(text: str, terms: list[str]) -> list[str]:
    lower_text = text.lower()
    return [term for term in terms if term.lower() in lower_text]
