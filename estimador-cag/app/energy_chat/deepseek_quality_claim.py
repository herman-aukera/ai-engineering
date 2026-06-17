"""Convert DeepSeek benchmark output into release-claim evidence.

This module is intentionally deterministic. It does not call a provider; it only
summarizes a completed benchmark result into the evidence contract consumed by
``release_claims.py``.
"""

from __future__ import annotations

from app.energy_chat.contracts import DeepSeekBenchmarkRunResult
from app.energy_chat.release_claims import DeepSeekQualityEvidence

QUALITY_METRIC_NAME = "accepted_answer_rate_after_one_repair"


def build_deepseek_quality_evidence(
    result: DeepSeekBenchmarkRunResult,
    *,
    report_path: str,
    live_provider_run: bool,
) -> DeepSeekQualityEvidence:
    """Build release-claim evidence from a completed benchmark run."""

    cases_total = result.cases_total
    plain_score = _rate(result.accepted_baseline, cases_total)
    energy_aware_score = _rate(result.accepted_after_repair, cases_total)
    return DeepSeekQualityEvidence(
        run_id=result.run_id,
        cases_total=cases_total,
        plain_deepseek_score=plain_score,
        energy_aware_score=energy_aware_score,
        metric_name=QUALITY_METRIC_NAME,
        report_path=report_path,
        live_provider_run=live_provider_run,
    )


def render_deepseek_quality_markdown(
    result: DeepSeekBenchmarkRunResult,
    evidence: DeepSeekQualityEvidence,
) -> str:
    """Render a reviewer-visible bounded DeepSeek comparison report."""

    improvement = None
    if (
        evidence.plain_deepseek_score is not None
        and evidence.energy_aware_score is not None
    ):
        improvement = evidence.energy_aware_score - evidence.plain_deepseek_score

    lines = [
        "# Energy Aware Chat DeepSeek quality benchmark",
        "",
        "Status: bounded benchmark evidence for the release-claim gate.",
        "",
        "This report may only support the phrase `quality improvement over plain DeepSeek` ",
        "when the run is live, the task set has at least three cases, and the energy-aware ",
        "score is higher than the plain DeepSeek score under the named metric.",
        "",
        "## Summary",
        "",
        f"- run_id: `{result.run_id}`",
        f"- provider: `{result.provider}`",
        f"- model: `{result.model}`",
        f"- tier: `{result.tier}`",
        f"- cases_total: `{result.cases_total}`",
        f"- metric_name: `{evidence.metric_name}`",
        f"- live_provider_run: `{str(evidence.live_provider_run).lower()}`",
        f"- plain_deepseek_score: `{_format_score(evidence.plain_deepseek_score)}`",
        f"- energy_aware_score: `{_format_score(evidence.energy_aware_score)}`",
        f"- improvement_delta: `{_format_score(improvement)}`",
        "",
        "## Case results",
        "",
        "| Case | Baseline decision | Final decision | Final energy | Accepted after repair | Delta after repair |",
        "|---|---|---|---:|---|---:|",
    ]

    for item in result.results:
        lines.append(
            "| "
            f"`{item.case.case_id}` | "
            f"`{item.baseline_evaluation.decision.decision}` | "
            f"`{item.final_decision}` | "
            f"{item.final_energy} | "
            f"`{str(item.accepted_after_repair).lower()}` | "
            f"{item.energy_delta_after_repair} |"
        )

    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            "Allowed only if the release-claim gate passes:",
            "",
            "```text",
            "quality improvement over plain DeepSeek",
            "```",
            "",
            "Forbidden if this report is not from a live provider run or does not show a positive score delta:",
            "",
            "```text",
            "quality improvement over plain DeepSeek",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _format_score(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"
