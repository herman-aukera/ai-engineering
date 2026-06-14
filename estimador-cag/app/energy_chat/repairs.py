"""Deterministic one pass repair helpers for Energy Aware Chat."""

from __future__ import annotations

import re

from app.energy_chat.contracts import EnergyChatRequest, EvaluationResult

REPAIR_NOTE = "deterministic_one_pass_repair"


def build_repaired_request(
    request: EnergyChatRequest,
    initial_result: EvaluationResult,
) -> tuple[EnergyChatRequest | None, list[str]]:
    """
    Build a deterministic repaired request for repairable findings.

    This is a seam for Slice 4. It deliberately avoids model calls and only
    applies explicit, auditable text patches for findings the deterministic
    critics already emitted.
    """

    if initial_result.decision.decision != "repair":
        return None, []

    findings = initial_result.score.findings
    violation_ids = {finding.violation_id for finding in findings}
    draft = _repair_scope_explosion(request.draft_answer) if "scope_explosion" in violation_ids else request.draft_answer
    draft_parts = [draft.strip()]
    repairs_applied: list[str] = []

    if "missing_user_constraint" in violation_ids:
        for constraint in request.required_constraints:
            if constraint.strip() and constraint.casefold() not in draft.casefold():
                draft_parts.append(f"Constraint satisfied: {constraint}.")
                repairs_applied.append(f"added_required_constraint:{constraint}")

    if "missing_mode_requirement" in violation_ids:
        for section in request.required_sections:
            if section.strip() and section.casefold() not in draft.casefold():
                draft_parts.append(
                    f"## {section}\nThis section is included to satisfy the required output structure."
                )
                repairs_applied.append(f"added_required_section:{section}")

    if "scope_explosion" in violation_ids:
        draft_parts.append(
            "Scope control: future slice components such as RAG, provider calls, "
            "or extra UI work are deferred until their own validated slice."
        )
        repairs_applied.append("added_scope_control")

    if "missing_comparison" in violation_ids:
        draft_parts.append(
            "Comparison: the safer option is to finish the current deterministic "
            "slice first, while provider and RAG work remain later slices."
        )
        repairs_applied.append("added_comparison")

    if "missing_tradeoffs" in violation_ids:
        draft_parts.append(
            "Tradeoff: this is slower than jumping to model calls, but it lowers "
            "implementation risk because each layer has test evidence."
        )
        repairs_applied.append("added_tradeoffs")

    if "missing_next_action" in violation_ids:
        draft_parts.append(
            "Next action: run the validation gate and inspect the Energy Card "
            "before claiming success."
        )
        repairs_applied.append("added_next_action")

    if not repairs_applied:
        return None, []

    metadata = dict(request.metadata)
    metadata["repair_strategy"] = REPAIR_NOTE
    metadata["repairs_applied"] = repairs_applied

    return (
        request.model_copy(
            update={
                "draft_answer": "\n\n".join(part for part in draft_parts if part),
                "metadata": metadata,
            }
        ),
        repairs_applied,
    )


def _repair_scope_explosion(draft_answer: str) -> str:
    replacements = {
        "also add rag": "defer RAG",
        "add rag": "defer RAG",
        "implement rag": "defer RAG",
        "add streamlit": "defer extra UI work",
        "add fastapi": "defer extra API work",
        "call deepseek": "defer provider calls",
        "call openai": "defer provider calls",
        "call kimi": "defer provider calls",
        "langgraph": "future orchestration",
        "vector database": "future retrieval storage",
        "production ready": "MVP ready with caveats",
        "start by skipping the current slice": "Next action: finish the current validated slice",
        "skip the current slice": "finish the current validated slice",
        "skip current slice": "finish the current validated slice",
    }
    repaired = draft_answer
    for marker, replacement in replacements.items():
        repaired = re.sub(re.escape(marker), replacement, repaired, flags=re.IGNORECASE)
    return repaired
