from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.session14_supervision import (
    SupervisorDecision,
    build_supervisor_digest,
)


def test_supervisor_decision_rejects_unknown_routes_and_extra_authority() -> None:
    decision = SupervisorDecision(
        next_agent="requirements_extractor",
        reason_code="missing_requirements",
        reason="Atomic requirements have not been extracted.",
    )

    assert decision.next_agent == "requirements_extractor"
    assert decision.reason_code == "missing_requirements"

    with pytest.raises(ValidationError):
        SupervisorDecision(
            next_agent="send_estimate_email",
            reason_code="work_complete",
            reason="Send the result directly.",
        )

    with pytest.raises(ValidationError):
        SupervisorDecision(
            next_agent="budget_searcher",
            reason_code="missing_budget_evidence",
            reason="Historical evidence is missing.",
            tool="search_budgets",
        )


def test_supervisor_digest_is_bounded_and_excludes_sensitive_content() -> None:
    sensitive_text = "CLIENT-SECRET: migrate the confidential acquisition system"

    digest = build_supervisor_digest(
        {
            "transcript": sensitive_text,
            "requirements": [
                {
                    "requirement_id": "req-1",
                    "text": sensitive_text,
                }
            ],
            "budget_matches": [
                {"budget_id": "budget-1", "raw_content": sensitive_text},
                {"budget_id": "budget-2", "raw_content": sensitive_text},
            ],
            "estimate": {"total_hours": 120},
            "validation": None,
            "confidence": 0.62,
            "review_required": True,
            "routing_steps": 3,
            "status": "pending",
        }
    )

    assert digest.model_dump() == {
        "requirements_count": 1,
        "budget_match_count": 2,
        "estimate_ready": True,
        "validation_ready": False,
        "confidence": 0.62,
        "review_required": True,
        "routing_steps": 3,
        "status": "pending",
    }

    serialized = digest.model_dump_json()
    assert sensitive_text not in serialized
    assert "raw_content" not in serialized
    assert "transcript" not in serialized
