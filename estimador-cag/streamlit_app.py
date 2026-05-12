"""
Streamlit product interface for the Session 04 typed estimation flow.

LAYER: frontend
RESPONSIBILITY: Collect typed estimation parameters and call the FastAPI backend.
WHY IT EXISTS: Session 04 turns the estimator from a free chat into a product
               interface with explicit request fields.
DEPENDS ON: streamlit, requests, FastAPI /api/v1/estimate.
"""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

DEFAULT_BACKEND_URL = "http://localhost:8000"
ESTIMATE_PATH = "/api/v1/estimate"

PROJECT_TYPE_OPTIONS = {
    "Mobile app": "mobile_app",
    "Web SaaS": "web_saas",
    "Internal tool": "internal_tool",
    "Data pipeline": "data_pipeline",
}

DETAIL_LEVEL_OPTIONS = {
    "Summary": "summary",
    "Medium": "medium",
    "Detailed": "detailed",
}

OUTPUT_FORMAT_OPTIONS = {
    "Phases table": "phases_table",
    "Line items": "line_items",
    "Narrative": "narrative",
}


def get_backend_url() -> str:
    """Return the configured backend base URL without a trailing slash."""

    return os.getenv("ESTIMADOR_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def build_estimate_url() -> str:
    """Build the FastAPI estimate endpoint URL used by the product form."""

    return f"{get_backend_url()}{ESTIMATE_PATH}"


def post_estimation_request(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Send the typed estimation payload to the backend.

    Raises:
        requests.HTTPError: When the backend returns a non-success response.
        requests.RequestException: For connection and timeout failures.
    """

    response = requests.post(
        build_estimate_url(),
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    """Render the Session 04 typed product estimation form."""

    st.set_page_config(
        page_title="AI Software Estimator",
        page_icon="🧠",
        layout="wide",
    )

    st.title("AI Software Estimator")
    st.caption("Typed product interface powered by the FastAPI estimator backend.")

    with st.sidebar:
        st.subheader("Backend")
        st.code(build_estimate_url())
        st.caption("Set ESTIMADOR_BACKEND_URL when running outside localhost.")

    with st.form("product_estimation_form"):
        description = st.text_area(
            "Project description",
            min_chars=20,
            max_chars=2000,
            height=220,
            placeholder=(
                "Describe the product, users, integrations, constraints, timeline, "
                "and any known technical requirements."
            ),
        )

        col_project, col_detail, col_format = st.columns(3)

        with col_project:
            project_type_label = st.selectbox(
                "Project type",
                options=list(PROJECT_TYPE_OPTIONS.keys()),
                index=1,
            )

        with col_detail:
            detail_level_label = st.selectbox(
                "Detail level",
                options=list(DETAIL_LEVEL_OPTIONS.keys()),
                index=1,
            )

        with col_format:
            output_format_label = st.selectbox(
                "Output format",
                options=list(OUTPUT_FORMAT_OPTIONS.keys()),
                index=0,
            )

        submitted = st.form_submit_button("Generate estimate", type="primary")

    if not submitted:
        st.info("Fill the form and generate an estimate when the project shape is clear.")
        return

    payload = {
        "description": description,
        "project_type": PROJECT_TYPE_OPTIONS[project_type_label],
        "detail_level": DETAIL_LEVEL_OPTIONS[detail_level_label],
        "output_format": OUTPUT_FORMAT_OPTIONS[output_format_label],
    }

    if len(description.strip()) < 20:
        st.error("Project description must contain at least 20 characters.")
        return

    with st.spinner("Generating typed product estimate..."):
        try:
            result = post_estimation_request(payload)
        except requests.HTTPError as exc:
            response_text = exc.response.text if exc.response is not None else str(exc)
            st.error(f"Backend returned an error: {response_text}")
            return
        except requests.RequestException as exc:
            st.error(f"Could not reach backend: {exc}")
            return

    st.subheader("Estimate")
    st.markdown(result.get("text", ""))

    prompt_version = result.get("prompt_version", "unknown")
    st.caption(f"Prompt version: {prompt_version}")

    with st.expander("Request payload"):
        st.json(payload)


if __name__ == "__main__":
    main()
