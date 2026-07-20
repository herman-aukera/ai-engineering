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
            "requirements_extraction_completed": True,
            "budget_matches": [
                {"budget_id": "budget-1", "raw_content": sensitive_text},
                {"budget_id": "budget-2", "raw_content": sensitive_text},
            ],
            "budget_search_completed": True,
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
        "requirements_extraction_completed": True,
        "budget_match_count": 2,
        "budget_search_completed": True,
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


def test_digest_distinguishes_not_started_from_completed_empty_stage() -> None:
    shared_state: dict[str, object] = {
        "requirements": [],
        "budget_matches": [],
        "estimate": None,
        "validation": None,
        "confidence": None,
        "review_required": False,
        "routing_steps": 0,
        "status": "pending",
    }

    not_started = build_supervisor_digest(
        {
            **shared_state,
            "requirements_extraction_completed": False,
            "budget_search_completed": False,
        }
    )
    completed_without_results = build_supervisor_digest(
        {
            **shared_state,
            "requirements_extraction_completed": True,
            "budget_search_completed": True,
        }
    )

    assert not_started.requirements_count == 0
    assert completed_without_results.requirements_count == 0
    assert not_started.budget_match_count == 0
    assert completed_without_results.budget_match_count == 0

    assert not_started.requirements_extraction_completed is False
    assert completed_without_results.requirements_extraction_completed is True
    assert not_started.budget_search_completed is False
    assert completed_without_results.budget_search_completed is True
