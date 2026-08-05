"""Report helpers for Energy Aware Chat benchmark runs."""

from __future__ import annotations

from pathlib import Path

from app.energy_chat.contracts import DeepSeekBenchmarkRunResult


def _percent(numerator: int, denominator: int) -> str:
    """Format a safe percentage for report summaries."""

    if denominator <= 0:
        return "0.00%"
    return f"{(numerator / denominator) * 100:.2f}%"


def _safe_cell(value: object) -> str:
    """Return a markdown-table-safe cell value."""

    return str(value).replace("|", "\\|").replace("\n", " ")


def build_deepseek_benchmark_report_markdown(
    result: DeepSeekBenchmarkRunResult,
) -> str:
    """Build a measurement-only Markdown report for a benchmark run.

    The report deliberately records evidence and limitations without claiming that
    Energy Aware Chat improved model quality. Benchmark claims require fixed live
    runs and human review in a later slice.
    """

    claim_status = result.metadata.get(
        "claim_status",
        "measurement_only_no_quality_claim",
    )
    accepted_baseline_rate = _percent(result.accepted_baseline, result.cases_total)
    accepted_after_repair_rate = _percent(
        result.accepted_after_repair,
        result.cases_total,
    )

    lines = [
        "# Energy Aware Chat Benchmark Report",
        "",
        "## Scope",
        "",
        "This report is a measurement artifact only. It does not claim that ",
        "Energy Aware Chat improves DeepSeek output quality.",
        "",
        "## Run summary",
        "",
        f"- Run ID: `{result.run_id}`",
        f"- Provider: `{result.provider}`",
        f"- Model: `{result.model}`",
        f"- Tier: `{result.tier}`",
        f"- Cases total: {result.cases_total}",
        f"- Accepted baseline: {result.accepted_baseline} ({accepted_baseline_rate})",
        "- Accepted after deterministic repair: "
        f"{result.accepted_after_repair} ({accepted_after_repair_rate})",
        f"- Repairs attempted: {result.repairs_attempted}",
        f"- Hard rejects: {result.hard_rejects}",
        f"- Claim status: `{claim_status}`",
        "",
        "## Case results",
        "",
        "| Case | Baseline decision | Final decision | Baseline energy | "
        "Final energy | Delta | Repair attempted |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]

    for item in result.results:
        baseline_decision = item.baseline_evaluation.decision.decision
        baseline_energy = item.baseline_evaluation.score.total_energy
        lines.append(
            "| "
            f"{_safe_cell(item.case.case_id)} | "
            f"{_safe_cell(baseline_decision)} | "
            f"{_safe_cell(item.final_decision)} | "
            f"{baseline_energy} | "
            f"{item.final_energy} | "
            f"{item.energy_delta_after_repair} | "
            f"{item.repair_evaluation.repair_attempted} |"
        )

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "1. Normal CI uses fake providers, so live model quality is not proven here.",
            "2. Deterministic repair is rule-based and intentionally narrow.",
            "3. This report is not a substitute for a fixed benchmark dataset, live "
            "DeepSeek runs, and human review.",
            "",
            "## Next action",
            "",
            "Run the same fixed cases with plain DeepSeek, structured-prompt "
            "DeepSeek, and the energy-aware loop before making any improvement claim.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_deepseek_benchmark_report(
    result: DeepSeekBenchmarkRunResult,
    output_path: Path | str,
) -> Path:
    """Write a measurement-only Markdown benchmark report to disk."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        build_deepseek_benchmark_report_markdown(result),
        encoding="utf-8",
    )
    return path
