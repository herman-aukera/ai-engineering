import pytest
from pydantic import ValidationError

from app.schemas.estimation import (
    DetailLevel,
    EstimationRequest,
    EstimationResponse,
    OutputFormat,
    ProjectType,
)

VALID_DESCRIPTION = (
    "Build a customer onboarding web product with authentication, admin review, "
    "email notifications, and a basic reporting dashboard."
)


def test_session04_request_serializes_enum_values_for_json_payloads():
    request = EstimationRequest(
        description=VALID_DESCRIPTION,
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
    )

    assert request.model_dump(mode="json") == {
        "description": VALID_DESCRIPTION,
        "project_type": "web_saas",
        "detail_level": "medium",
        "output_format": "phases_table",
    }


def test_session04_request_rejects_short_description():
    with pytest.raises(ValidationError) as exc_info:
        EstimationRequest(
            description="Too short",
            project_type="mobile_app",
            detail_level="summary",
            output_format="narrative",
        )

    assert "String should have at least 20 characters" in str(exc_info.value)


def test_session04_request_rejects_invalid_enum_value():
    with pytest.raises(ValidationError) as exc_info:
        EstimationRequest(
            description=VALID_DESCRIPTION,
            project_type="wordpress_site",
            detail_level="summary",
            output_format="narrative",
        )

    assert "wordpress_site" in str(exc_info.value)


def test_session04_response_contains_text_and_prompt_version_only():
    response = EstimationResponse(
        text="## Estimate\n\nThe implementation can be delivered in three phases.",
        prompt_version="v1",
    )

    assert response.model_dump() == {
        "text": "## Estimate\n\nThe implementation can be delivered in three phases.",
        "prompt_version": "v1",
    }
