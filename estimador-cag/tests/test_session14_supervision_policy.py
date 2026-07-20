from __future__ import annotations

import pytest

from app.schemas.session14_supervision import SupervisorStateDigest
from app.services.session14_supervision import (
    MAX_ROUTING_STEPS,
    choose_deterministic_route,
)


def _digest(**overrides: object) -> SupervisorStateDigest:
    values: dict[str, object] = {
        "requirements_count": 0,
        "requirements_extraction_completed": False,
        "budget_match_count": 0,
        "budget_search_completed": False,
        "estimate_ready": False,
        "validation_ready": False,
        "confidence": None,
        "review_required": False,
        "routing_steps": 0,
        "status": "pending",
    }
    values.update(overrides)
    return SupervisorStateDigest.model_validate(values)


@pytest.mark.parametrize(
    ("overrides", "expected_destination", "expected_reason_code"),
    [
        pytest.param(
            {},
            "requirements_extractor",
            "missing_requirements",
            id="requirements-not-extracted",
        ),
        pytest.param(
            {
                "requirements_count": 2,
                "requirements_extraction_completed": True,
            },
            "budget_searcher",
            "missing_budget_evidence",
            id="budget-search-not-completed",
        ),
        pytest.param(
            {
                "requirements_count": 2,
                "requirements_extraction_completed": True,
                "budget_match_count": 0,
                "budget_search_completed": True,
            },
            "estimate_generator",
            "missing_estimate",
            id="completed-search-with-no-precedent",
        ),
        pytest.param(
            {
                "requirements_count": 2,
                "requirements_extraction_completed": True,
                "budget_match_count": 2,
                "budget_search_completed": True,
                "estimate_ready": True,
            },
            "coherence_validator",
            "missing_validation",
            id="estimate-not-validated",
        ),
        pytest.param(
            {
                "requirements_count": 2,
                "requirements_extraction_completed": True,
                "budget_match_count": 2,
                "budget_search_completed": True,
                "estimate_ready": True,
                "validation_ready": True,
                "review_required": True,
            },
            "human_review_gate",
            "human_review_required",
            id="protected-result",
        ),
        pytest.param(
            {
                "requirements_count": 2,
                "requirements_extraction_completed": True,
                "budget_match_count": 2,
                "budget_search_completed": True,
                "estimate_ready": True,
                "validation_ready": True,
            },
            "finalize",
            "work_complete",
            id="validated-safe-result",
        ),
    ],
)
def test_deterministic_route_enforces_contextual_prerequisites(
    overrides: dict[str, object],
    expected_destination: str,
    expected_reason_code: str,
) -> None:
    decision = choose_deterministic_route(_digest(**overrides))

    assert decision.next_agent == expected_destination
    assert decision.reason_code == expected_reason_code
    assert decision.reason.strip()


def test_routing_budget_preempts_additional_agent_work() -> None:
    decision = choose_deterministic_route(
        _digest(routing_steps=MAX_ROUTING_STEPS)
    )

    assert decision.next_agent == "human_review_gate"
    assert decision.reason_code == "routing_budget_exhausted"


def test_route_selection_does_not_mutate_the_digest() -> None:
    digest = _digest(
        requirements_count=2,
        requirements_extraction_completed=True,
    )
    before = digest.model_dump()

    choose_deterministic_route(digest)

    assert digest.model_dump() == before
