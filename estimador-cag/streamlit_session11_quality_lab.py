"""
Optional Streamlit viewer for the Session 11 generation-quality artifacts.

This standalone page is intentionally kept off the canonical Streamlit app so
Session 11 delivery remains stable. Use it as an extra branch seed for Session 12.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from evals.session11_generation.quality_lab_helpers_s11 import (
    OFFICIAL_RAGAS_PROFILE,
    build_metric_rows,
    build_provider_status_rows,
    load_json_payload,
)


RESULTS_PATH = Path("evals/session11_generation/ragas_results_openai_s11.json")
REPORT_PATH = Path("evals/session11_generation/RAGAS_BASELINE_S11.md")


def render_metrics_section() -> None:
    """Render the committed OpenAI RAGAS baseline as a Streamlit table."""

    st.header("RAGAS baseline")

    if not RESULTS_PATH.exists():
        st.warning(f"Missing result artifact: {RESULTS_PATH}")
        return

    payload = load_json_payload(RESULTS_PATH)
    metric_a, metric_b, metric_c, metric_d = st.columns(4)

    rows = build_metric_rows(payload)
    average = rows[-1]

    with metric_a:
        st.metric("faithfulness", f"{average['faithfulness']:.3f}")
    with metric_b:
        st.metric("answer_relevancy", f"{average['answer_relevancy']:.3f}")
    with metric_c:
        st.metric("context_precision", f"{average['context_precision']:.3f}")
    with metric_d:
        st.metric("context_recall", f"{average['context_recall']:.3f}")

    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.info(
        "The suspicious signal is low answer_relevancy with perfect grounding metrics. "
        "Treat this as course-scale baseline evidence, not production quality."
    )

    with st.expander("Raw RAGAS JSON", expanded=False):
        st.json(payload)


def render_provider_section() -> None:
    """Render official and comparison provider status."""

    st.header("Provider status")
    st.caption(
        "OpenAI is the official submitted baseline. DeepSeek and Kimi remain comparison paths "
        "that need a live judge adapter avoiding multi-completion requests."
    )
    st.dataframe(build_provider_status_rows(), use_container_width=True, hide_index=True)


def render_report_section() -> None:
    """Render the committed Markdown report."""

    st.header("Committed report")

    if not REPORT_PATH.exists():
        st.warning(f"Missing report artifact: {REPORT_PATH}")
        return

    st.markdown(REPORT_PATH.read_text())


def render_reproduction_section() -> None:
    """Show the safe reproduction profile without embedding secrets."""

    st.header("Reproduction profile")
    st.code(OFFICIAL_RAGAS_PROFILE, language="text")
    st.caption(
        "Run live provider commands only from a local/Codespaces terminal with explicit keys. "
        "Never run live RAGAS from deterministic CI."
    )


def main() -> None:
    """Render the optional Session 11 Quality Lab."""

    st.set_page_config(
        page_title="Session 11 Quality Lab",
        page_icon="📊",
        layout="wide",
    )

    st.title("Session 11 Quality Lab")
    st.caption(
        "Optional extra branch viewer for verifiable citations and RAGAS baseline artifacts."
    )

    tab_metrics, tab_providers, tab_report, tab_reproduce = st.tabs(
        [
            "RAGAS metrics",
            "Providers",
            "Report",
            "Reproduce",
        ]
    )

    with tab_metrics:
        render_metrics_section()

    with tab_providers:
        render_provider_section()

    with tab_report:
        render_report_section()

    with tab_reproduce:
        render_reproduction_section()


if __name__ == "__main__":
    main()
