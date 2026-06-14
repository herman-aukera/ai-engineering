"""Energy Aware Chat deterministic evaluator package."""

from app.energy_chat.contracts import (
    CriticFinding,
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    DeepSeekBenchmarkCase,
    DeepSeekBenchmarkCaseResult,
    DeepSeekBenchmarkRequest,
    DeepSeekBenchmarkRunResult,
    EnergyCard,
    EnergyChatRequest,
    EnergyDecision,
    EnergyPolicy,
    EnergyScore,
    EvaluationResult,
    RepairEvaluationResult,
    SourceNeedRequest,
    SourceNeedResult,
)
from app.energy_chat.evaluator import evaluate_answer, evaluate_with_one_pass_repair
from app.energy_chat.reports import (
    build_deepseek_benchmark_report_markdown,
    write_deepseek_benchmark_report,
)
from app.energy_chat.source_guard import classify_source_need

__all__ = [
    "CriticFinding",
    "DeepSeekBaselineRequest",
    "DeepSeekBaselineResult",
    "DeepSeekBenchmarkCase",
    "DeepSeekBenchmarkCaseResult",
    "DeepSeekBenchmarkRequest",
    "DeepSeekBenchmarkRunResult",
    "EnergyCard",
    "EnergyChatRequest",
    "EnergyDecision",
    "EnergyPolicy",
    "EnergyScore",
    "EvaluationResult",
    "RepairEvaluationResult",
    "SourceNeedRequest",
    "SourceNeedResult",
    "build_deepseek_benchmark_report_markdown",
    "classify_source_need",
    "evaluate_answer",
    "evaluate_with_one_pass_repair",
    "write_deepseek_benchmark_report",
]
