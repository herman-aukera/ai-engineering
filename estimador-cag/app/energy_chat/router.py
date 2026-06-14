"""FastAPI transport for deterministic Energy Aware Chat evaluation."""

from __future__ import annotations

from fastapi import APIRouter

from app.energy_chat.contracts import EnergyChatRequest, EvaluationResult
from app.energy_chat.evaluator import evaluate_answer

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
