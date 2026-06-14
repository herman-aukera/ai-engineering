"""Energy Aware Chat deterministic evaluator package."""

from app.energy_chat.artifact_registry import (
    CORE_ARTIFACTS,
    DOC_ARTIFACTS,
    EnergyChatArtifact,
    artifact_paths,
    list_energy_chat_artifacts,
)
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
from app.energy_chat.release_snapshot import (
    GateSnapshot,
    ReleaseSnapshot,
    build_release_snapshot,
    build_release_snapshot_markdown,
)
from app.energy_chat.reports import (
    build_deepseek_benchmark_report_markdown,
    write_deepseek_benchmark_report,
)
from app.energy_chat.review_packet import ReviewPacket, build_review_packet
from app.energy_chat.source_guard import classify_source_need
from app.energy_chat.workflow_proof import (
    ENERGY_CHAT_BRANCH,
    ENERGY_CHAT_PROOF_SCRIPT,
    ENERGY_CHAT_VALIDATION_SCRIPT,
    ENERGY_CHAT_WORKFLOW,
    build_ci_proof_command,
    build_local_gate_command,
)

__all__ = [
    "CORE_ARTIFACTS",
    "DOC_ARTIFACTS",
    "CriticFinding",
    "DeepSeekBaselineRequest",
    "DeepSeekBaselineResult",
    "DeepSeekBenchmarkCase",
    "DeepSeekBenchmarkCaseResult",
    "DeepSeekBenchmarkRequest",
    "DeepSeekBenchmarkRunResult",
    "ENERGY_CHAT_BRANCH",
    "ENERGY_CHAT_PROOF_SCRIPT",
    "ENERGY_CHAT_VALIDATION_SCRIPT",
    "ENERGY_CHAT_WORKFLOW",
    "EnergyCard",
    "EnergyChatArtifact",
    "EnergyChatRequest",
    "EnergyDecision",
    "EnergyPolicy",
    "EnergyScore",
    "EvaluationResult",
    "GateSnapshot",
    "ReleaseSnapshot",
    "RepairEvaluationResult",
    "ReviewPacket",
    "SourceNeedRequest",
    "SourceNeedResult",
    "artifact_paths",
    "build_ci_proof_command",
    "build_deepseek_benchmark_report_markdown",
    "build_local_gate_command",
    "build_release_snapshot",
    "build_release_snapshot_markdown",
    "build_review_packet",
    "classify_source_need",
    "evaluate_answer",
    "evaluate_with_one_pass_repair",
    "list_energy_chat_artifacts",
    "write_deepseek_benchmark_report",
]
