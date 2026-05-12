from pathlib import Path

STREAMLIT_SOURCE = Path("streamlit_app.py").read_text()


def test_streamlit_uses_product_estimation_form_as_primary_interface():
    assert "st.form(" in STREAMLIT_SOURCE
    assert "form_submit_button" in STREAMLIT_SOURCE


def test_streamlit_no_longer_uses_chat_input_as_primary_interface():
    assert "st.chat_input" not in STREAMLIT_SOURCE


def test_streamlit_sends_typed_session04_request_fields():
    assert '"description"' in STREAMLIT_SOURCE or "'description'" in STREAMLIT_SOURCE
    assert '"project_type"' in STREAMLIT_SOURCE or "'project_type'" in STREAMLIT_SOURCE
    assert '"detail_level"' in STREAMLIT_SOURCE or "'detail_level'" in STREAMLIT_SOURCE
    assert '"output_format"' in STREAMLIT_SOURCE or "'output_format'" in STREAMLIT_SOURCE
    assert '"reference_projects"' in STREAMLIT_SOURCE or "'reference_projects'" in STREAMLIT_SOURCE


def test_streamlit_displays_prompt_version_from_backend_response():
    assert "prompt_version" in STREAMLIT_SOURCE


def test_streamlit_posts_to_backend_estimate_endpoint_with_requests():
    assert "requests.post" in STREAMLIT_SOURCE
    assert "ESTIMATE_PATH" in STREAMLIT_SOURCE
    assert "/api/v1/estimate" in STREAMLIT_SOURCE


def test_streamlit_exposes_prompt_version_and_optional_reference_projects():
    assert "PROMPT_VERSION_OPTIONS" in STREAMLIT_SOURCE
    assert "Reference projects, optional" in STREAMLIT_SOURCE
    assert "parse_reference_projects" in STREAMLIT_SOURCE


def test_streamlit_text_area_uses_supported_streamlit_arguments():
    assert "min_chars=" not in STREAMLIT_SOURCE
    assert "max_chars=2000" in STREAMLIT_SOURCE
    assert "Project description must contain at least 20 characters." in STREAMLIT_SOURCE
