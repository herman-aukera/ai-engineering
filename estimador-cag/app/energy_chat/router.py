"""FastAPI transport for deterministic Energy Aware Chat evaluation."""

from __future__ import annotations

from fastapi import APIRouter

from app.energy_chat import baseline, benchmark
from app.energy_chat.agent import run_energy_aware_chat_agent
from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    DeepSeekBenchmarkRequest,
    DeepSeekBenchmarkRunResult,
    EnergyAwareChatAgentRequest,
    EnergyAwareChatAgentResult,
    EnergyChatRequest,
    EvaluationResult,
    EvidenceBundleRequest,
    EvidenceBundleResult,
    ProjectRagRequest,
    ProjectRagResult,
    RepairEvaluationResult,
    SourceNeedRequest,
    SourceNeedResult,
)
from app.energy_chat.evaluator import evaluate_answer, evaluate_with_one_pass_repair
from app.energy_chat.evidence import build_evidence_bundle
from app.energy_chat.rag import retrieve_project_context
from app.energy_chat.source_guard import classify_source_need

router = APIRouter()


@router.post("/evaluate", response_model=EvaluationResult)
def evaluate_energy_chat(request: EnergyChatRequest) -> EvaluationResult:
    """
    Evaluate a draft assistant answer against the deterministic energy policy.

    This endpoint is intentionally provider-free in Slice 2. It does not call
    DeepSeek, OpenAI, Kimi, RAG, or any external service; it only exposes the
    tested deterministic evaluator through FastAPI.
    """
    return evaluate_answer(request)


@router.post("/evaluate/repair-once", response_model=RepairEvaluationResult)
def evaluate_energy_chat_with_one_pass_repair(request: EnergyChatRequest) -> RepairEvaluationResult:
    """
    Evaluate a draft and apply one deterministic repair when repairable.

    This Slice 4 endpoint is still provider-free. It does not call DeepSeek,
    OpenAI, Kimi, RAG, or a repair model; it only runs deterministic repair
    text patches for known critic findings.
    """
    return evaluate_with_one_pass_repair(request)


@router.post("/source-needed", response_model=SourceNeedResult)
def classify_energy_chat_source_need(request: SourceNeedRequest) -> SourceNeedResult:
    """
    Classify whether the request needs current or project evidence.

    This Batch 8 endpoint prepares research and project modes without adding
    RAG yet. It is deterministic, provider-free, and CI safe.
    """
    return classify_source_need(request)


@router.post("/evidence/bundle", response_model=EvidenceBundleResult)
def build_energy_chat_evidence_bundle(
    request: EvidenceBundleRequest,
) -> EvidenceBundleResult:
    """
    Normalize evidence refs and command outputs for project/research checks.

    This Batch 9 endpoint prepares project grounding without adding a vector
    database, repository crawler, or live provider call. It only turns attached
    evidence strings into typed refs that the evaluator can already consume.
    """
    return build_evidence_bundle(request)


@router.post("/rag/search", response_model=ProjectRagResult)
def search_energy_chat_project_sources(request: ProjectRagRequest) -> ProjectRagResult:
    """
    Retrieve committed project-source evidence for Energy Aware Chat answers.

    This Slice 21 endpoint is the CI-safe RAG baseline. It uses deterministic
    lexical cosine retrieval over committed project-source chunks, not live web,
    provider embeddings, or production vector search.
    """
    return retrieve_project_context(request)


@router.post("/chat", response_model=EnergyAwareChatAgentResult)
def chat_energy_aware_mvp(request: EnergyAwareChatAgentRequest) -> EnergyAwareChatAgentResult:
    """
    Run the local MVP agent path: retrieve, draft, critique, repair, and return an Energy Card.

    This endpoint provides deterministic agent orchestration for final-project
    validation while keeping live provider calls and deployment evidence as
    separate controlled gates.
    """
    return run_energy_aware_chat_agent(request)


@router.post("/draft/deepseek-baseline", response_model=DeepSeekBaselineResult)
def draft_deepseek_baseline(request: DeepSeekBaselineRequest) -> DeepSeekBaselineResult:
    """
    Generate one plain DeepSeek draft answer before Energy Aware evaluation.

    This Slice 5 endpoint is the first provider seam. Normal tests monkeypatch
    the provider call and must not require real API keys. Use it for bounded
    baseline capture, not for benchmark claims yet.
    """
    return baseline.generate_deepseek_baseline_draft(request)


@router.post("/benchmark/deepseek-energy-aware", response_model=DeepSeekBenchmarkRunResult)
def benchmark_deepseek_energy_aware(
    request: DeepSeekBenchmarkRequest,
) -> DeepSeekBenchmarkRunResult:
    """
    Run measurement-only DeepSeek baseline plus Energy Aware evaluation.

    This Slice 6 endpoint stores no benchmark claim. Normal tests monkeypatch
    the provider call and must not require live DeepSeek credentials.
    """
    return benchmark.run_deepseek_energy_benchmark(request)
