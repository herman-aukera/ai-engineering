"""
Streamlit product interface for the Session 04 typed estimation flow.

LAYER: frontend
RESPONSIBILITY: Collect typed estimation parameters, call the FastAPI backend,
                and render structured estimate fields.
WHY IT EXISTS: Session 04 turns the estimator from a free chat into a product
               interface with explicit request fields and field based output.
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

PROMPT_VERSION_OPTIONS = ["v1", "v2"]


def get_backend_url() -> str:
    """Return the configured backend base URL without a trailing slash."""

    return os.getenv("ESTIMADOR_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def build_estimate_url() -> str:
    """Build the FastAPI estimate endpoint URL used by the product form."""

    return f"{get_backend_url()}{ESTIMATE_PATH}"


def post_estimation_request(payload: dict[str, Any], prompt_version: str = "v1") -> dict[str, Any]:
    """
    Send the typed estimation payload to the backend.

    Raises:
        requests.HTTPError: When the backend returns a non success response.
        requests.RequestException: For connection and timeout failures.
    """

    response = requests.post(
        build_estimate_url(),
        params={"prompt_version": prompt_version},
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


def parse_reference_projects(raw_text: str) -> list[dict[str, Any]] | None:
    """Parse optional reference project notes into typed request payload items."""

    projects: list[dict[str, Any]] = []

    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue

        parts = [part.strip() for part in cleaned.split("|")]
        name = parts[0][:120]
        estimated_hours = None
        notes = None

        if len(parts) >= 2:
            hours_candidate = (
                parts[1]
                .lower()
                .replace("hours", "")
                .replace("hour", "")
                .replace("hrs", "")
                .replace("h", "")
                .strip()
            )
            if hours_candidate.isdigit():
                estimated_hours = int(hours_candidate)
            else:
                notes = parts[1]

        if len(parts) >= 3:
            notes = parts[2]

        summary = notes or cleaned

        projects.append(
            {
                "name": name,
                "summary": summary[:800],
                "estimated_hours": estimated_hours,
                "notes": notes[:800] if notes else None,
            }
        )

    return projects or None


def format_eur(value: int | float | None) -> str:
    """
    Format a euro value for metric cards.

    Why this matters:
    The backend stores numeric fields, while the UI needs a readable product
    presentation.
    """

    if value is None:
        return "unknown"

    return f"€{value:,.0f}"


def render_list_section(title: str, items: list[str] | None) -> None:
    """
    Render a structured list section.

    Why this matters:
    Assumptions, risks, and recommendations are first class fields in
    EstimationResult. The UI should not scrape them from markdown.
    """

    st.markdown(f"### {title}")

    if not items:
        st.caption("No items returned.")
        return

    for item in items:
        st.markdown(f"- {item}")


def render_cache_and_prompt_metadata(result: dict[str, Any]) -> None:
    """
    Render prompt and cache metadata for auditability.

    Why this matters:
    During class review we can explain which prompt version, cache state, model,
    provider, and tier produced the estimate.
    """

    prompt_version = result.get("prompt_version", "unknown")
    st.caption(f"Prompt version: {prompt_version}")

    cached = result.get("cached")
    cache_backend = result.get("cache_backend")
    model = result.get("model")
    provider = result.get("provider")
    tier = result.get("tier")

    cache_label = "hit" if cached else "miss" if cached is False else "unknown"
    metadata_parts = [
        f"Cache: {cache_label}",
        f"backend={cache_backend or 'unknown'}",
        f"model={model or 'unknown'}",
        f"provider={provider or 'unknown'}",
        f"tier={tier or 'unknown'}",
    ]

    st.caption(" | ".join(metadata_parts))


def render_structured_estimate(result: dict[str, Any]) -> None:
    """
    Render the backend EstimationResponse.

    Structured result is the primary UI path. Text is a compatibility fallback.

    Why this matters:
    Phase 5 closes the product loop. The frontend now consumes fields from
    EstimationResult instead of parsing model prose.
    """

    structured_result = result.get("result")

    st.subheader("Estimate")

    if not structured_result:
        st.warning("No structured result returned. Falling back to text output.")
        st.markdown(result.get("text", ""))
        render_cache_and_prompt_metadata(result)
        return

    st.markdown("### Summary")
    st.info(structured_result.get("summary", "No summary returned."))

    metric_cost, metric_duration, metric_confidence = st.columns(3)

    with metric_cost:
        st.metric("Total cost", format_eur(structured_result.get("total_cost_eur")))

    with metric_duration:
        duration = structured_result.get("total_duration_weeks", "unknown")
        st.metric("Duration", f"{duration} weeks")

    with metric_confidence:
        confidence = structured_result.get("confidence_pct", "unknown")
        st.metric("Confidence", f"{confidence}%")

    phases = structured_result.get("phases") or []
    phase_rows = [
        {
            "Phase": phase.get("name"),
            "Summary": phase.get("summary"),
            "Duration weeks": phase.get("duration_weeks"),
            "Cost EUR": phase.get("cost_eur"),
            "Confidence %": phase.get("confidence_pct"),
            "Tasks": ", ".join(phase.get("tasks") or []),
            "Risks": ", ".join(phase.get("risks") or []),
        }
        for phase in phases
    ]

    st.markdown("### Phases")
    if phase_rows:
        st.dataframe(phase_rows, use_container_width=True, hide_index=True)
    else:
        st.caption("No phases returned.")

    section_assumptions, section_risks, section_recommendations = st.columns(3)

    with section_assumptions:
        render_list_section("Assumptions", structured_result.get("assumptions"))

    with section_risks:
        render_list_section("Risks", structured_result.get("risks"))

    with section_recommendations:
        render_list_section("Recommendations", structured_result.get("recommendations"))

    with st.expander("Compatibility text"):
        st.markdown(result.get("text", ""))

    render_cache_and_prompt_metadata(result)


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

        prompt_version_label = st.selectbox(
            "Prompt version",
            options=PROMPT_VERSION_OPTIONS,
            index=0,
        )

        reference_projects_raw = st.text_area(
            "Reference projects, optional",
            height=120,
            placeholder=(
                "Optional calibration notes, one project per line. Example: "
                "CRM migration | 260h | permissions and reporting were risky"
            ),
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
        "reference_projects": parse_reference_projects(reference_projects_raw),
    }

    if len(description.strip()) < 20:
        st.error("Project description must contain at least 20 characters.")
        return

    with st.spinner("Generating typed product estimate..."):
        try:
            result = post_estimation_request(payload, prompt_version=prompt_version_label)
        except requests.HTTPError as exc:
            response_text = exc.response.text if exc.response is not None else str(exc)
            st.error(f"Backend returned an error: {response_text}")
            return
        except requests.RequestException as exc:
            st.error(f"Could not reach backend: {exc}")
            return

    render_structured_estimate(result)

    with st.expander("Request payload"):
        st.json(payload)


if __name__ == "__main__":
    main()
