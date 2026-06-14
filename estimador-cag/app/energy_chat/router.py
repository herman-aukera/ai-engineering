"""FastAPI transport for deterministic Energy Aware Chat evaluation."""

from __future__ import annotations

from fastapi import APIRouter

from app.energy_chat import baseline
from app.energy_chat.contracts import (
    DeepSeekBaselineRequest,
    DeepSeekBaselineResult,
    EnergyChatRequest,
    EvaluationResult,
    RepairEvaluationResult,
)
from app.energy_chat.evaluator import evaluate_answer, evaluate_with_one_pass_repair

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


@router.post("/draft/deepseek-baseline", response_model=DeepSeekBaselineResult)
def draft_deepseek_baseline(request: DeepSeekBaselineRequest) -> DeepSeekBaselineResult:
    """
    Generate one plain DeepSeek draft answer before Energy Aware evaluation.

    This Slice 5 endpoint is the first provider seam. Normal tests monkeypatch
    the provider call and must not require real API keys. Use it for bounded
    baseline capture, not for benchmark claims yet.
    """
    return baseline.generate_deepseek_baseline_draft(request)
