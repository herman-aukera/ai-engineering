"""Energy Aware Chat deterministic evaluator package."""

from app.energy_chat.agent import run_energy_aware_chat_agent
from app.energy_chat.artifact_registry import (
    CORE_ARTIFACTS,
    DOC_ARTIFACTS,
    EnergyChatArtifact,
    artifact_paths,
    list_energy_chat_artifacts,
)
from app.energy_chat.closeout_pack import (
    CloseoutPack,
    CloseoutSection,
    build_energy_chat_closeout_pack,
    render_energy_chat_closeout_markdown,
)
from app.energy_chat.contracts import (
    CriticFinding,
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    DeepSeekBenchmarkCase,
    DeepSeekBenchmarkCaseResult,
    DeepSeekBenchmarkRequest,
    DeepSeekBenchmarkRunResult,
    EnergyAwareChatAgentRequest,
    EnergyAwareChatAgentResult,
    EnergyCard,
    EnergyChatRequest,
    EnergyDecision,
    EnergyPolicy,
    EnergyScore,
    EvaluationResult,
    ProjectRagChunk,
    ProjectRagRequest,
    ProjectRagResult,
    RepairEvaluationResult,
    SourceNeedRequest,
    SourceNeedResult,
)
from app.energy_chat.evaluator import evaluate_answer, evaluate_with_one_pass_repair
from app.energy_chat.rag import retrieve_project_context
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
    "CloseoutPack",
    "CloseoutSection",
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
    "EnergyAwareChatAgentRequest",
    "EnergyAwareChatAgentResult",
    "EnergyCard",
    "EnergyChatArtifact",
    "EnergyChatRequest",
    "EnergyDecision",
    "EnergyPolicy",
    "EnergyScore",
    "EvaluationResult",
    "GateSnapshot",
    "ProjectRagChunk",
    "ProjectRagRequest",
    "ProjectRagResult",
    "ReleaseSnapshot",
    "RepairEvaluationResult",
    "ReviewPacket",
    "SourceNeedRequest",
    "SourceNeedResult",
    "artifact_paths",
    "build_ci_proof_command",
    "build_deepseek_benchmark_report_markdown",
    "build_energy_chat_closeout_pack",
    "build_local_gate_command",
    "build_release_snapshot",
    "build_release_snapshot_markdown",
    "build_review_packet",
    "classify_source_need",
    "evaluate_answer",
    "evaluate_with_one_pass_repair",
    "list_energy_chat_artifacts",
    "render_energy_chat_closeout_markdown",
    "retrieve_project_context",
    "run_energy_aware_chat_agent",
    "write_deepseek_benchmark_report",
]
